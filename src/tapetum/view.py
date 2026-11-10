"""`tapetum view <dir>`: one self-contained HTML page, frames beside the transcript."""
from __future__ import annotations

import json
import webbrowser
from importlib import resources
from pathlib import Path

from .common import TapetumError

# Characters that could end the <script> block or break a JS string, and their JSON escapes.
_UNSAFE = {"<": "\\u003c", chr(0x2028): "\\u2028", chr(0x2029): "\\u2029"}


def safe_json(data) -> str:
    blob = json.dumps(data, ensure_ascii=False)
    for ch, esc in _UNSAFE.items():
        blob = blob.replace(ch, esc)
    return blob


def build(run_dir: str, open_browser: bool = True) -> dict:
    root = Path(run_dir).expanduser()
    rj, tj = root / "result.json", root / "transcript.json"
    if not rj.exists():
        raise TapetumError("not_a_run", f"{root} has no result.json", "Pass a folder that `tapetum <url>` produced.")
    res = json.loads(rj.read_text(encoding="utf-8"))
    segs = json.loads(tj.read_text(encoding="utf-8")) if tj.exists() else []
    frames = [{"file": f["file"], "t": f["t"], "ts": f["ts"]} for f in res.get("frame_meta", [])]
    data = {
        **{k: (res.get("meta") or {}).get(k) for k in ("title", "uploader", "duration")},
        "url": (res.get("params") or {}).get("source", ""), "source": res.get("source"),
        "transcript": res.get("transcript"), "warnings": res.get("warnings", []),
        "segments": segs, "frames": frames,
    }
    html = resources.files("tapetum").joinpath("viewer.html").read_text(encoding="utf-8")
    out = root / "index.html"
    out.write_text(html.replace("/*__DATA__*/null", safe_json(data)), encoding="utf-8")
    if open_browser:
        webbrowser.open(out.resolve().as_uri())
    return {"ok": True, "viewer": str(out.resolve())}
