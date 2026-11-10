"""Shared helpers: errors, logging, ffmpeg, timestamps, source parsing."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class TapetumError(Exception):
    """An error the agent can act on. `hint` says what to try next."""

    def __init__(self, code: str, message: str, hint: str = ""):
        super().__init__(message)
        self.code, self.message, self.hint = code, message, hint

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "hint": self.hint}


def log(msg: str) -> None:
    print(f"[tapetum] {msg}", file=sys.stderr, flush=True)


def fmt_ts(sec: float) -> str:
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_ts(text: str) -> float:
    """'3:12', '01:03:12', '192' or '192s' -> seconds."""
    t = text.strip().lower().rstrip("s")
    parts = [float(p) for p in t.split(":")]
    out = 0.0
    for p in parts:
        out = out * 60 + p
    return out


def ffmpeg_exe() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover
        raise TapetumError(
            "no_ffmpeg", "ffmpeg not found", "Install ffmpeg or `pip install imageio-ffmpeg`."
        ) from exc


def run_ffmpeg(args: list[str]) -> None:
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise TapetumError("ffmpeg_failed", r.stderr.strip()[-400:] or "ffmpeg failed")


def cache_root() -> Path:
    base = os.environ.get("TAPETUM_HOME")
    root = Path(base) if base else Path.home() / ".tapetum"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class Source:
    kind: str  # youtube | tiktok | instagram | x | vimeo | twitch | reddit | local | web
    id: str
    url: str

    @property
    def key(self) -> str:
        return re.sub(r"[^A-Za-z0-9_-]+", "_", f"{self.kind}-{self.id}")[:80]


_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_source(raw: str) -> Source:
    raw = raw.strip()
    if os.path.exists(raw):
        p = Path(raw).resolve()
        if p.is_dir():
            raise TapetumError("not_a_video", f"{p} is a folder", "Pass a video file or a URL.")
        st = p.stat()
        # same name in two folders, or a file edited in place, must not share a cache entry
        digest = hashlib.sha1(f"{p}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8")).hexdigest()[:10]
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", p.stem).strip("_")[:40] or "file"
        return Source("local", f"{stem}-{digest}", str(p))
    if _YT_ID.match(raw):
        return Source("youtube", raw, f"https://www.youtube.com/watch?v={raw}")
    u = urlparse(raw if "://" in raw else "https://" + raw)
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    path = u.path.strip("/")
    q = parse_qs(u.query)
    if host == "youtu.be":
        return Source("youtube", path.split("/")[0], f"https://www.youtube.com/watch?v={path.split('/')[0]}")
    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        vid = (q.get("v") or [""])[0]
        if not vid:
            m = re.match(r"(?:shorts|embed|live|v)/([A-Za-z0-9_-]{11})", path)
            vid = m.group(1) if m else ""
        if vid:
            return Source("youtube", vid, f"https://www.youtube.com/watch?v={vid}")
        if "list" in q or path.startswith(("playlist", "@", "c/", "channel/", "user/")):
            raise TapetumError("playlist_url", "this is a playlist or channel, not a single video",
                               "Pass one video link. For many videos, run tapetum once per link.")
    for kind, domains in {
        "tiktok": ("tiktok.com",),
        "instagram": ("instagram.com",),
        "x": ("x.com", "twitter.com"),
        "vimeo": ("vimeo.com",),
        "twitch": ("twitch.tv",),
        "reddit": ("reddit.com", "v.redd.it"),
    }.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            m = re.findall(r"(\d{5,})", path) or [path.split("/")[-1] or host]
            return Source(kind, m[-1], u.geturl())
    return Source("web", re.sub(r"\W+", "_", host + "_" + path)[:50], u.geturl())
