# real-eyes research 01: Transcript sources from a bare URL (zero auth)

Research date: 2026-11-10. Stars/licenses/last-push come from the GitHub API on that date. Anything marked **(unverified)** comes from vendor blogs or secondary sources and should be tested before we rely on it.

## TL;DR

- **YouTube is the only hard problem.** Everything else is either easy (podcast RSS, Vimeo/Twitch/TikTok via yt-dlp) or login-gated no matter what we do (Instagram, much of X and Facebook).
- **From a home/residential IP**, `youtube-transcript-api` and `yt-dlp --skip-download --write-auto-subs` both work with no cookies. This is the normal real-eyes case: the agent runs on the user's machine.
- **From a datacenter IP** (CI, cloud agent sandboxes), YouTube blocks most requests outright. Neither library fixes this. A residential proxy, or a fallback that doesn't touch YouTube from our IP, is the only reliable answer.
- **PO tokens are the new wrinkle.** Some caption tracks (`exp=xpe` in the track URL) return an empty HTTP 200 without a runtime-generated token. Upstream issue is still open (see below).
- **Whisper is the universal last resort**, but you still need the audio, and for YouTube that has the same IP and PO-token problems as captions.

---

## 1. Websites/services where you paste a link and get a transcript

None of these are a clean "free, no-login, stable API". Most free web tools have daily caps and are meant for humans, not agents. Treat them as last-gasp fallbacks, never the primary path.

| Service | Free? | Programmatic? | Arabic | Notes |
|---|---|---|---|---|
| TubeScript (tubescript.cc) | 2 free/day, no signup (unverified) | Web UI only | Yes, any language | Fine for a human, useless for an agent at volume |
| Apify actors (`akash9078/youtube-transcript-scraper`, `locaihost/youtube-transcripts`, `tidytools/youtube-transcript`, `openkrill/youtube-transcripts` and others) | Advertised "no API key, no login" for the *video*, but calling Apify itself needs an Apify token and costs roughly $1.50 to $4 per 1,000 transcripts (unverified) | Yes (HTTP API) | Several list Arabic, some offer translate-to | Breaks the zero-key rule for the end user. Could be an opt-in tier. |
| Commercial APIs (Supadata, Tactiq, OutlierKit, transcriptapi.com) | Free tiers exist but need an API key | Yes | Yes | Key required, so out for the default path. I did not get current pricing for Supadata/Tactiq. |
| Generic "YouTube to transcript" sites (youtubetotranscript.com style) | Free, ad-supported | Scrapeable in theory, but they sit behind Cloudflare/captchas and change often | Usually | Fragile. If you scrape them you inherit their breakage, and they are doing the same YouTube scrape we would do ourselves. |

**Takeaway:** hosted services mostly wrap the same timedtext/innertube calls from proxied IPs. The honest zero-auth solution is to do that call ourselves from the user's own IP.

---

## 2. Libraries and what actually works against YouTube bot-blocking

### 2.1 youtube-transcript-api (Python)

- Repo: `jdepoix/youtube-transcript-api`. MIT. About 8.6k stars. Last push 2026-11-09. PyPI 1.2.5 released 2026-11-05. Actively maintained.
- Uses YouTube's undocumented web-client endpoints. No headless browser, no API key. Takes a `languages` priority list (e.g. `["ar", "en"]`), supports auto-generated captions and translation.
- **Cloud IPs:** the README itself says YouTube blocks most cloud-provider IPs (AWS, GCP, Azure) and you will see `RequestBlocked` / `IpBlocked`. Even self-hosted boxes get blocked after too many requests. Official workaround: `WebshareProxyConfig` (rotating residential) or `GenericProxyConfig` (any HTTP/SOCKS proxy). The README warns that static proxies eventually get banned.
- **PO token issue:** [Issue #592](https://github.com/jdepoix/youtube-transcript-api/issues/592), opened 2026-04-25 on v1.2.4. When a caption track's `baseUrl` contains `&exp=xpe`, the timedtext endpoint returns an empty 200 and the library raises `PoTokenRequired`. The maintainer says it "shouldn't happen" on current versions, but the issue is still open with no documented fix. Community suggestions: generate PoTokens, or fall back to the innertube `/browse` transcript panel.
- Reports (unverified, blog sources) say that even through a proxy, YouTube rate-limits per video+IP, so 3 to 5 rapid hits on the same video gets that video blocked.
- **Verdict:** best first attempt on a home IP. Cheap, fast (one or two HTTP calls), returns timestamps. Always catch `RequestBlocked`/`IpBlocked`/`PoTokenRequired` and fall through.

### 2.2 yt-dlp subtitle extraction

- Repo: `yt-dlp/yt-dlp`. Unlicense. About 206k stars. Last push 2026-11-04. Releases nearly daily; the YouTube extractor is patched constantly.
- Command: `yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "ar.*,en.*" --sub-format json3/vtt URL`. Also `--dump-json` gives caption track metadata.
- **PO token rules** (from the [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide), fetched today):
  - Subtitle requests need a PO token **only for the `web` client**.
  - Video/audio (GVS) requests need one for `web`, `web_safari`, `mweb`, `tv_simply`, `web_music`, `web_creator`, `android`, `ios`.
  - **No PO token needed:** `tv`, `web_embedded`, `android_vr`. Catches: `tv` needs cookies to dodge DRM'd formats, `web_embedded` only works for embeddable videos, `android_vr` fails on "Made for Kids" videos.
  - Recommended cookie-less setup: `mweb` client plus a PO-token provider plugin.
- **Provider plugins:** `Brainicism/bgutil-ytdlp-pot-provider` (GPL-3.0, about 900 stars, last push 2026-10-07; runs a small Node/Docker service or script that mints tokens) and `yt-dlp-getpot-wpc` (browser based). These add a Node or Docker dependency, which is a real cost for a "just works" tool.
- Practical tip: try `--extractor-args "youtube:player_client=android_vr,web_embedded"` first for audio/subs without any token; escalate to `mweb` + bgutil only if that fails.
- **Cloud IPs:** a PO token does not cure an IP-level block. Sources disagree on how much a token helps from datacenter ranges. Assume it does not.
- Older reports say auto-translated caption tracks hit HTTP 429 while manual and original-language auto-captions were fine (2025, unverified for now). For Arabic videos, ask for the original `ar` track, never a translation.
- **Verdict:** best second step and the best audio downloader for the Whisper step. Heavier (subprocess, ~1 to 3 s startup) but the most maintained thing in the ecosystem.

### 2.3 Innertube-based libraries

- `LuanRT/YouTube.js` (`youtubei.js`): MIT, about 5.4k stars, last push 2026-11-04. Node/TS client for the same private API. Good if real-eyes ends up in the Node ecosystem; same datacenter-IP and PO-token limits apply. Has built-in session/PO-token plumbing to some degree, but I did not verify its current caption behaviour.
- Raw approach: POST to `youtubei/v1/player` with a non-web client context (ANDROID / ANDROID_VR / TV_EMBEDDED), read `captions.playerCaptionsTracklistRenderer.captionTracks[].baseUrl`, fetch it with `&fmt=json3`. Blog sources (unverified) say the ANDROID client avoids the caption PO-token check, while a Dart project reports sending `androidSdkVersion` is what triggers it. Contradictory, so **this changes monthly**. Treat as an implementation detail we maintain in a small adapter, not a promise.
- Browser fallback: a third-party project added a Playwright-based transcript fetcher (Aug 2026) referencing issue #592. Loading the watch page in a real headless browser and reading the transcript panel sidesteps PO tokens, because the page mints its own. Heavy but robust from a residential IP.

### 2.4 Invidious and Piped

- Invidious: `iv-org/invidious`, AGPL-3.0, about 10.3k stars, last push 2026-11-08. Piped: `TeamPiped/Piped`, AGPL-3.0, about 25.9k stars, last push 2026-11-06.
- Both expose captions via API (Invidious: `/api/v1/captions/{id}`). But the official Invidious instance list says it is short because of recent YouTube issues, and recommends self-hosting at home. A secondary source counted about 3 public Invidious vs 15 Piped instances in March 2026 (unverified). Public instances get rate-limited, CAPTCHA'd and vanish.
- **Verdict:** usable as an opportunistic fallback (try a few instances from a configurable list, short timeout). Never a dependency. Self-hosting only makes sense for a datacenter deployment and still needs rotating IPs.

### 2.5 cobalt

- `imputnet/cobalt`: AGPL-3.0, about 46k stars, last push 2026-04-06 (seven months quiet, so possibly stale for YouTube).
- It downloads media, **not transcripts**. Public `api.cobalt.tools` uses bot protection and its docs say do not use it in other projects without permission. Self-hosted instances commonly run with `API_AUTH_REQUIRED` and can return `api.auth.*.missing`. YouTube support is a known sore spot (GitHub issue #1356 is cited).
- **Verdict:** could be an audio-download fallback if the user points at their own instance. Not a default.

### 2.6 What actually works in 2026 without cookies (summary)

| Scenario | Works? | Best path |
|---|---|---|
| Home/residential IP, normal video, captions exist | Yes | youtube-transcript-api, then yt-dlp subs |
| Home IP, track has `exp=xpe` / empty body | Sometimes | yt-dlp with `tv`/`android_vr`/`web_embedded`; else bgutil PO token; else Playwright transcript panel |
| Home IP, no captions at all | Audio yes | yt-dlp audio (`android_vr`) then Whisper |
| Datacenter IP | Mostly blocked | Residential proxy (Webshare etc., paid, so opt-in), Invidious/Piped hop, or tell the user to run locally |
| Age-gated, private, members-only | No | Needs login. Report clearly, do not try to dodge. |
| Made-for-Kids with `android_vr` | No | Use `web_embedded` or `mweb` + token |

---

## 3. Other platforms

All of these work through **yt-dlp** (about 1,800 extractors) for metadata and media. Almost none expose a transcript without audio, so the realistic path is download audio, then Whisper.

| Platform | No-login status | Captions? | Plan |
|---|---|---|---|
| **Vimeo** | Public videos work. Private or embed-restricted ones need a referer or password. | Often has text tracks (VTT) listed in the player config; yt-dlp lists them as subtitles | `yt-dlp --write-subs`, else audio then Whisper |
| **Twitch** | Public VODs and clips work. Sub-only VODs need login. Live streams work but are unbounded. | No transcript. VODs sometimes carry no captions at all. | Download audio of VOD (or clip), then Whisper. Cap duration. |
| **TikTok** | Single public videos usually work through yt-dlp's native extractor. Slideshows (photo posts) are not supported. Breaks when TikTok rotates signing; "update yt-dlp" is the first fix. | Some videos expose auto-captions in the page JSON; most do not | yt-dlp, then Whisper |
| **Instagram Reels** | Poor. Sources in 2026 say Instagram serves almost everything behind a logged-in session; yt-dlp reworked the extractor in mid-2026 and now flags stale cookies. Treat no-cookie as best-effort and failing. | No | Try yt-dlp once; on "login required" return a clear, structured error. Do not promise this platform. |
| **X / Twitter** | Many public tweet videos still work through yt-dlp, but X increasingly requires login, especially for age-gated or sensitive content. | No (video only) | yt-dlp then Whisper; surface login errors honestly. |
| **Facebook** | Public page videos sometimes work; most reels/watch links push a login wall. I found no good 2026 data. | Sometimes auto-captions in page data | Same: try yt-dlp, then fail clearly. |
| **Podcasts / RSS** | Fully open. Audio enclosure is a plain MP3 URL. | **Podcasting 2.0 `<podcast:transcript url="..." type="text/vtt|srt|json|plain">`** in the feed item gives a ready transcript (Apple, Spotify for Creators, Pocket Casts all read it; coverage is only a minority of episodes) | Parse feed; use the transcript tag if present; else download enclosure then Whisper. PodcastIndex API is free but needs a key. Taddy free tier (key, 500 req/month) passes through publisher transcripts. Neither needed for the RSS-URL case. |
| **Direct media URLs / Apple Podcasts / Spotify pages** | Direct MP3/MP4 trivial. Apple Podcasts pages resolve to an RSS feed through the iTunes lookup API (no key). Spotify is DRM, so skip. | n/a | Resolve to RSS, then as above |

Legal note worth putting in the README: platform ToS (X, Instagram, TikTok) generally forbid scraping. real-eyes should be user-initiated, one URL at a time, no bulk harvesting.

---

## 4. Recommended fallback ladder (cheapest first)

Run steps in order. Return on the first success, and always report which step produced the text plus its quality (`source: manual | auto | whisper`, language, whether timestamps exist). Keep every network step on a short timeout (5 to 10 s).

**For YouTube**

0. **Normalize the URL** to a video ID (watch, youtu.be, shorts, embed, live, music.youtube.com). Cache by ID so repeated asks cost nothing.
1. **youtube-transcript-api**, `languages=["ar","en"]` (honor the user's language, then original track). ~0.5 s. Prefer manual over auto. Catch `RequestBlocked`, `IpBlocked`, `PoTokenRequired`, `TranscriptsDisabled`, `NoTranscriptFound`.
2. **yt-dlp subtitles only**, `--skip-download --write-subs --write-auto-subs`, clients `android_vr,web_embedded,tv` (no token needed per the PO Token Guide). ~2 to 4 s. Take the *original-language* auto track, never a machine translation (429-prone).
3. **innertube adapter or Playwright transcript panel** (headless browser, residential IP only). Slow (5 to 15 s) but handles `exp=xpe` tracks.
4. **Invidious/Piped hop** over a configurable list, 3 instances max, 5 s each. Flaky, free.
5. **Opt-in paid rungs**: residential proxy config (Webshare via youtube-transcript-api) or a hosted transcript API. Only if the user supplied credentials; never default.
6. **Audio + Whisper**: yt-dlp audio-only (`-f bestaudio`, clients `android_vr`/`mweb`+bgutil), then local `faster-whisper` (MIT, CTranslate2). Use `large-v3` or `large-v3-turbo` on GPU, `small`/`medium` on CPU (Arabic quality drops sharply on small models; Whisper handles MSA well, dialects less so, so set `language="ar"` explicitly rather than trusting auto-detect). Cost: roughly real-time/10 on a decent GPU, real-time or slower on CPU. If the audio download is blocked by the same IP issue, fail with a clear message.
7. **Fail loudly**: return a structured error naming the blocker (`ip_blocked`, `login_required`, `no_captions_and_audio_blocked`, `age_restricted`) and the single best next action for the user, instead of silently returning empty text.

**For every other platform**

1. Direct caption/transcript file if the page or feed exposes one (podcast:transcript, Vimeo text track, yt-dlp-listed subtitles).
2. yt-dlp audio download.
3. Whisper (same settings as above).
4. Structured `login_required` error for Instagram/Facebook/X when they wall us.

### Reliability notes

- Order matters because step 1 and 2 are 100x cheaper than Whisper and carry the *creator's* captions, which beat ASR for names and Arabic dialect.
- Pin and auto-update yt-dlp (`yt-dlp -U` or `pip install -U yt-dlp` at start, at most once a day). Most "it stopped working" reports are stale yt-dlp.
- Don't loop retries on the same video from the same IP. YouTube throttles per video and IP; retry once with a different client, then move down the ladder.
- Detect the empty-200 case (HTTP 200 with zero-length body) explicitly. It means PO token, not "no captions".
- Add a self-test (`real-eyes doctor`) that tries a known captioned video through each rung and prints which ones work from the current network. This is the most useful thing we can ship given how fast YouTube changes.
- Arabic specifics: request `ar` and `ar-*` variants, strip RTL marks only at display time, keep UTF-8 throughout, and flag auto-generated Arabic captions as lower quality.

## 5. Open questions to test hands-on

1. Does `android_vr` still return caption `baseUrl`s that fetch without a token on a datacenter IP today? (Test from a cheap VPS.)
2. Current Invidious/Piped instance health for `/captions` specifically.
3. Does the mid-2026 Instagram extractor give *any* public Reel without cookies?
4. Is bgutil's Node dependency acceptable, or do we ship a rung that works without it?

## Sources

- [youtube-transcript-api README/PyPI](https://pypi.org/project/youtube-transcript-api/) and [issue #592](https://github.com/jdepoix/youtube-transcript-api/issues/592)
- [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)
- [Invidious instances](https://docs.invidious.io/instances/)
- GitHub API (stars, license, last push): yt-dlp, youtube-transcript-api, imputnet/cobalt, Brainicism/bgutil-ytdlp-pot-provider, LuanRT/YouTube.js, TeamPiped/Piped, iv-org/invidious
- Podcast namespace: <https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md>
- Vendor/blog sources (treat as unverified): Apify actor listings, tubescript.cc, transcriptapi.com blog, assorted yt-dlp how-to posts
