"""tapetum CLI. stdout is one JSON object; progress goes to stderr."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def _emit(obj: dict, as_json: bool) -> int:
    if as_json or not sys.stdout.isatty():
        print(json.dumps(obj, ensure_ascii=False))
    else:
        if obj.get("ok") is False and obj.get("error"):
            e = obj["error"]
            print(f"✗ {e['code']}: {e['message']}\n  → {e['hint']}")
        elif "checks" in obj:
            for c in obj["checks"]:
                print(f"{'✓' if c['ok'] else '✗'} {c['check']:<20} {c['detail']}")
        else:
            print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0 if obj.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    """Every path ends in one JSON object on stdout, even a crash."""
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    try:
        return _main(argv)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        return _emit({"ok": False, "error": {"code": "interrupted", "message": "stopped by the user", "hint": ""}}, as_json)
    except Exception as e:
        from .common import TapetumError
        if isinstance(e, TapetumError):
            return _emit({"ok": False, "error": e.to_dict()}, as_json)
        return _emit({"ok": False, "error": {"code": "internal", "message": f"{type(e).__name__}: {str(e)[:300]}",
                      "hint": "This is a bug. Please report it at https://github.com/Nadercr7/tapetum/issues"}}, as_json)


def _main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles: never choke on non-ASCII
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if argv[:1] == ["doctor"]:
        from .doctor import run
        return _emit(run(), "--json" in argv)
    if argv[:1] == ["view"]:
        from .view import build
        if len(argv) < 2:
            print("usage: tapetum view <run-dir> [--no-open]", file=sys.stderr)
            return 2
        return _emit(build(argv[1], "--no-open" not in argv), "--json" in argv)
    if argv[:1] == ["mcp"]:
        from .mcp_server import serve
        serve()
        return 0

    p = argparse.ArgumentParser(prog="tapetum", description="Give any AI agent eyes.")
    p.add_argument("source", help="video URL, YouTube id, or local file")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--lang", help="preferred caption/speech languages, e.g. ar,en")
    p.add_argument("--budget", type=int, default=24, help="max frames kept (default 24; short clips use fewer)")
    p.add_argument("--quality", default="balanced", help="fast | balanced | accurate | any Whisper model name")
    p.add_argument("--no-frames", action="store_true", help="transcript only")
    p.add_argument("--ocr", action="store_true", help="read on-screen text (needs tapetum[ocr])")
    p.add_argument("--force-stt", action="store_true", help="skip platform captions, use speech-to-text")
    p.add_argument("--fresh", action="store_true", help="ignore the cache")
    p.add_argument("--out", help="output directory (default: ~/.tapetum/<id>)")
    p.add_argument("--at", help="zoom: full-resolution frames around MM:SS")
    p.add_argument("--window", type=float, default=8.0, help="zoom window in seconds")
    p.add_argument("--json", action="store_true", help="always print JSON")
    a = p.parse_args(argv)

    from . import pipeline
    if a.at:
        res = pipeline.zoom(a.source, a.at, a.window, out=a.out)
    else:
        res = pipeline.watch(
            a.source, out=a.out, budget=a.budget, lang=a.lang, quality=a.quality,
            no_frames=a.no_frames, fresh=a.fresh, force_stt=a.force_stt, ocr=a.ocr,
        )
    return _emit(res, a.json)


if __name__ == "__main__":
    raise SystemExit(main())
