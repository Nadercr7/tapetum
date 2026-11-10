# real-eyes: prior art, packaging, presentation, naming

Research date: 2026-11-10. Stars and last-push dates come from `gh` on that day. Anything marked "(web)" comes from search snippets and aggregator pages that I did not verify against the repo.

## TL;DR

- The idea is not empty. `bradautomates/claude-video` (the `/watch` skill) has about 20k stars and was created 2026-04-24. It already does URL to frames plus transcript, runs on Codex and other Agent Skills hosts, and has a Gemini "whole video" engine. Pitching real-eyes as "a skill that watches video" will not set it apart.
- Its weakness is packaging and reliability. It is Claude-plugin-first, the README is a long install maze, and the open issues are extraction bugs: the near-duplicate filter drops slides that differ only in text, caption selection picks the wrong language, FFmpeg 7+ breaks on `-vsync`, TikTok reports "no captions", WhisperX fails to install on Linux, Gemini engine throws 400/503.
- Best wedge: one zero-install CLI (`uvx real-eyes <url>`) with a stable JSON/Markdown contract, a tiny SKILL.md, an optional MCP wrapper, and a visual viewer (transcript beside frames on a timeline) that no competitor has.
- Name: `real-eyes` and `realeyes` are free on PyPI and npm, and no GitHub repo has that exact name. But Realeyes is an established emotion-AI company (GitHub org `Realeyes`, realeyesit.com) and the GitHub user handle `real-eyes` is taken by a person. Safer picks are in section 4.

---

## 1. Prior art: the ones to beat

Stars as of 2026-11-10.

### Tier A: direct competitors (frames + transcript for an agent)

| # | Repo | Stars | Last push | Form | Good | Lacks | Steal |
|---|------|-------|-----------|------|------|-------|-------|
| 1 | [bradautomates/claude-video](https://github.com/bradautomates/claude-video) | 20.4k | 2026-09-25 | Skill + Claude/Codex plugin, Python scripts | Captions first, then WhisperX/Groq/OpenAI fallback. `--engine gemini` hands the whole video to Gemini. Detail dial (transcript / balanced). Installs via Claude Desktop, VS Code, Codex, `npx skills add`. Has AGENTS.md, CLAUDE.md, tests, CHANGELOG | README front-loads about 100 lines of install steps. Does not work in Claude Chat/Cowork. Open bugs (see TL;DR). No viewer. No zero-install CLI | The detail dial, the "Choose your app" table, screenshots in install docs, AGENTS.md next to CLAUDE.md |
| 2 | [jordanrendric/claude-video-vision](https://github.com/jordanrendric/claude-video-vision) | 1.5k | 2026-10-14 | Claude plugin + npm MCP server | Hero image, "perception layer, not interpretation layer" framing, setup wizard, adaptive fps / time range / resolution, MCP auto-installs through npx | Claude Code only in practice; backends need keys or setup | The perception-layer positioning and the setup wizard |
| 3 | [guimatheus92/mcp-video-analyzer](https://github.com/guimatheus92/mcp-video-analyzer) | 120 | 2026-11-08 | npm MCP + `/video` plugin + portable skill + CLI | Three entry points. Skill falls back to a bundled CLI when MCP is absent. Transcripts, key frames, OCR, metadata, comments. Many platforms (Loom, TikTok, X, Instagram). Listed in awesome-mcp-servers and Glama. Badge row | Node 22.12+ requirement; yt-dlp still needed for most platforms; low stars | The skill-falls-back-to-CLI trick. Registry listings |
| 4 | [Newuxtreme/watch-video-skill](https://github.com/Newuxtreme/watch-video-skill) | 86 | 2026-04-30 | Skill | Structured notes: TL;DR, timeline, key quotes, visual notes | Small, stale | Notes template as an optional output mode |
| 5 | [khou/watch-video](https://github.com/khou/watch-video) | 7 | 2026-05-03 | Skill + marketplace + Homebrew | Honest token-cost table (fast/balanced/accurate with image-token ranges), local whisper.cpp, "agent reads only the frames it needs", Gemini CLI wiring, install by "just ask your agent" | Tiny community, shell-script feel | Token-cost table. The "ask your agent to install from this URL" flow |
| 6 | [kar2phi/video-lens](https://github.com/kar2phi/video-lens) | 127 | 2026-11-06 | Coding-agent skill | YouTube transcript into a structured HTML page | Transcript only | HTML report as a first-class output (feeds our viewer) |
| 7 | [newway1814/reelvault](https://github.com/newway1814/reelvault) | 2 | 2026-07-24 | Claude skills | Transcript + frames into a vault of notes | Barely used | Knowledge-base output angle |
| 8 | media-context-mcp, VideoContext MCP, claude-real-video, OcularAudio-MCP (web only, not verified) | n/a | n/a | MCP / plugins | Local-first; scene-change keyframes, near-duplicate removal, faster-whisper, optional OCR | Unverified, small | Scene-change keyframes plus OCR for slide-heavy video |

### Tier B: transcript-only and YouTube plumbing (what people use today)

| # | Repo | Stars | Last push | What it is | Lacks | Steal |
|---|------|-------|-----------|-----------|-------|-------|
| 9 | [jdepoix/youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | 8.6k | 2026-11-09 | The de facto Python lib for YouTube captions, no API key | Captions only, YouTube only, IP blocks from cloud hosts | Cheap first step in the fallback chain |
| 10 | [steipete/summarize](https://github.com/steipete/summarize) | 6.8k | 2026-11-05 | "Point at any URL/YouTube/Podcast or file. Get the gist." CLI + Chrome extension | Summarises with its own LLM; gives the agent no raw frames | One-sentence tagline; CLI-first ergonomics |
| 11 | [ZeroPointRepo/youtube-skills](https://github.com/ZeroPointRepo/youtube-skills) | 1.2k | 2026-11-03 | Transcript API skills: transcripts, search, channels | Hosted API dependency, no frames | Search/browse beyond one video |
| 12 | [kevinwatt/yt-dlp-mcp](https://github.com/kevinwatt/yt-dlp-mcp) | 308 | 2026-10-29 | MCP bridging yt-dlp (subtitles, metadata, download) | No frames, no vision | Typed tools with small outputs |
| 13 | [coyaSONG/youtube-mcp-server](https://github.com/coyaSONG/youtube-mcp-server) | 27 | 2026-10-26 | Citation-ready transcript search, exact timestamp links | Transcript only | Timestamp deep links (`&t=123s`) in every answer |
| 14 | [kirbah/mcp-youtube](https://github.com/kirbah/mcp-youtube) | 33 | 2026-11-01 | "Token-optimized" structured YouTube data | Data API, not content | Token-budget framing |
| 15 | [ZubeidHendricks/youtube-mcp-server](https://github.com/ZubeidHendricks/youtube-mcp-server) | 596 | 2026-08-08 | Broad YouTube Data API v3 MCP | API key; no understanding | Shows demand for "youtube" in the title |

### Adjacent, worth knowing

- [browser-use/video-use](https://github.com/browser-use/video-use) (30.8k): agents editing video. Different job, but proof that "agents + video" is hot and a model for a viral README.
- [PleasePrompto/notebooklm-mcp](https://github.com/PleasePrompto/notebooklm-mcp) (3.4k): developers star "give my agent a grounded source" tools.
- Gemini native YouTube understanding: several tiny MCPs wrap it (DerYUYU/gemini-video-mcp, adamanz/gemini-video-mcp-server). Cheapest path to a whole video with audio, but needs a Google key and is a black box. claude-video already offers it as an engine; offer it too, but not as the default.
- Directories to get listed in: VoltAgent/awesome-agent-skills (37k), punkpeye/awesome-mcp-servers (97.5k), Glama, mcpservers.org, skills.sh, claudemarketplaces.com, tessl registry.

### Competitive read

1. Nobody ships a viewer. Every tool dumps frames and text into the agent's context, and the human never sees what the agent saw.
2. Nobody has a stable machine contract (versioned JSON schema, exit codes, a token budget flag). Each MCP invents its own output shape.
3. Reliability on real videos is where claude-video's issues pile up: slides, multi-language captions, FFmpeg versions, TikTok/Reels without captions, Linux installs. A tight test corpus and a doctor command would be a differentiator.
4. Token honesty: only khou/watch-video publishes image-token costs. A `--budget 20k` flag that picks frame count and size to fit would beat everyone.
5. Two-pass watching: a cheap overview first (transcript plus sparse contact sheet), then the agent asks for specific time ranges (`--at 12:30-13:10 --dense`). Adaptive extraction in claude-video-vision gestures at this; make it the core loop.

---

## 2. Packaging for maximum reach

### The shape: one core CLI, three thin wrappers

```
real-eyes (Python package, CLI)         <- the product
  |- skills/real-eyes/SKILL.md          <- 30-60 line wrapper, calls the CLI
  |- MCP server (`real-eyes mcp`)       <- optional, same functions, 3 tools
  |- AGENTS.md                          <- for Codex / Cursor / Copilot / Gemini CLI
```

Why CLI first: every coding agent can run a shell command, so the CLI works in Claude Code, Codex, Cursor, Gemini CLI, Aider, OpenCode and custom agent loops. MCP-only reaches fewer places and pays tool-schema tokens on every turn. mcp-video-analyzer's design (skill falls back to the bundled CLI) confirms the pattern.

### Agent Skills format (agentskills.io spec, fetched 2026-11-10)

- `SKILL.md` with YAML frontmatter. Required: `name` (1-64 chars, lowercase letters/digits/hyphens, no leading, trailing or double hyphens, must equal the parent directory name) and `description` (1-1024 chars; say what it does and when to use it, with trigger keywords).
- Optional: `license`, `compatibility` (max 500 chars, e.g. "needs uv; ffmpeg bundled"), `metadata` (string map), `allowed-tools` (experimental, space-separated, e.g. `Bash(uvx:*)`).
- Progressive disclosure: metadata about 100 tokens always loaded; body under 5000 tokens (and under 500 lines) loaded on activation; `scripts/`, `references/`, `assets/` loaded on demand. Keep references one level deep.
- Validate with `skills-ref validate ./skill`.
- Shared by Claude Code, Codex, Cursor, Copilot, Gemini CLI and others. `vercel-labs/skills` (38.8k stars) is the cross-agent installer: `npx skills add owner/repo` detects installed agents and copies the skill in. `anthropics/skills` has 191k stars, so the format has gravity.

Keep SKILL.md tiny: 40 to 60 lines, under roughly 600 tokens.
1. Frontmatter with a keyword-rich description (watch, video, YouTube, TikTok, screen recording, "what happens in this video", transcribe).
2. The one command: `uvx real-eyes watch <url> --budget 20k`.
3. How to read the output (3 lines) and how to zoom (`--at 12:30-13:10`).
4. "On error run `uvx real-eyes doctor`".
5. Everything else in `references/` (flags, platforms, troubleshooting).

Description trap: too vague and the agent never triggers it; too broad and it fires on every URL. Name the trigger: the user gives a video link or file and asks about its content.

### CLI distribution, zero-install

| Channel | Command | Notes |
|---|---|---|
| uv | `uvx real-eyes <url>` | Best default. uv has 91.8k stars and is the standard for Python tool runs. No venv, no global install |
| pipx | `pipx run real-eyes` | Fallback for people without uv |
| npm | `npx real-eyes` | Only if the core is JS, or ship a tiny npm shim that spawns `uvx`. A shim is cheap and reaches the Node crowd and MCP configs that expect `npx` |
| Homebrew | `brew install real-eyes` | Later; pulls ffmpeg + yt-dlp as deps (khou does this) |
| Docker | `docker run ghcr.io/<owner>/real-eyes` | For people with no ffmpeg; optional |

System deps are the real friction: ffmpeg and yt-dlp. Mitigations: depend on the `yt-dlp` PyPI package directly, and bundle ffmpeg through a binary wheel (`imageio-ffmpeg` or `static-ffmpeg`) so `uvx real-eyes` works with nothing preinstalled. mcp-video-analyzer does the npm equivalent with `ffmpeg-static`. Add `real-eyes doctor` that prints what is missing and the exact fix per OS.

Transcript chain, cheapest first: native captions (yt-dlp / youtube-transcript-api), then local `faster-whisper` (opt-in extra, `real-eyes[whisper]`), then an API (Groq/OpenAI) if a key is present. The default path never needs a key.

### MCP server

- Python FastMCP (official `modelcontextprotocol/python-sdk`, 24.8k stars) or the TypeScript SDK. Python keeps one codebase with the CLI: `real-eyes mcp` over stdio.
- Config users paste: `{"command":"uvx","args":["real-eyes","mcp"]}`.
- Keep it to 3 tools so the schema stays cheap: `watch(url, budget, at?)`, `transcript(url, range?)`, `frames(url, times[])`. Return images as MCP image content blocks, and also write them to disk and return paths for agents that cannot take inline images.
- Publish to the official MCP registry plus Glama and mcpservers.org, and open a PR on `punkpeye/awesome-mcp-servers` (it has a multimedia section).

### Claude Code plugin marketplace

- Add `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json` so users run `/plugin marketplace add <owner>/real-eyes` then `/plugin install real-eyes@real-eyes`. Bundle the skill, optionally the MCP config, and a slash command. claude-video, mcp-video-analyzer and claude-video-vision all do this; it is table stakes.
- Add `.codex-plugin/` too (claude-video does; Codex has `codex plugin marketplace add`).
- Submit to community marketplaces (claudemarketplaces.com, skills.sh, tessl) after the first release.

### Cross-agent files

- `AGENTS.md` at the repo root: read by Codex, Cursor, Copilot, Gemini CLI, Aider and others. Put the 5-line "how to use it" there plus "if you are an agent asked to install this, run: ...". khou/watch-video's install-by-asking flow works because of this file.
- `CLAUDE.md` can just say `@AGENTS.md`.
- `llms.txt` on the docs site, for agents that browse.
- For Cursor without skills support, a `.cursor/rules/` snippet in the docs.

### JSON output conventions

- stdout is data only; logs and progress go to stderr. Default is compact Markdown (agents read it well and it costs fewer tokens); `--json` gives one JSON document.
- Stable, versioned envelope, for example: `{"schema":"real-eyes/1","source":{},"duration_s":0,"engine":"","transcript":[{"t0":0,"t1":0,"text":""}],"frames":[{"t":0,"path":"","reason":"scene-change"}],"budget":{"requested":20000,"estimated_image_tokens":0},"warnings":[]}`.
- Timestamps as seconds (numbers) plus a human `mm:ss` string, so the agent can cite them.
- Exit codes: 0 ok, 2 bad input, 3 unreachable or private, 4 missing dependency (fix in `warnings`), 5 partial result (captions failed, frames ok).
- Frames written to a cache dir, absolute paths in the output, so any agent's image reader can open them. Inline base64 only as an opt-in flag.
- Cache keyed by URL plus options, so a second question about the same video costs nothing.
- Always print a `next` hint ("zoom: real-eyes watch <url> --at 12:30-13:10") so a weaker model knows what to do.

---

## 3. What makes a dev-tool repo look excellent

### README skeleton that works

1. Logo or wordmark plus a one-sentence tagline (verb first, concrete: "Let any AI agent watch a video from a URL").
2. Badge row, 4 to 6 max: PyPI version, license, CI, Python versions, "works with" agent badges. Skip vanity badges.
3. A hero demo directly under the tagline: a 10 to 20 second terminal recording or GIF showing the real loop (paste URL, agent answers with timestamps). Show the result, not the install.
4. One command to try it, copyable: `uvx real-eyes https://youtu.be/...`.
5. "Why" in 3 bullets, then a comparison table against claude-video, transcript-only tools and Gemini wrappers. Be fair and list where others win.
6. Per-agent install in a table or tabs (Claude Code, Codex, Cursor, Gemini CLI, any MCP client, plain CLI). claude-video's "Choose your app" table is the model, but keep it shorter.
7. How it works, one diagram (URL to captions/whisper, ffmpeg frames, budget fitter, output).
8. Token cost table (khou's idea).
9. A real output snippet.
10. Platforms, limits, privacy ("runs locally unless you pick an API engine").
11. Contributing, license.

Keep install short; push edge cases to docs.

### Demo recording tools

- VHS (`charmbracelet/vhs`, 21.3k stars): scripted `.tape` files render GIF/MP4/WebM deterministically, so the demo is reproducible in CI and never goes stale. Best choice for the hero.
- asciinema (17.9k stars): text-based recordings, tiny, selectable text, embeddable player; `agg` converts to GIF. Good for the docs site.
- For the agent UI (Claude Code itself), a screen capture as MP4/WebM plus a short GIF fallback. GitHub README GIFs under about 10 MB are safest.
- Make the demo show something a screenshot cannot: a 20-minute talk reduced to a timestamped answer.

### Social preview and repo metadata

- Social preview: 1280x640 PNG. Dark background, wordmark, tagline, a strip of 4 frames with timestamps.
- About box: description, website, topics (`agent-skills`, `mcp`, `claude-code`, `codex`, `video-understanding`, `youtube`, `yt-dlp`, `ffmpeg`, `whisper`, `llm-tools`).
- Registry badges and listings (Glama card, awesome-mcp-servers) double as backlinks.

### Docs site or landing page

- Single landing page (Astro or plain HTML on GitHub Pages or Cloudflare Pages): hero demo, install tabs, comparison, FAQ. Enough for launch.
- MkDocs Material or Starlight once docs outgrow a README; add `llms.txt`.
- Do not build a docs site before the CLI is stable. README plus `docs/` markdown first.

### The viewer idea (our differentiator)

A local web UI opened with `real-eyes view <url-or-run-id>`:
- A single static HTML file generated into the cache dir (no server needed), or a tiny `http.server` for local video playback.
- Layout: player top left; a horizontal timeline of frame thumbnails; transcript on the right, synced and clickable. Frames the agent actually requested get a highlight ring, and timestamps the agent cited get markers.
- Export as self-contained HTML (embedded thumbnails) that a human can share. kar2phi/video-lens shows people like HTML output from transcripts; ours adds frames.
- Why it wins: it makes the agent's perception inspectable ("what did my agent actually see?"). It is also the best demo GIF and the best debugging tool for the project.
- Later: a live mode where the viewer updates as the agent zooms into ranges.

### Exemplary READMEs to study

1. [charmbracelet/vhs](https://github.com/charmbracelet/vhs): animated hero that is the product's own output, tight tagline, tutorial built step by step.
2. [astral-sh/uv](https://github.com/astral-sh/uv): benchmark chart as the hero claim, one-line installs, short feature bullets linking to docs. The model for "boring to install".
3. [BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep) and [sharkdp/bat](https://github.com/sharkdp/bat): honest comparisons, screenshots right under the tagline, skimmable install tables.
4. In our category, [bradautomates/claude-video](https://github.com/bradautomates/claude-video) and [mcp-video-analyzer](https://github.com/guimatheus92/mcp-video-analyzer): study the install-by-app table and the registry badge row; avoid the front-loaded install length. [steipete/summarize](https://github.com/steipete/summarize) is worth a look for its one-line pitch.

---

## 4. Naming and availability

Checked 2026-11-10 against `pypi.org/pypi/<name>/json` and `registry.npmjs.org/<name>` (HTTP 404 means free), plus GitHub search and user lookups.

### real-eyes / RealEyes

| Where | Result |
|---|---|
| PyPI `real-eyes`, `realeyes`, `real_eyes` | Free (404). PyPI treats `real-eyes` and `real_eyes` as the same name |
| npm `real-eyes`, `realeyes`, `real_eyes` | Free (404) |
| GitHub repo named `real-eyes` | None found. Search hits are unrelated |
| GitHub user `real-eyes` | Taken: personal account from 2021, 3 unrelated repos. You would need another owner handle |
| GitHub org `Realeyes` | Exists: the company Realeyes (emotion/attention AI, realeyesit.com) |
| GitHub repos named `realeyes` | Small hobby repos (7, 3, 2, 0, 0 stars) |

Verdict: the package names are free, but the brand overlaps with a real company in adjacent AI/vision territory. Expect search confusion and a small trademark risk if the project grows. Fine as a tagline or CLI alias; I would not make it the primary brand unless you accept that risk. Domains were not checked.

### Five alternatives (free on both PyPI and npm at check time)

| Name | PyPI | npm | GitHub search | Notes |
|---|---|---|---|---|
| vidwatch | free | free | 3 hobby repos, 0 stars | Says what it does; matches the skill-name convention (`/vidwatch`) |
| vidlook | free | free | a few 0-star repos | Short; "look at this video" |
| watchframe | free | free | 2 repos, max 1 star | Hints at both watching and frames |
| clipsight | free | free | 3 repos, 0 stars | Brandable, "insight from a clip" |
| vidscope | free | free | 3 repos, max 2 stars | Short; "scope" suggests zooming into a time range |

Checked and rejected: `lookat`, `eyeball`, `lookie`, `watchit`, `scenery`, `sightline`, `framesight` (taken on PyPI and/or npm). `seeit`, `lookingglass`, `vidcap`, `clipwatch` are partly free but taken on npm or PyPI, which breaks a matching `uvx` plus `npx` pair. `eyesight` is free on both but `chriswritescode-dev/opencode-eyesight` (38 stars) is a near neighbor in the agent space. `seevideo`, `eyes-on`, `vidsee` are free but weaker names.

Pick if real-eyes is dropped: vidwatch (clearest, and the skill name `watch` stays natural) or vidscope (more brandable). Before committing, check the domain, the GitHub org/handle, and run a quick trademark search.

### Name hygiene

- Reserve the same string on PyPI, npm, GitHub and a domain on day one; publish a 0.0.1 placeholder to PyPI and npm to hold the name.
- The skill directory name must equal the `name` in SKILL.md and be lowercase-hyphen, so the name has to survive that constraint.
- Keep "claude" out of the name. The tool should read as agent-agnostic; the claude-video name caps its own reach.

---

## 5. Suggested next moves

1. Decide the name (section 4) and grab PyPI, npm, GitHub and a domain.
2. Build the CLI core: stable JSON envelope, `--budget`, `--at` zoom, `doctor`, bundled ffmpeg, caption-first transcript chain.
3. Write a 40-line SKILL.md plus AGENTS.md; add `.claude-plugin` and `.codex-plugin` manifests.
4. Build a test corpus aimed at claude-video's known failures (text-only slide changes, multi-language captions, no-caption TikTok, FFmpeg 7+, Linux) and publish results in the comparison table.
5. Ship the viewer as the hero demo; record it with VHS.
6. List in awesome-agent-skills, awesome-mcp-servers, Glama and skills.sh.
