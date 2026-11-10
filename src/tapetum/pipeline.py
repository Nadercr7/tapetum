"""The whole run, start to finish. Every outcome is a JSON-able dict, never a traceback."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from . import frames as fr
from . import media, timeline, transcript as tr
from .common import Source, TapetumError, cache_root, fmt_ts, log, parse_source, parse_ts, run_ffmpeg

SCHEMA_VERSION = 1
OUTPUTS = ("frames", "result.json", "timeline.md", "transcript.json", "transcript.srt", "index.html")
# failures that describe the video, not a passing problem; results with only these are safe to cache
BENIGN = {"no_captions", "empty_captions", "no_audio"}


def _clear_outputs(root: Path) -> None:
    """Remove only what tapetum writes. Never the folder itself, never anything else in it."""
    for name in OUTPUTS:
        p = root / name
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()
    for p in root.glob("sheet_*.jpg"):
        p.unlink()


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _cacheable(res: dict) -> bool:
    if res.get("error"):
        return False
    return all(s.get("ok") or s.get("code") in BENIGN for s in res.get("steps", []))


def _run_ladder(src: Source, meta: dict, lang, quality, force_stt, tried: list[dict], work: Path):
    steps = []
    if src.kind == "youtube" and not force_stt:
        steps.append(("youtube-transcript-api", lambda: tr.via_youtube_api(src, lang, meta.get("language"))))
    if src.kind != "local" and not force_stt and (meta.get("subtitles") or meta.get("automatic_captions")):
        steps.append(("yt-dlp-subs", lambda: tr.via_ytdlp_subs(src, lang, meta)))

    def stt():
        return tr.via_whisper(media.get_audio(src, work), lang, quality, work)

    steps.append(("speech-to-text", stt))
    for name, fn in steps:
        try:
            t = fn()
            tried.append({"step": name, "ok": True})
            return t
        except TapetumError as e:
            tried.append({"step": name, "ok": False, "code": e.code, "error": e.message})
            log(f"{name}: {e.code}")
        except Exception as e:  # one broken rung must never take down the ladder
            tried.append({"step": name, "ok": False, "code": "unexpected", "error": f"{type(e).__name__}: {str(e)[:200]}"})
            log(f"{name}: {type(e).__name__}")
    return None


def watch(raw: str, *, out: str | None = None, budget: int = 24, lang: str | None = None,
          quality: str = "balanced", no_frames: bool = False, fresh: bool = False,
          force_stt: bool = False, ocr: bool = False) -> dict:
    src = parse_source(raw)
    root = Path(out) if out else cache_root() / src.key
    if src.kind == "local" and root.resolve() in Path(src.url).parents:
        raise TapetumError("bad_out", "--out is the folder that holds the video",
                           "Pick an empty or new folder for the output.")
    params = {"source": src.url, "budget": budget, "lang": lang, "quality": quality,
              "no_frames": no_frames, "force_stt": force_stt, "ocr": ocr}
    rj = root / "result.json"
    if rj.exists() and not fresh:
        try:
            cached = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cached = {}
        if cached.get("params") == params and cached.get("schema_version") == SCHEMA_VERSION and _cacheable(cached):
            cached["cached"] = True
            return cached
    root.mkdir(parents=True, exist_ok=True)
    _clear_outputs(root)

    result: dict = {"schema_version": SCHEMA_VERSION, "ok": False, "source": src.kind, "id": src.id,
                    "dir": str(root.resolve()), "steps": [], "warnings": [], "params": params}
    try:
        meta = media.probe(src)
    except TapetumError as e:
        result["error"] = e.to_dict()
        return result
    result["meta"] = {k: meta.get(k) for k in ("title", "uploader", "duration", "upload_date", "language")}

    t = None
    frames_meta: list[dict] = []
    sheets: list[str] = []
    ocr_text = None
    with tempfile.TemporaryDirectory(prefix="tapetum-") as td:
        work = Path(td)
        t = _run_ladder(src, meta, lang, quality, force_stt, result["steps"], work)
        if t is None and result["steps"] and result["steps"][-1].get("code") == "no_audio":
            t = tr.Transcript([], "none", "", "none", ["this video has no audio track"])
        if t is None:
            result["error"] = TapetumError(
                "no_transcript", "every transcript method failed",
                "Read `steps`. Then try `tapetum doctor`, another network, or a local file.",
            ).to_dict()
        else:
            if t.segments:
                (root / "transcript.json").write_text(json.dumps(t.segments, ensure_ascii=False, indent=1), encoding="utf-8")
                timeline.write_srt(t.segments, root / "transcript.srt")
            result["transcript"] = {"source": t.source, "lang": t.lang, "kind": t.kind,
                                    "track": t.track, "segments": len(t.segments)}
            result["warnings"] += t.warnings

        if not no_frames:
            try:
                video = media.get_video(src, work)
                files, fps = fr.sample_candidates(video, meta.get("duration"), work / "cand")
                dur = meta.get("duration") or len(files) / fps
                eff = min(budget, max(6, int(dur // 8) + 1))  # short clips need few frames
                chosen = fr.select_frames(files, fps, eff)
                frames_meta = fr.save_frames(chosen, root / "frames")
                sheets = fr.contact_sheets(frames_meta, root)
            except TapetumError as e:
                result["warnings"].append(f"no frames: {e.code}: {e.message}")
                result["frame_error"] = e.to_dict()
            except Exception as e:
                result["warnings"].append(f"no frames: {type(e).__name__}: {str(e)[:160]}")
            if ocr and frames_meta:
                try:
                    from .ocr import read_frames
                    ocr_text = read_frames(root, frames_meta)
                except TapetumError as e:
                    result["warnings"].append(f"on-screen text skipped: {e.message} ({e.hint})")
                except Exception as e:
                    result["warnings"].append(f"on-screen text skipped: {type(e).__name__}")

    md = timeline.build(meta, t, frames_meta, sheets, src.url, ocr_text)
    (root / "timeline.md").write_text(md, encoding="utf-8")
    result["ok"] = t is not None or bool(frames_meta)
    result["files"] = {"timeline": "timeline.md", "sheets": sheets, "frames": [f["file"] for f in frames_meta]}
    result["frame_count"] = len(frames_meta)
    result["frame_meta"] = frames_meta
    _write_json(rj, result)
    return result


def zoom(raw: str, at: str, window: float = 8.0, height: int = 720, out: str | None = None) -> dict:
    src = parse_source(raw)
    try:
        center = parse_ts(at)
    except ValueError:
        raise TapetumError("bad_time", f"can't read the time '{at}'", "Use MM:SS, HH:MM:SS or seconds, like 03:12.")
    window = max(2.0, min(float(window), 60.0))
    t0 = max(0.0, center - window / 2)
    root = Path(out) if out else cache_root() / src.key
    zdir = root / f"zoom_{fmt_ts(t0).replace(':', '-')}"
    if zdir.exists():
        shutil.rmtree(zdir, ignore_errors=True)
    with tempfile.TemporaryDirectory(prefix="tapetum-") as td:
        if src.kind == "local":
            clip = Path(td) / "clip.mp4"
            run_ffmpeg(["-ss", f"{t0:.3f}", "-t", f"{window:.3f}", "-i", src.url, "-an", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "18", str(clip)])
        else:
            clip = media.get_clip(src, Path(td), t0, t0 + window, height)
        shots = fr.grab_around(clip, zdir, count=4, step=max(window / 4, 0.5), offset=t0)
    if not shots:
        raise TapetumError("zoom_empty", "no frames at that time", "Check the time is inside the video.")
    return {"schema_version": SCHEMA_VERSION, "ok": True, "at": at, "dir": str(zdir.resolve()),
            "files": [str((zdir / Path(s["file"]).name).resolve()) for s in shots],
            "times": [s["ts"] for s in shots]}
