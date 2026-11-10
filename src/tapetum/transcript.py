"""Transcript ladder: platform captions first, local speech-to-text last."""
from __future__ import annotations

import html
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .common import Source, TapetumError, log, run_ffmpeg


@dataclass
class Transcript:
    segments: list[dict]  # {"start": float, "end": float, "text": str}
    source: str  # which rung produced it
    lang: str = ""
    kind: str = "unknown"  # manual | auto | translated | speech-to-text | none
    warnings: list[str] = field(default_factory=list)
    track: str = ""  # the exact caption track used, for provenance

    def text(self) -> str:
        return " ".join(s["text"] for s in self.segments)


def _prefs(lang: str | None) -> list[str]:
    return [p.strip().lower() for p in (lang or "").split(",") if p.strip()]


def _base(code: str) -> str:
    return (code or "").lower().split("-")[0].split("_")[0]


def _tidy_code(code: str) -> str:
    """'en-ehkg1hFWq8A' (a yt-dlp track id) -> 'en'; 'en-US' stays; 'ar-orig' -> 'ar'."""
    parts = (code or "").split("-")
    if len(parts) > 1 and 2 <= len(parts[1]) <= 4 and parts[1] != "orig":
        return f"{parts[0]}-{parts[1]}"
    return parts[0]


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def choose_track(manual: list[str], auto: list[str], prefs: list[str], orig: str | None) -> tuple[str, str] | None:
    """Pick (code, kind) from available caption codes.

    Order: a human track in a wanted language; the original-language human track; the
    original-language speech-recognition track; any human track; a machine translation into a
    wanted language (flagged). Never silently hands back a translation as if it were the original.
    """
    orig = _base(orig or "")
    auto_orig = [c for c in auto if c.endswith("-orig")]
    if not orig and auto_orig:
        orig = _base(auto_orig[0])
    for p in prefs:
        for c in manual:
            if _base(c) == _base(p):
                return c, "manual"
    if orig:
        for c in manual:
            if _base(c) == orig:
                return c, "manual"
    if auto_orig:
        return auto_orig[0], "auto"
    if orig:
        for c in auto:
            if _base(c) == orig:
                return c, "auto"
    if manual:
        # original language unknown: English is the most likely source language, else YouTube's order
        en = [c for c in manual if _base(c) == "en"]
        return (en or manual)[0], "manual"
    for p in prefs:
        for c in auto:
            if _base(c) == _base(p):
                return c, "translated"
    return None


# ---- rung 1: youtube-transcript-api -------------------------------------


def via_youtube_api(src: Source, lang: str | None, orig: str | None = None) -> Transcript:
    from youtube_transcript_api import YouTubeTranscriptApi, YouTubeTranscriptApiException

    api = YouTubeTranscriptApi()
    try:
        tlist = list(api.list(src.id))
    except YouTubeTranscriptApiException as exc:
        first = next((ln for ln in str(exc).splitlines()
                      if ln.strip() and "Could not retrieve" not in ln and "most likely" not in ln), type(exc).__name__)
        code = "bot_blocked" if re.search(r"block|too many requests|ip", first, re.I) else "no_captions"
        raise TapetumError(code, first.strip()[:200]) from exc
    if not tlist:
        raise TapetumError("no_captions", "video has no caption tracks")
    by_code = {}
    for t in tlist:
        key = t.language_code + ("-orig" if t.is_generated else "")
        by_code.setdefault(key, t)
    manual = [t.language_code for t in tlist if not t.is_generated]
    auto = [t.language_code + "-orig" for t in tlist if t.is_generated]
    pick = choose_track(manual, auto, _prefs(lang), orig)
    if pick is None:
        raise TapetumError("no_captions", "no usable caption track")
    code, kind = pick
    chosen = by_code[code]
    segs = [{"start": float(sn.start), "end": float(sn.start + sn.duration), "text": _clean(sn.text)}
            for sn in chosen.fetch()]
    segs = [s for s in segs if s["text"]]
    if not segs:
        raise TapetumError("empty_captions", "caption track was empty")
    warns = _lang_warnings(_prefs(lang), chosen.language_code)
    return Transcript(segs, "youtube-transcript-api", chosen.language_code, kind, warns, track=code)


def _lang_warnings(prefs: list[str], got: str) -> list[str]:
    if prefs and _base(got) not in [_base(p) for p in prefs]:
        return [f"asked for {','.join(prefs)}, the video only has '{got}'"]
    return []


# ---- rung 2: yt-dlp subtitles -------------------------------------------

_TS = re.compile(r"(\d+):(\d\d):(\d\d)[.,](\d{3})|(\d\d):(\d\d)[.,](\d{3})")


def _vtt_time(m: re.Match) -> float:
    if m.group(1) is not None:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000
    return int(m.group(5)) * 60 + int(m.group(6)) + int(m.group(7)) / 1000


def parse_vtt(path: Path) -> list[dict]:
    """VTT to segments. Handles YouTube's rolling auto-captions, where every cue repeats the
    previous line and adds a new one, plus 10 ms cues that only repeat."""
    cues: list[tuple[float, float, list[str]]] = []
    start = end = None
    buf: list[str] = []

    def close():
        if start is not None and buf:
            lines = [_clean(re.sub(r"<[^>]+>", "", b)) for b in buf]
            cues.append((start, end, [ln for ln in lines if ln]))

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "-->" in line:
            close()
            buf = []
            ms = list(_TS.finditer(line))
            start, end = (_vtt_time(ms[0]), _vtt_time(ms[1])) if len(ms) >= 2 else (None, None)
        elif line.strip() and not line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE")) \
                and not (line.strip().isdigit() and not buf):
            buf.append(line)
    close()

    segs: list[dict] = []
    prev: set[str] = set()
    for s, e, lines in cues:
        if e is not None and e - s < 0.05:  # flash cue that only repeats the last line
            continue
        new = [ln for ln in lines if ln not in prev]
        prev = set(lines)
        text = " ".join(new).strip()
        if text and (not segs or text != segs[-1]["text"]):
            segs.append({"start": s, "end": e, "text": text})
    return segs


def via_ytdlp_subs(src: Source, lang: str | None, meta: dict | None = None) -> Transcript:
    import yt_dlp

    meta = meta or {}
    pick = choose_track(meta.get("subtitles") or [], meta.get("automatic_captions") or [],
                        _prefs(lang), meta.get("language"))
    if pick is None:
        raise TapetumError("no_captions", "no subtitles on this video")
    code, kind = pick
    with tempfile.TemporaryDirectory() as td:
        opts = {
            "skip_download": True, "writesubtitles": kind == "manual", "writeautomaticsub": kind != "manual",
            "subtitleslangs": [re.escape(code)], "subtitlesformat": "vtt/best",
            "outtmpl": str(Path(td) / "s.%(ext)s"), "quiet": True, "no_warnings": True, "noplaylist": True,
            "noprogress": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([src.url])
        files = sorted(Path(td).glob("*.vtt"))
        if not files:
            raise TapetumError("no_captions", "yt-dlp could not download the subtitle file")
        segs = parse_vtt(files[0])
    if not segs:
        raise TapetumError("empty_captions", "subtitle file had no text")
    warns = _lang_warnings(_prefs(lang), code)
    if kind == "translated":
        warns.append(f"captions are YouTube's machine translation into '{code}', not the original")
    return Transcript(segs, "yt-dlp-subs", _tidy_code(code), kind, warns, track=code)


# ---- rung 3: local speech-to-text ---------------------------------------

_MODELS = {"fast": "base", "balanced": "small", "accurate": "large-v3-turbo"}
_WEAK_ON_SMALL = {"ar", "fa", "ur", "hi", "bn", "ta", "te", "th", "my", "am", "sw", "yo", "ha"}


def _whisper_langs() -> set[str]:
    try:
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        return set(_LANGUAGE_CODES)
    except Exception:
        return set()


def via_whisper(audio: Path, lang: str | None, quality: str = "balanced", work: Path | None = None) -> Transcript:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TapetumError("no_stt", "faster-whisper is not installed", "pip install faster-whisper") from exc
    import wave

    import numpy as np

    name = _MODELS.get(quality, quality)
    own_tmp = None
    if work is None:
        own_tmp = tempfile.TemporaryDirectory(prefix="tapetum-")
        work = Path(own_tmp.name)
    wav = work / "speech.wav"
    try:
        try:
            run_ffmpeg(["-i", str(audio), "-vn", "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", str(wav)])
        except TapetumError as exc:
            if "does not contain any stream" in exc.message or "matches no streams" in exc.message:
                raise TapetumError("no_audio", "this video has no audio track") from exc
            raise
        # decode ourselves: faster-whisper's own decoder breaks on some PyAV versions
        with wave.open(str(wav), "rb") as w:
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        pcm = pcm.astype(np.float32)
        pcm /= 32768.0

        prefs = [_base(p) for p in _prefs(lang)]
        known = _whisper_langs()
        valid = [p for p in prefs if not known or p in known]
        warns: list[str] = []
        if prefs and not valid:
            warns.append(f"Whisper doesn't know the language code(s) {prefs}; detected the language instead")
        # Force a language only when exactly one is asked for. With several, let Whisper detect.
        force = valid[0] if len(valid) == 1 else None

        log(f"speech-to-text with Whisper '{name}' (the first run downloads the model)")

        def go(device: str):
            model = WhisperModel(name, device=device, compute_type="int8")
            it, inf = model.transcribe(pcm, language=force, vad_filter=True,
                                       condition_on_previous_text=False, no_speech_threshold=0.6)
            return list(it), inf  # lazy; force it here so errors surface inside the try

        try:
            segments, info = go("auto")
        except Exception as exc:
            if not re.search(r"cublas|cudnn|cuda", str(exc), re.I):
                raise
            log("GPU found but its CUDA libraries are missing; using the CPU")
            segments, info = go("cpu")
    finally:
        if own_tmp:
            own_tmp.cleanup()

    segs = []
    for s in segments:
        text = _clean(s.text)
        if not text or s.no_speech_prob > 0.8 or s.avg_logprob < -1.5:  # silence/music hallucinations
            continue
        segs.append({"start": float(s.start), "end": float(s.end), "text": text})
    if not segs:
        warns.append("no speech found (silent, music only, or an unsupported language)")
    elif force is None and info.language_probability < 0.6:
        warns.append(f"unsure which language this is ({info.language}, p={info.language_probability:.2f})")
    if valid and force is None and info.language not in valid:
        warns.append(f"asked for {','.join(valid)}, but the speech sounds like '{info.language}'")
    if name in ("tiny", "base", "small") and info.language in _WEAK_ON_SMALL:
        warns.append("the small speech model is weak on this language; retry with --quality accurate")
    return Transcript(segs, f"whisper:{name}", info.language, "speech-to-text", warns)
