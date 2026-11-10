# Changelog

## 0.2.2 (2026-11-10)
- `--at` zoom on YouTube takes seconds instead of minutes. It used to ask ffmpeg for the section over one HTTP stream, which YouTube throttles (an 8-second clip took about 8 minutes). It now fetches only the few HLS segments around the moment and trims them locally, and falls back to the old path when a site has no HLS.

## 0.2.1 (2026-11-10)
- Install straight from PyPI: `uvx tapetum "<url>"`.
- The MCP server runs with `uvx --from "tapetum[mcp]" tapetum mcp`.

## 0.2.0 (2026-11-10)
First public release.
- Transcripts in order of cost: platform captions, then local Whisper. Captions pick the original language over machine translations and say which track was used.
- Frames picked by change, not by clock, with a budget, contact sheets and `--at` zoom.
- One `timeline.md` per video, a browser viewer (`tapetum view`), an MCP server and a Claude Code skill and plugin.
- Every failure is a JSON error with a code and a hint. Failed runs aren't cached.
