# 04 - Fetching media without auth (research for real-eyes)

Research date: 10 Nov 2026. Sources are mostly yt-dlp's own wiki, issues and release notes, plus a handful of third-party blogs. Where a claim rests on a blog only, it is marked "unverified". Nothing here was tested live. Run a smoke test before you trust any row in the tables.

## TL;DR

- yt-dlp is still the only backend that covers nearly every site, and it is the right default. Install with `pip install "yt-dlp[default,curl-cffi]"` (the `default` extra ships the JS challenge solver, `yt-dlp-ejs`; the `curl-cffi` extra enables browser impersonation).
- YouTube is the hard one. In practice it works from a home machine, and often fails from cloud IPs with "Sign in to confirm you're not a bot". Design for that: try the cheap path first (captions and metadata), then yt-dlp, then fall back to telling the user what to run locally.
- Do not download whole videos. For an agent that "watches", you need (a) captions or an audio track for speech, and (b) sparse frames. Both can be had with a fraction of the bytes.
- Everything outside YouTube is mostly easy for public content: TikTok, Instagram public posts, X video posts, Reddit, Vimeo, Twitch VODs/clips, Loom, direct mp4/m3u8 all work in yt-dlp without credentials, at least per the release notes and a late-Oct 2026 status post.

## 1. yt-dlp state in 2026

Latest stable seen: **2026.10.26** (26 Oct). Before it: 2026.10.21, 2026.08.19. Release cadence is roughly monthly with fast fixes in nightly/master builds. Recent notes:

- 2026.10.26: curl_cffi 0.17.x supported (bundled binaries ship 0.17.0). Python 3.10 dropped, **3.11+ required**. Windows 10+ for official binaries.
- 2026.10.21: new `tv_samsung` YouTube client added to defaults; `web_embedded` switched to a Safari UA; a warning that old executables are vulnerable to MITM through the self-updater (reinstall manually).
- 2026.08.19: `visionos` client added; **`android_vr` removed from default clients**; TikTok extractor and share-URL fixes; Instagram logged-in fix; Vimeo `ios`/`macos` clients removed.

### JS challenge solving (the new hard requirement)

Since late 2025, full YouTube support needs an **external JavaScript runtime** to solve the signature and "n" challenges. It only applies to YouTube. From the EJS wiki:

| Runtime | Status |
|---|---|
| Deno >= 2.3.0 | Recommended, on by default |
| Node >= 22 | Opt in with `--js-runtimes node` |
| QuickJS / QuickJS-NG | Opt in, binary must be named `qjs` |
| Bun 1.2.11 - 1.3.14 | Deprecated |

The solver scripts come from `yt-dlp-ejs`. Standalone binaries bundle it, and `pip install "yt-dlp[default]"` pulls it in. You can also use `--remote-components ejs:npm` (Deno/Bun only) or `ejs:github` to fetch them at runtime.

Two things to plan for. First, this breaks the "zero setup beyond pip/uvx" goal for YouTube specifically, because Deno or Node must exist on PATH. If Node 22+ is already there, great; otherwise real-eyes should detect the missing runtime and print an exact one-line install hint (or try a pip-installable runtime, see section 7). Second, Deno's maintainers announced they will wind down development in about a year (yt-dlp issue #17799, opened 9 Oct 2026). A maintainer said Deno remains the recommended runtime for fresh installs for now, so expect the default to change by late 2027. Treat "which runtime" as a detect-and-pass-flag concern, not a hardcoded one.

### PO tokens and player clients

From the PO Token Guide (last edited 12 Jul 2026):

- Need a GVS (streaming) PO token: `mweb`, `tv_simply`, `web_music`, `web_creator`; `android` and `ios` need one for player or GVS requests.
- `web_safari` HLS formats currently do not need a GVS token. `web` only offers SABR formats.
- No token needed, with caveats: `web_embedded` (only embeddable videos), `android_vr` (no "made for kids"), `tv` (without logged-in or guest cookies, formats can be DRM'd or SABR-only).
- Tokens are now bound to the video ID, so hand-copied tokens are no longer a viable approach. Anything that needs a token would need a **PO token provider plugin** (for example `bgutil-ytdlp-pot-provider`, which needs a helper process). That is exactly the kind of setup real-eyes wants to avoid, so do not depend on it.

Reality check on `android_vr`: issue #17348 (Aug 2026) shows yt-dlp marking `android_vr` https formats as requiring a GVS token, with only **format 18** (360p, 640x360, H.264/AAC, pre-merged mp4, ~11 MiB for a short clip) coming through unless you override. The workaround is `--extractor-args "youtube:player-client=android_vr;formats=missing_pot,duplicate"`. Format 18 is a handy accident for us: 360p with audio in a single progressive file is all a "watching" agent needs. Still, assume it can vanish any month.

Takeaway: do not force clients. Let yt-dlp's default client list run, and only add an explicit retry ladder (`web_safari`, `tv_samsung`/`tv`, `android_vr` with the override, `web_embedded`) on failure.

### Datacenter IP blocking

Evidence is consistent but mostly anecdotal. One 2026 write-up says YouTube returns LOGIN_REQUIRED at the player API for datacenter IPs before any stream URL is returned (unverified blog). The `youtube-transcript-api` README itself says YouTube has begun blocking most cloud-provider IPs (RequestBlocked / IpBlocked), and its issue tracker is full of "works on laptop, fails on AWS". Free datacenter proxies are blocked too; residential proxies are the usual paid workaround. I found no source confirming that any client works from a datacenter IP without login in Nov 2026.

OAuth login support was removed from yt-dlp, and cookies are out of scope for this project, so the only real lever is "run on the user's own IP".

### Impersonation (curl_cffi)

yt-dlp can mimic Chrome/Safari TLS and HTTP/2 fingerprints via curl_cffi (`--impersonate chrome`). It is used by extractors that sit behind Cloudflare-style checks (SoundCloud and Bandcamp were fixed that way in 2026) and it helps with some generic-extractor and direct-URL cases. It is not needed for YouTube. Install `curl-cffi` as an extra; the supported version range moves with each release (0.16.x then 0.17.x in 2026), so pin through the extra instead of by hand.

## 2. Alternatives

| Tool | Verdict |
|---|---|
| **cobalt (cobalt.tools)** | API is `POST /` with `{url}` returning `tunnel`/`redirect`/`picker`. Auth is optional per instance, but the official hosted instance (api.cobalt.tools) uses bot protection and the docs say it is "not intended to be used in other projects without explicit permission". Self-hosting is a Docker/Node service, not pip. Good as an *optional* user-configured fallback (`REAL_EYES_COBALT_URL`), never as a built-in dependency. |
| **Invidious / Piped** | Public instances are flaky. One 2026 comparison claims Invidious public instances collapsed to about 3 because of YouTube IP blocking; Piped has more but the number is from a single blog (unverified). Self-hosting on a residential IP works but is more setup than yt-dlp. Optional fallback for captions and metadata only. |
| **youtubei.js (Node)** | Active (1.7k+ commits), but I could not confirm release dates or PO-token handling from the page. It faces the same IP and PO-token walls; no real advantage over yt-dlp for us and it drags in Node. Skip. |
| **pytubefix** | Python, about 1,000 commits, small issue count. It supports OAuth, which is out of scope. Could not verify PO-token behavior. Not worth carrying as a second YouTube engine. |
| **youtube-transcript-api** | Pure Python, tiny, fetches captions without video streams. Same cloud-IP blocking, but fine from home. This is the best *first* step for YouTube because it avoids media entirely. |
| **lux, you-get** | Mainly useful for Chinese platforms (Bilibili, Youku, etc.). Slower-moving than yt-dlp. Not needed for v1. |
| **gallery-dl** | Great for image-centric sites (Instagram/X/Reddit images). Video support exists but yt-dlp is better for that. Optional fallback for image posts and carousels. |
| **yt-dlp forks / nightly** | Nightly and master builds (`yt-dlp-nightly-builds`, `yt-dlp-master-builds`) get extractor fixes days before stable. Support `--update-to nightly` when an extractor fails. |

## 3. Per-platform notes (anonymous access)

Based on the yt-dlp release notes and a late-Oct 2026 status post; not live-tested.

| Platform | Anonymous status | Notes |
|---|---|---|
| YouTube | Public videos work with default clients on a residential IP | Needs JS runtime. Age-gated, private, members-only need cookies: out of scope, report "needs login". Cloud IPs likely hit bot-check. |
| TikTok | Public videos and short links (`vm.tiktok.com`) work | Challenge solving is native Python, no JS runtime needed. Extractor breaks and gets fixed often; use nightly. |
| Instagram | Public posts and reels work without login | Private accounts need cookies. Extractor reworked in 2026, so expect churn. Stories/profiles generally need login. |
| X / Twitter | Video posts and broadcasts work | Login support removed. Text-only posts are not extracted (which is fine, nothing to watch). |
| Facebook | Public videos work | Built-in login removed. Many "public" videos still redirect to login. Expect a low success rate. |
| Reddit | Anonymous extraction works again | v.redd.it serves video and audio as separate DASH streams; yt-dlp needs ffmpeg to merge. |
| Vimeo | Public URLs work | Password or private videos need credentials. |
| Twitch | Public VODs and clips work | Sub-only VODs do not. Live streams are out of scope for "watch this". |
| Loom | Public share links should work (extractor exists); I found no 2026 breakage reports | Loom pages expose an HLS/MP4 URL through a GraphQL call that does not require login for public videos. Verify. |
| Direct mp4/m3u8 | Works | Hand it straight to ffmpeg; no extractor needed. |
| Podcasts | RSS feed enclosure is a plain mp3/m4a URL | For Apple Podcasts links, hit the iTunes Lookup API (`https://itunes.apple.com/lookup?id=<id>&entity=podcast`) to get `feedUrl`, then parse the RSS and pick the episode. No auth, no keys. |
| SoundCloud / Bandcamp | Work, with impersonation | Fixed in 2026 using curl_cffi. |

## 4. Not downloading the whole thing

The agent needs three things: speech content, visual content, and metadata. None requires the full file.

1. **Captions first.** For YouTube, uploader subtitles or auto-captions via `yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "en.*" --sub-format json3/vtt` or `youtube-transcript-api`. Zero media bytes. Many other sites (Vimeo, Twitch no, TikTok sometimes, Loom has transcripts) expose subtitle tracks too. If captions exist, the "audio" step can be skipped entirely.
2. **Audio-only stream for ASR.** `-f "ba[abr<=64]/worst[ext=m4a]/ba"` plus `--extract-audio --audio-format m4a` or, better, no re-encode. A 1-hour talk at about 48-64 kbps is roughly 25-30 MB. Run it through ffmpeg to 16 kHz mono before sending to a speech model.
3. **Low-res video for frames.** `-f "bv*[height<=360][vcodec^=avc1]/worst[height>=240]"` video-only, or the progressive format 18 on YouTube. 360p is plenty for slides, UI, and scene changes. Save a lot more by not asking for audio on this one.
4. **Range / partial downloads.** `--download-sections "*00:10:00-00:12:30"` cuts a window using byte ranges where the container allows it (for HLS/DASH it fetches only the needed fragments; for progressive mp4 it needs the moov atom at the front). Useful for "look at this part".
5. **ffmpeg directly on the stream URL.** Get the URL with `yt-dlp -g -f ...` (or `-J` for JSON), then `ffmpeg -ss 600 -i "<url>" -frames:v 1 out.jpg` for single frames, or `-vf fps=1/10` for a sparse timeline. Input seeking over HTTP uses range requests, so it only reads what it needs. Caveats: (a) YouTube URLs are signed, expire in about 6 hours, and are IP-bound, so you must fetch from the same machine that resolved; (b) some CDNs require headers (`--add-header` / ffmpeg `-headers`) which yt-dlp reports in `http_headers`; pass them through; (c) DASH-only audio+video need two inputs, and fragmented formats may not seek cheaply, so cap the work with `-t`.
6. **Scene-aware sampling** keeps frame counts low: `ffmpeg -vf "select='gt(scene,0.3)',scale=-2:360" -vsync vfr` on the 360p file, plus a fixed-rate fallback (1 frame / 10-30 s). Cap total frames.

Suggested default budget: audio <= 64 kbps plus 360p video-only, with a hard size cap and duration cap, both configurable.

## 5. Residential machine vs cloud sandbox

| | User's own machine | Cloud sandbox / CI / agent container |
|---|---|---|
| YouTube | Mostly works (with JS runtime) | Frequently blocked ("Sign in to confirm you're not a bot"); captions-only may still work for some videos |
| TikTok / Instagram / X | Works | Mixed; Instagram and X are the most likely to rate-limit or redirect to login |
| Reddit, Vimeo, Twitch, Loom, direct URLs, podcasts | Works | Usually works |
| Signed-URL tricks (ffmpeg on stream URL) | Works, same IP | Works only if resolver and ffmpeg share the IP |

If real-eyes is invoked as an MCP server or CLI from the user's own agent (Claude Code, Cursor, Codex on a laptop), it inherits the residential IP, and that is its strongest selling point. In cloud sandboxes it should degrade honestly rather than fake success.

## 6. Legal and ToS, short version

Downloading from YouTube, TikTok, Instagram and similar platforms generally violates their terms of service even when no login is involved, and circumventing technical measures (PO tokens, DRM) can raise anti-circumvention issues in some jurisdictions; copyright still applies to the content you fetch. Mitigations that fit this tool: run on the user's own machine and IP, fetch only what is needed for personal analysis (captions, a low-bitrate audio track, a few frames), never redistribute or persist media by default (use a temp dir, delete after), avoid DRM'd content, and put a short notice in the README that users are responsible for complying with the terms of the sites they use. Not legal advice.

## 7. Recommended architecture: the resolver ladder

Goal: `uvx real-eyes <url>` or `pip install real-eyes` and go. Hard dependencies are only pip packages: `yt-dlp[default]`, `curl-cffi`, `youtube-transcript-api`, `httpx`, `feedparser` (or stdlib XML), and `imageio-ffmpeg` (ships a static ffmpeg binary through pip, so no system ffmpeg is needed). Optional extras, never required: a user-set cobalt URL, nightly yt-dlp.

### Step 0: classify the URL

Regex/host routing to one of: `youtube`, `direct`, `podcast`, `social` (TikTok/IG/X/FB/Reddit/Vimeo/Twitch/Loom/other). Probe `HEAD` for unknown URLs; if `Content-Type` is `video/*`, `audio/*`, or `application/vnd.apple.mpegurl`, treat it as `direct`.

### Step 1: per-type ladders

**Direct mp4/m3u8/mp3**: ffmpeg straight on the URL with `-ss`/`-t` and range requests. No yt-dlp. Fall back to yt-dlp's generic extractor (with `--impersonate chrome`) if it returns 403.

**Podcast**: Apple Podcasts URL -> iTunes lookup -> RSS -> enclosure URL -> audio ladder. RSS URL given -> parse -> enclosure. Spotify is DRM'd; do not try.

**YouTube** (the careful one):
1. Metadata and captions via `youtube-transcript-api` (no media, fastest). If captions exist and the task is speech-only, stop here.
2. `yt-dlp` with default clients, `-f` picking small audio and 360p video (section 4), JS runtime auto-detected (`deno`, then `node >= 22`, then `qjs`) and passed via `--js-runtimes`.
3. Retry with explicit clients in order: `web_safari` (HLS, no GVS token needed today), `tv_samsung`/`tv`, `android_vr` with `formats=missing_pot,duplicate` (yields format 18), `web_embedded`.
4. Optional user-configured fallbacks: cobalt instance, Invidious/Piped instance for captions and metadata.
5. On "not a bot" or LOGIN_REQUIRED: stop and return a structured error, `{"error":"ip_blocked","hint":"Run this on your own machine; cloud IPs are blocked by YouTube"}`, plus whatever partial data was obtained (title, description, chapters, captions). Never silently return empty frames.

**Social/other** (TikTok, Instagram, X, Facebook, Reddit, Vimeo, Twitch VOD/clip, Loom, SoundCloud, hundreds more): `yt-dlp` with `--impersonate chrome` when curl_cffi is available. On extractor failure, self-update to nightly once (`yt-dlp --update-to nightly`, or pip install `yt-dlp` nightly into the tool's own venv) and retry. For image-only Instagram/X/Reddit posts, optionally `gallery-dl`. If it still fails, return `needs_login` or `unsupported` with a clear message, never a stack trace.

### Step 2: normalise output

Whatever the backend, hand the rest of real-eyes the same bundle: `{audio.m4a (or captions), video360.mp4 (video-only, optional), metadata, chapters, source, backend_used, warnings}`. Frame extraction and ASR are separate stages that do not care how the bytes arrived.

### Graceful degradation order

full audio + frames -> audio + captions only -> captions only -> metadata + description only -> structured error with a hint. Each downgrade is reported in `warnings`, so the calling agent knows what it did and did not see.

### Operational rules

- Pin a minimum yt-dlp, but check for staleness: if the installed version is older than about 60 days, warn; offer `--update`.
- One shared retry/backoff policy, polite rate limits, per-run temp dir, cleanup on exit, size and duration caps.
- `doctor` command: reports Python version (3.11+), yt-dlp version, JS runtime found, curl_cffi present, ffmpeg source, whether the IP looks blocked (probe a known-public YouTube video with `--skip-download`).
- No cookies, header tokens, or API keys are accepted anywhere in the API. If the user wants those, that is a different tool.

## 8. Open questions to test before building

1. Does `web_safari` HLS still work token-free from a residential IP today, and what resolutions does it give? (PO Token Guide says yes as of Jul 2026.)
2. Is a pip-installable JS runtime available (QuickJS wheels such as `quickjs`/`pyquickjs`, or a `deno` PyPI wrapper) so YouTube works with truly zero setup? yt-dlp requires a `qjs`-named executable for QuickJS, so a wheel that ships the binary would be needed. Not verified.
3. How much of the Loom, Facebook and Instagram flow survives from a cold IP? Build a tiny nightly CI matrix of 10 public URLs per platform (run from a home runner, not GitHub-hosted, which is a datacenter) to catch breakage early.
4. Does `youtube-transcript-api` still work from a home IP after the 2026 PO-token changes for captions? Reports of empty transcripts suggest it sometimes fails; yt-dlp's `--write-auto-subs` is the backstop.

## Sources

- yt-dlp EJS wiki: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- yt-dlp PO Token Guide: https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide
- yt-dlp releases: https://github.com/yt-dlp/yt-dlp/releases
- Deno deprecation discussion: https://github.com/yt-dlp/yt-dlp/issues/17799
- android_vr GVS token issue: https://github.com/yt-dlp/yt-dlp/issues/17348
- Upcoming YouTube requirements announcement: https://github.com/yt-dlp/yt-dlp/issues/14404
- cobalt API docs: https://github.com/imputnet/cobalt/blob/main/docs/api.md
- yt-dlp platform status, Oct 2026 (third-party): https://www.huntapi.com/blog/yt-dlp-platforms-october-2026
- Datacenter IP block write-up (third-party, unverified): https://ansaribilal.com/blog/ytagent-datacenter-ip-block-youtube-ai-agents-2026/
- youtube-transcript-api: https://github.com/jdepoix/youtube-transcript-api
- Invidious vs Piped (third-party): https://dev.to/selfhostingsh/invidious-vs-piped-4ijn
