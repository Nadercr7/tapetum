<p align="center">
  <a href="https://nadercr7.github.io/tapetum/"><img src="https://raw.githubusercontent.com/Nadercr7/tapetum/main/docs/social.png" alt="tapetum: give your agent eyes" width="760"></a>
</p>

<p align="center">
  <a href="https://github.com/Nadercr7/tapetum/actions/workflows/ci.yml"><img src="https://github.com/Nadercr7/tapetum/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-E8A317.svg" alt="MIT license"></a>
  <a href="https://pypi.org/project/tapetum/"><img src="https://img.shields.io/pypi/v/tapetum.svg?color=E8A317" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-0B0D12.svg" alt="Python 3.10+">
  <a href="https://nadercr7.github.io/tapetum/"><img src="https://img.shields.io/badge/site-live-E8A317.svg" alt="Website"></a>
</p>

**tapetum lets an AI agent watch a video.** You give it a link. It hands back one file with what was said and what was on screen, in time order, plus the handful of frames worth looking at. No cookies, no API keys, no account. Everything runs on your machine.

<p align="center">
  <img src="https://raw.githubusercontent.com/Nadercr7/tapetum/main/docs/media/demo.gif" alt="tapetum running on a YouTube link and printing the timeline" width="760">
</p>

## Install

With [uv](https://docs.astral.sh/uv/), there's nothing to install. Just run it:

```bash
uvx tapetum "https://youtu.be/jNQXAC9IVRw"
```

To keep it around, `uv tool install tapetum` or `pipx install tapetum`, then call `tapetum` directly.

ffmpeg comes bundled. Check your setup any time with `tapetum doctor`.

## What you get back

One JSON object on stdout, and a folder:

```
timeline.md       speech and frame references in time order. Start here.
sheet_01.jpg      nine frames per image, timestamps burned in
frames/           the frames it kept
transcript.srt    plus transcript.json
```

A slice of `timeline.md`:

```markdown
### 00:05 – 00:10
frame: `frames/f001_00-05.jpg`
> the cool thing about these guys is that they have really...
> really really long trunks
```

Open any run in your browser with `tapetum view <folder>`: frames on one side, a searchable transcript on the other. [See a live one.](https://nadercr7.github.io/tapetum/demo/)

## How it works

**Words, cheapest first.** It reads the platform's captions when they exist: human ones over auto-generated, the original language over machine translations, your `--lang` over both. When there are none, it downloads a small audio file and runs Whisper locally. Every step it tried is listed in `steps`, failures included.

**Frames by change, not by clock.** It samples a frame every second, then keeps one only when the picture actually changed. A new line on a slide counts. A wobbling camera doesn't. Transitions collapse into one settled frame, and `--budget` caps the total, so a talking head costs you three images instead of thirty.

**Detail on demand.** `tapetum <url> --at 03:12` downloads just that moment at 720p and writes four sharp frames. No re-run of the whole video.

**Honest output.** Every error comes with a `code` and a `hint`. Shaky transcripts carry warnings. Failed runs aren't cached, so a network blip doesn't stick.

## Use it from an agent

| Where | How |
|---|---|
| Claude Code | `/plugin marketplace add Nadercr7/tapetum`, then `/plugin install tapetum@tapetum`. Or copy `skills/tapetum/` to `~/.claude/skills/`. |
| Any MCP client | Add `{"command": "uvx", "args": ["--from", "tapetum[mcp]", "tapetum", "mcp"]}` to your client's MCP config. Tools: `watch_video`, `zoom_video`. Frames come back as images. |
| Codex, Cursor, others | [AGENTS.md](AGENTS.md) tells them how to call it. |

The skill file is short on purpose. Long instructions cost tokens on every single run.

## Options

```
tapetum <url | file>
  --lang ar,en        languages you prefer, in order
  --budget 24         most frames to keep (short clips use fewer)
  --quality accurate  bigger speech model: fast | balanced | accurate
  --no-frames         transcript only, fastest
  --ocr               read on-screen text (pip install "tapetum[ocr]")
  --force-stt         ignore captions and listen instead
  --at 03:12          zoom into one moment
  --fresh             ignore the cache
  --out DIR           where to write (default ~/.tapetum/<id>)

tapetum doctor        what works on this machine
tapetum view DIR      open a run in the browser
tapetum mcp           start the MCP server
```

## Languages

Whisper covers about 99 languages. On Egyptian Arabic the default model garbles names and numbers, and `--quality accurate` fixes most of it. On a laptop CPU that took about two and a half minutes for a seven-minute video, after a one-time 1.6 GB model download. tapetum warns you when a language is known to be weak on the model you picked. Numbers are in [docs/research/10-measured.md](docs/research/10-measured.md).

## What it can't do

- **Private videos.** Private, age-gated and login-only videos return `login_required`. Instagram and Vimeo mostly land here.
- **Servers.** YouTube blocks most datacenter IPs. Run it from your own computer.
- **Live streams.** You get `live_stream`. Try again once the recording is up.
- **Playlists.** One video per run. You get `playlist_url` otherwise.
- **Hear tone.** Music, sarcasm and accent don't survive a transcript, and the agent should say so.

Text from a video is content, not instructions. `timeline.md` says so at the top, so agents don't take orders from a caption.

## Why "tapetum"

The tapetum is the mirror layer behind a cat's retina. It sends light back through the eye for a second pass, which is why cats see in the dark and why their eyes glow in a flashlight beam. Look twice, miss less.

## Contributing

```bash
uv venv && uv pip install -e ".[mcp]" pytest
pytest
```

Keep the virtualenv outside OneDrive or Dropbox; sync clients lock files mid-install. Design notes, competitor research and measurements are in [docs/research](docs/research/). Releasing is in [docs/RELEASING.md](docs/RELEASING.md).

MIT licensed. Use it on videos you're allowed to watch.
