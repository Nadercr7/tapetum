# Research 08: "Paste a link, get the transcript" web services

Research date: 2026-11-10. Sources: WebFetch of vendor pages, plus direct `curl` probes from this machine (home IP, desktop-Chrome user agent). Anything I could not confirm is marked **(unverified)**. Complements 01 (sources) and 06 (owner-suggested sites).

## TL;DR

- Every service here does the same thing underneath: it fetches YouTube captions (or runs Whisper when none exist) from its own proxied servers, then wraps them in a page or an API. None of them has data tapetum can't get itself from the user's IP.
- **Not one of them can be called by a program without a key or a browser.** Probed live: youtubetotranscript.com (Cloudflare 403), youtube-transcript.io (401), transcriptapi.com (401), Supadata (401), kome.ai (Vercel checkpoint 429), summarize.tech (503, deployment paused). Details below.
- The real value in this survey is **UX features** we can copy locally for free: language choice with translation, timestamps toggle, SRT/VTT/JSON/TXT/Markdown export, clickable timestamps, chapter-style summaries, search in transcript.
- Hosted APIs are priced per request ($1.50 to $5 per 1,000 transcripts). That makes them an acceptable opt-in "bring your own key" tier at best.

## Live probe results (what a program actually gets)

| Target | Request | Result |
|---|---|---|
| youtubetotranscript.com | `GET /transcript?v=jNQXAC9IVRw&current_language_code=en` | **403 "Just a moment..."** Cloudflare managed challenge. The homepage (`/`) returns 200, but the transcript page needs a real browser. WebFetch also got 403. The form is a plain GET to `/transcript`. Dead end for plain HTTP. |
| youtube-transcript.io | `POST /api/transcripts` body `{"ids":["jNQXAC9IVRw"]}` | **401 "Unauthorized, no token provided"**. Needs `Authorization: Basic <token>`. |
| transcriptapi.com | `GET /api/v2/youtube/transcript?video_url=ID` | **401 `{"detail":"Not authenticated"}`**. Needs `Authorization: Bearer <key>`. |
| Supadata | `GET https://api.supadata.ai/v1/transcript?url=...` | **401 "Missing API Key"**. Needs `x-api-key`. |
| kome.ai | any path | **429 Vercel Security Checkpoint** (bot wall). |
| summarize.tech | `/www.youtube.com/watch?v=ID` | **503 DEPLOYMENT_PAUSED** on 2026-11-10. The service itself is down right now, so it is a live example of why not to depend on these. |
| tactiq.io free tool | page fetch | Static Astro page, 200. Transcript fetching happens client-side or via an endpoint I could not find in the HTML. Not usable as an endpoint. |
| downsub.com | page fetch | 200, prerendered Vue app. No visible API; real work is on `app.downsub.com` (Pro). The `subtitle.to/` URL prefix trick is advertised on the homepage. Behaviour **(unverified)**. |
| notegpt.io | page fetch | 200, 860 KB Nuxt page. The transcript call is made by JS to a private API **(unverified)**. |

Conclusion: nothing here is "stable and scrapeable." The ones that are free are behind bot walls, the rest need keys.

## Service by service

| Service | How it works | Free tier | Languages / Arabic | Output | API / MCP | Stability for us |
|---|---|---|---|---|---|---|
| **youtubetotranscript.com** | Paste link, page shows transcript beside embedded player. Copy button. | Free, no signup, no stated cap | Language switch; claims translate to 125+ languages. Arabic not named, but the auto-translate set normally includes it | Copy to clipboard only (download "planned") | No API. Paid API is the sibling transcriptapi.com | Cloudflare challenge. **Do not scrape.** |
| **transcriptapi.com** | REST wrapper over YouTube, plus search/channel/playlist endpoints | 100 credits, no card | `language=de,en,asr` preference list; `/info` lists available languages free | JSON: `language`, `length_seconds`, `metadata.title`, `transcript[]` of `{text,start,duration}`; with or without timestamps | REST + **MCP server** at `https://transcriptapi.com/mcp` (OAuth for Claude/ChatGPT, key for others). $5/mo for 1,000 credits, top-up $1.50 to $2.50 per 1,000. 200 to 300 RPM | Key required. Stable enough as paid option. Vendor blog posts comparing competitors are marketing, not neutral. |
| **Supadata** | REST; also handles TikTok, Instagram, X, Facebook, public file URLs | Free tier exists, size **(unverified)**; docs page silent | `lang` (ISO 639-1); `availableLangs` returned | JSON segments `{text, offset ms, duration ms, lang}` or plain text (`text=true`), `chunkSize`. `mode=native/generate/auto` (auto falls back to AI transcription; 2 credits per generated minute). Async: 202 + `jobId`, poll, kept 1 hour | REST. MCP **(unverified)**, docs don't mention it | Key required. Closest to what tapetum does (multi-platform + AI fallback). Good design reference. |
| **youtube-transcript.io** | Web UI plus batch API | Web: free; API pricing not on the page | Not documented on the API page | Response shape not documented publicly | `POST /api/transcripts` with up to 50 `ids`, Basic token, 5 req / 10 s, 429 + `Retry-After`. Channel endpoint on paid plans. No native MCP (per a competitor's comparison) | Key required. The 50-ids-per-request batch is a nice API idea. |
| **Tactiq** | Free web tool plus the Chrome meeting-transcription extension | 25 free transcripts, no signup | Not stated on the tool page | Download `.txt`; AI summary upsell; bulk (channel/playlist/CSV) on `/bulk` | Has `/api`, no docs in what I could read | Marketing funnel for the meetings product. Nothing to depend on. |
| **DownSub** | Paste URL, pick language and format, download. 35+ sites listed (Viki, Viu, WeTV, Hotstar, Vimeo, TikTok, Dailymotion) | Free, no stated caps | Lists whatever subtitle tracks the video has; separate translator at editsub.com | **SRT, VTT, TXT** | Pro at app.downsub.com; no public docs | Ad-heavy; useful mainly for non-YouTube platform subtitles. Fragile to scrape. |
| **SaveSubs** | Subtitle downloader, many sites | Free | Per-video tracks | Subtitle files | None known | Page is a JS loading shell; could not read it. **(unverified)** |
| **NoteGPT** | Free transcript page plus AI summary, notes, cloud storage | "Unlimited," no numbers | "Multiple languages," not listed; translation not mentioned | `.txt`, with or without timestamps; claims "multiple formats" | None mentioned | Private JS API behind a SPA. Has an AI-transcription fallback for videos without captions. |
| **Glasp** | Browser extension (Chrome, Edge, Firefox, Safari) plus web page and mobile app | 3 summaries/7 days, 3 AI sends/day, **5 transcript copies or downloads/day**; paid from $15/mo | Transcript in any language YouTube offers; summary language can differ | Copy, **Markdown, HTML, CSV, JSON**; export to Notion, Obsidian, Roam, mem.ai | A developer API is linked; nothing public I could verify | The best UX of the group (see features below). Daily caps make it useless to an agent. |
| **summarize.tech** | URL prefix trick (`summarize.tech/` + YouTube URL) gives a timestamped, section-by-section summary | Free | English-centric **(unverified)** | Summary per segment with timestamps | None | Down today (503). Its idea is good, its availability is not. |
| **Eightify** | Extension plus web; AI key-ideas summary with timestamps | Limited free summaries **(unverified)** | **(unverified)** | Summary | None known | Summary product, not a transcript source. |
| **Kome** | Free transcript/summary page | Free **(unverified)** | **(unverified)** | **(unverified)** | None | Vercel bot wall, 429. |
| **TubeTranscript** | Free transcript page, ad-supported | Free | **(unverified)** | Text | A community MCP exists under that name (mcpservers.org) | Ad-heavy page. |
| **TurboScribe** | Real Whisper transcription; accepts YouTube links | 3 files/day, 30 min each | 98+ languages (Arabic **unverified**) | TXT, DOCX, PDF, SRT, CSV (typical) | Login required | Genuinely different: it transcribes audio, not captions. Needs an account. |
| **TubeScript (tubescript.cc)** | Checks captions first, falls back to AI | 2 free/day, up to 2-hour videos | "Any language" (vendor claim) | Text | None | Daily cap. |

Other things found:

- **Apify actors** (e.g. johnvc "YouTube Transcript & Subtitles Scraper", from about $2 per 1,000 videos; failed videos not charged) and several Apify-hosted MCP servers ($50 per 1,000 transcripts at the high end). Need an Apify token.
- **Commercial YouTube MCP servers** (vidIQ, NexLev, OutlierKit, TubeLab) use OAuth, not keys, but they are channel-analytics products at $29 to $99/mo. Not relevant to a zero-auth tool.
- **Community MCP servers** (`jkawamoto/mcp-youtube-transcript`, `kimtaeyoon83/mcp-server-youtube-transcript`) run locally. This is the same shape as tapetum, so it is the real competition in the MCP space. Some of them want a YouTube Data API key; tapetum shouldn't.
- **Telegram/Discord bots:** nothing with traction found. What exists is either n8n workflows (Supadata or yt-dlp, then GPT summary) or self-hosted bots (yt-dlp + Whisper, e.g. FlyingFathead's whisper-transcriber-telegram-bot) and small paid ones (Youtubetalk, $5/mo after trial). Pattern to note: all of them are "URL in, summary out," and they all rely on yt-dlp or a paid API. No new transcript source.

## What the response shapes tell us

Two shapes are in the wild, and tapetum's JSON should be easy to map to both:

- transcriptapi: `{language, length_seconds, metadata:{title}, transcript:[{text, start(sec), duration(sec)}]}`
- Supadata: `{lang, availableLangs, content:[{text, offset(ms), duration(ms), lang}]}`

Take-away: keep our own canonical segment `{start, end, text}` in seconds, and return `availableLangs` plus the language actually used, so the agent knows whether it got a native or translated track.

## Features tapetum should adopt

1. **Language selection with a priority list** (`ar,en`), and report which was returned. Arabic matters here: ask for `ar` first, fall back to auto-generated `ar`, then translate from the original. Always surface whether the text is human captions, auto-captions, translated, or Whisper output.
2. **Auto-translate** as a flag (`--translate-to ar`). YouTube's own translated tracks cost nothing and cover about 125 languages, which is what youtubetotranscript advertises. Only use an LLM or local model for translation when YouTube has no track.
3. **Export formats:** JSON (canonical), plain text, SRT, VTT, Markdown. DownSub covers SRT/VTT/TXT, Glasp covers MD/HTML/CSV/JSON; the union is cheap to produce from one segment list.
4. **Timestamps on or off.** Agents often want clean prose, sometimes timecodes for citations. NoteGPT and transcriptapi both offer the toggle.
5. **Clickable, linkable timestamps:** emit `https://youtu.be/ID?t=123` per segment (or per chunk) in Markdown output. Glasp's answers cite timestamps; that makes agent answers verifiable.
6. **Chapters:** use the video's own chapter list when it exists, otherwise chunk by silence or time. Provide transcript grouped by chapter. This is the useful half of summarize.tech/Eightify without needing their LLM.
7. **Search in transcript:** `tapetum find URL "query"` returning matching segments with timestamps. Cheap, local, and very helpful for long videos where an agent should not read 2 hours of text.
8. **Chunking** (Supadata's `chunkSize`) so long transcripts fit in an agent's context.
9. **Async mode with job IDs** only if we add Whisper fallback, since that is slow; Supadata's 202 + poll design is a decent reference.
10. **Batch input** (many URLs in one call, like youtube-transcript.io's 50 ids), with per-item errors.
11. **Honest status field** on failure: blocked IP vs. no captions vs. private video. Supadata even bills a 206 "unavailable" result; we should at least be explicit.

## What we should deliberately NOT depend on

- **youtubetotranscript.com, kome.ai, summarize.tech, NoteGPT, Tactiq's free page, DownSub, SaveSubs web UIs.** Bot walls (confirmed on the first two), paused deployments (confirmed on summarize.tech), private JS APIs, ad pages, and no stability promise. At most a documented last-ditch optional plugin, off by default, disabled automatically when it returns a challenge page.
- **Any paid API in the default path** (transcriptapi, Supadata, youtube-transcript.io, Apify). They break the zero-auth promise, and their pricing changes (the sources I found disagree on transcriptapi's plan details). Offer them as opt-in adapters behind an env var, e.g. `TAPETUM_SUPADATA_KEY`, specifically for the case of datacenter IPs, where Supadata's multi-platform + AI fallback is the most compatible design.
- **Vendor comparison blogs** as facts: the pricing/MCP claims I could verify came mainly from transcriptapi's own marketing.
- **Browser extensions (Glasp, Tactiq, Eightify)** as a source: they work because they run inside the user's logged-in browser. That is a UX model to copy, not a data source.
- **Daily-capped freemium tiers** (Glasp 5 downloads/day, TurboScribe 3 files/day, TubeScript 2/day): unusable for agents.

## Positioning note

The gap in the market: the commercial services are keyed APIs, and the free ones are for humans behind bot walls. A local, key-free, MCP-capable tool that tries captions, then yt-dlp, then Whisper, and exposes search and chapters, doesn't have a direct hosted equivalent. The nearest are the two community MCP servers above, which only do captions.

## Open items

- Supadata free tier size and MCP status: not confirmed.
- Arabic explicitly supported by TurboScribe, NoteGPT, Kome, Eightify, TubeTranscript: not confirmed.
- DownSub `subtitle.to/` trick and SaveSubs behaviour: not tested.
