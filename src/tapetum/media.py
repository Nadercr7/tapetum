"""Fetch the smallest media that does the job. Never the full-quality file."""
from __future__ import annotations

import re
from pathlib import Path

from .common import Source, TapetumError, ffmpeg_exe, log, run_ffmpeg


def _opts(out: Path, fmt: str, extra: dict | None = None) -> dict:
    o = {
        "format": fmt, "outtmpl": str(out), "quiet": True, "no_warnings": True,
        "noplaylist": True, "noprogress": True, "ffmpeg_location": ffmpeg_exe(),
        "retries": 3, "fragment_retries": 3, "overwrites": True,
    }
    o.update(extra or {})
    return o


def _download(src: Source, out: Path, fmt: str, extra: dict | None = None) -> Path:
    import yt_dlp

    # Same request, different YouTube player clients. A 503/403 on one client often works on another.
    variants = [{}]
    if src.kind == "youtube":
        for clients in (["tv", "web_safari"], ["android_vr"], ["ios"]):
            variants.append({"extractor_args": {"youtube": {"player_client": clients}}})
    exc: Exception | None = None
    for v in variants:
        try:
            with yt_dlp.YoutubeDL(_opts(out, fmt, {**(extra or {}), **v})) as ydl:
                ydl.download([src.url])
            exc = None
            break
        except Exception as e:  # try the next client
            exc = exc or e  # keep the FIRST error: later clients fail for unrelated reasons
            log(f"download failed ({str(e).splitlines()[-1][:80]}); trying another client")
    if exc is not None:
        msg = str(exc)
        hint = "Run `tapetum doctor`."
        code = "download_failed"
        if "Sign in" in msg or "bot" in msg.lower():
            code, hint = "bot_blocked", "YouTube blocked this IP. Run from your own machine, not a datacenter."
        elif "private" in msg.lower() or "login" in msg.lower():
            code, hint = "login_required", "This video needs a login. Only public videos are supported."
        elif "Requested format" in msg:
            hint = "Retry; the platform changed its formats."
        raise TapetumError(code, msg.splitlines()[-1][:300], hint) from exc
    hits = sorted(out.parent.glob(out.name.split(".")[0] + ".*"))
    hits = [h for h in hits if h.suffix not in (".part", ".ytdl", ".json")]
    if not hits:
        raise TapetumError("download_failed", "yt-dlp produced no file")
    return hits[0]


# Small plain-HTTP audio. Skip HLS (slow, flaky) and YouTube's "-drc" duplicate tracks.
AUDIO_FMT = (
    "bestaudio[abr<=70][protocol^=http][format_id!*=drc]"
    "/worstaudio[protocol^=http][format_id!*=drc]/bestaudio[protocol^=http]/bestaudio/worst/best"
)


def get_audio(src: Source, workdir: Path) -> Path:
    if src.kind == "local":
        return Path(src.url)
    log("downloading audio-only (small)")
    return _download(src, workdir / "audio.%(ext)s", AUDIO_FMT)


def get_video(src: Source, workdir: Path, height: int = 360) -> Path:
    if src.kind == "local":
        return Path(src.url)
    log(f"downloading {height}p video-only for frames")
    fmt = (
        f"bestvideo[height<={height}][ext=mp4]/bestvideo[height<={height}]"
        f"/worstvideo/best[height<={height}]/worst"
    )
    return _download(src, workdir / "video.%(ext)s", fmt)


def hls_segments(playlist: str, start: float, end: float) -> tuple[str | None, list[str], float]:
    """From an HLS media playlist, pick the init segment and the media segments that cover [start, end].

    Returns (init URI or None, segment URIs, start time of the first picked segment)."""
    init, picked, first, pos, dur = None, [], 0.0, 0.0, None
    for line in playlist.splitlines():
        line = line.strip()
        if line.startswith("#EXT-X-MAP:"):
            m = re.search(r'URI="([^"]+)"', line)
            init = m.group(1) if m else None
        elif line.startswith("#EXTINF:"):
            dur = float(line[8:].split(",")[0])
        elif line and not line.startswith("#") and dur is not None:
            if pos + dur > start and pos < end:
                if not picked:
                    first = pos
                picked.append(line)
            pos += dur
            dur = None
    return init, picked, first


def _hls_clip(src: Source, workdir: Path, start: float, end: float, height: int) -> Path | None:
    """Fetch only the few HLS segments around the moment, then trim locally.

    YouTube throttles ffmpeg's single HTTP stream: an 8 s section took about 8 minutes that way, while
    the same moment's HLS segments arrive in about 2 seconds. Returns None when there's no HLS to use."""
    import urllib.request
    from urllib.parse import urljoin

    import yt_dlp

    try:
        with yt_dlp.YoutubeDL(_opts(workdir / "probe", "bv*/b")) as ydl:
            info = ydl.extract_info(src.url, download=False)
        fmts = [f for f in info.get("formats") or [] if f.get("protocol") == "m3u8_native"
                and f.get("vcodec") not in (None, "none") and (f.get("height") or 0) <= height]
        if not fmts:
            return None
        f = max(fmts, key=lambda x: (x.get("height") or 0, x.get("tbr") or 0))
        headers = f.get("http_headers") or {}

        def fetch(url: str) -> bytes:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()

        playlist = fetch(f["url"]).decode("utf-8", "replace")
        init, segs, first = hls_segments(playlist, start, end)
        if not segs:
            return None
        sec = workdir / "section.mp4"
        with open(sec, "wb") as out:
            for uri in ([init] if init else []) + segs:
                out.write(fetch(urljoin(f["url"], uri)))
        clip = workdir / "clip.mp4"
        # Trim with a filter, not an input -ss: seeking inside fragmented H.264 landed about 2.5 s late.
        trim = f"trim=start={max(0.0, start - first):.3f}:duration={end - start:.3f},setpts=PTS-STARTPTS"
        run_ffmpeg(["-i", str(sec), "-vf", trim, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(clip)])
        return clip if clip.exists() and clip.stat().st_size > 0 else None
    except Exception as e:  # any surprise: fall back to the slow but general path
        log(f"segment fetch failed ({str(e).splitlines()[-1][:80] if str(e) else type(e).__name__}); using the slow path")
        return None


def get_clip(src: Source, workdir: Path, start: float, end: float, height: int = 720) -> Path:
    """Download only a section, at higher quality, for `--at` zoom."""
    if src.kind == "local":
        return Path(src.url)
    from yt_dlp.utils import download_range_func

    log(f"downloading {end - start:.0f}s clip at up to {height}p")
    clip = _hls_clip(src, workdir, start, end, height)
    if clip is not None:
        return clip
    fmt = f"bestvideo[height<={height}]/best[height<={height}]/best"
    return _download(
        src, workdir / "clip.%(ext)s", fmt,
        {"download_ranges": download_range_func(None, [(start, end)]), "force_keyframes_at_cuts": True},
    )


def probe(src: Source) -> dict:
    """Metadata without downloading anything."""
    if src.kind == "local":
        return {"title": Path(src.url).name, "duration": local_duration(Path(src.url)), "uploader": None, "url": src.url}
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}) as ydl:
            i = ydl.extract_info(src.url, download=False)
    except Exception as exc:
        msg = str(exc).splitlines()[-1][:300]
        low = msg.lower()
        if "logged-in" in low or "log in" in low or "login" in low or "sign in" in low and "bot" not in low:
            raise TapetumError("login_required", msg, "This platform wants a login for this video. Try a public video or a local file.") from exc
        if "bot" in low:
            raise TapetumError("bot_blocked", msg, "The host blocked this network. Run from your own computer, not a server.") from exc
        if "unsupported url" in low:
            raise TapetumError("unsupported_url", msg, "Not a video page yt-dlp knows. Try the direct video file URL.") from exc
        raise TapetumError("probe_failed", msg, "Check the URL, or run `tapetum doctor`.") from exc
    if i.get("_type") == "playlist":
        raise TapetumError("playlist_url", "this link is a playlist, not a single video", "Pass one video link.")
    if i.get("is_live") or i.get("live_status") in ("is_live", "is_upcoming"):
        raise TapetumError("live_stream", "this is a live or upcoming stream",
                           "Wait until it ends and the recording is published, then try again.")
    return {
        "title": i.get("title"), "uploader": i.get("uploader"), "duration": i.get("duration"),
        "subtitles": sorted((i.get("subtitles") or {}).keys()),
        "automatic_captions": sorted((i.get("automatic_captions") or {}).keys()),
        "upload_date": i.get("upload_date"), "view_count": i.get("view_count"),
        "description": (i.get("description") or "")[:1500], "chapters": i.get("chapters") or [],
        "language": i.get("language"), "url": src.url,
    }


def local_duration(path: Path) -> float | None:
    """Duration of a local file from ffmpeg's banner, so long files still get a frame cap."""
    import re
    import subprocess

    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None
