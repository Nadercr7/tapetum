# tapetum for coding agents

To watch a video, run `tapetum "<url>"` (or `uvx tapetum "<url>"` with nothing installed) and read the `dir/timeline.md` it reports. Full instructions: [skills/tapetum/SKILL.md](skills/tapetum/SKILL.md).

Working on this repo:
- Python 3.10+, source in `src/tapetum/`. Install with `uv pip install -e .` into a venv outside OneDrive.
- stdout is one JSON object, progress goes to stderr. Don't print anything else to stdout.
- Every failure is a `TapetumError` with a `code` and a `hint`. No raw tracebacks reach the user.
- Test on real links: a captioned YouTube video, one without captions (forces Whisper), a local file, an Arabic video.
