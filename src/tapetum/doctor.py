"""`tapetum doctor`: say what works on THIS machine, and what to do about what doesn't."""
from __future__ import annotations

import shutil
import sys
import urllib.request

from .common import ffmpeg_exe

TEST_VIDEO = "jNQXAC9IVRw"  # the first YouTube video; short and stable


def _check(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:
        ok, detail = False, f"{type(exc).__name__}: {str(exc)[:120]}"
    return {"check": name, "ok": ok, "detail": detail}


def run() -> dict:
    checks = []
    checks.append(_check("python>=3.10", lambda: (sys.version_info >= (3, 10), sys.version.split()[0])))
    checks.append(_check("ffmpeg", lambda: (True, ffmpeg_exe())))

    def ytdlp():
        import yt_dlp
        return True, yt_dlp.version.__version__

    checks.append(_check("yt-dlp", ytdlp))

    def js():
        found = [n for n in ("deno", "node", "qjs", "bun") if shutil.which(n)]
        return bool(found), ", ".join(found) or "none (some YouTube formats may fail; install Node 22+ or Deno)"

    checks.append(_check("js-runtime", js))

    def net():
        urllib.request.urlopen("https://www.youtube.com/", timeout=8).read(200)
        return True, "reachable"

    checks.append(_check("network:youtube", net))

    def captions():
        from youtube_transcript_api import YouTubeTranscriptApi
        n = len(list(YouTubeTranscriptApi().fetch(TEST_VIDEO)))
        return n > 0, f"{n} caption lines"

    checks.append(_check("youtube-captions", captions))

    def stt():
        import faster_whisper
        return True, f"faster-whisper {faster_whisper.__version__}"

    checks.append(_check("speech-to-text", stt))

    def ocr():
        import rapidocr_onnxruntime  # noqa: F401
        return True, "installed"

    r = _check("ocr (optional)", ocr)
    if not r["ok"]:
        r["detail"] = "not installed: pip install 'tapetum[ocr]'"
        r["optional"] = True
    checks.append(r)
    required = [c for c in checks if not c.get("optional")]
    return {"ok": all(c["ok"] for c in required), "checks": checks}
