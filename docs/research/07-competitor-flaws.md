# Competitor flaw mining (2026-11-10)

Method: `gh issue list --state all` on each repo, plus targeted reads of issue bodies. Stars come from `gh`. Issue counts are what I pulled (limit 200). I did not run the tools. The prior-art overview is in 05-prior-art-and-packaging.md and is not repeated here.

Issue links: `https://github.com/<repo>/issues/<n>`. CV = bradautomates/claude-video.

## 1. Comparison matrix

Y = has it, p = partial, n = no, ? = not checked. "JSON contract" means a documented, stable machine output. "Token control" means a budget or a published cost table.

| Competitor | Stars | Frames | Transcript | OCR | Non-YouTube sites | Whisper fallback | Local/keyless | JSON contract | Token control | Cache | Doctor/setup check | Viewer |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bradautomates/claude-video | 20.4k | Y (scene-aware, 2 fps cap) | Y (captions, then Whisper) | n | p (yt-dlp, TikTok broken) | Y (Groq/OpenAI/WhisperX) | p (key or WhisperX) | n (#25 asked for --json) | p (detail dial) | n | p (check-setup.sh, buggy) | n |
| jordanrendric/claude-video-vision | 1.5k | Y (adaptive) | Y | n | ? | Y (whisper.cpp) | p | p (MCP) | p | ? | wizard | n |
| guimatheus92/mcp-video-analyzer | 120 | Y | Y | Y | Y (Loom, TikTok, X) | Y | p | p (warnings[] contract added late) | n | Y (sidecar) | n | n |
| khou/watch-video | 7 | Y | Y | n | p | Y (whisper.cpp) | Y | n | Y (cost table) | ? | n | n |
| kar2phi/video-lens | 127 | n | Y | n | YouTube only | n | p | n | n | n | n | HTML report |
| steipete/summarize | 6.8k | p (slides) | Y | n | Y | Y | p | p (--json ignored on local media, #562) | n | Y | n | Chrome ext |
| jkawamoto/mcp-youtube-transcript | 496 | n | Y | n | YouTube only | n | Y | Y | p (pagination) | n | n | n |
| anaisbetts/mcp-youtube | 552 | n | Y (subs) | n | YouTube | n | Y | n | n | n | n | n |
| kevinwatt/yt-dlp-mcp | 308 | n | Y (subs) | n | Y | n | Y | p | n | n | n | n |
| jdepoix/youtube-transcript-api | 8.6k | n | Y | n | YouTube only | n | Y (but IP blocks) | Y (library) | n | n | n | n |
| JangHyuckYun/mcp-youtube-intelligence | 53 | n | Y | n | YouTube | ? | ? | ? | ? | ? | n | n |
| video-db/agent-toolkit (VideoDB) | 49 | hosted | hosted | hosted | upload | hosted | n (cloud, API key) | Y (SDK) | n | hosted | n | hosted player |
| Gemini-video MCP wrappers (DerYUYU, sonnguyen-2002, others) | 0-1 each | black box | black box | black box | YouTube/upload | n/a | n (Google key) | n | n | n | n | n |

VideoDB's toolkit repo has 2 open issues, both about docs. The Gemini wrappers have no issues and no users. Their only lesson is that Gemini is a cloud black box that needs a key, so neither is worth mining further.

## 2. Real user complaints by theme

### A. Fragile external-tool assumptions (ffmpeg, yt-dlp, Windows). The biggest bucket.
- CV: the `-vsync` flag was removed in ffmpeg 7/8/9, so frame extraction fails with zero frames. There are about 20 duplicate issues, all open: #99, #101, #117, #122, #126, #134, #141, #143, #149, #161, #163, #174, #180, #195, #229, #238, #241, #244, #246. Nobody merged the one-line fix. This is the strongest single piece of evidence in the study.
- CV on Windows: cp1252 crashes on emoji or non-Latin titles (#51, #109, #150, #134), subprocess output decode crashes (#108, #238), `read_text()` without encoding (#4, closed), a permissions warning that is always wrong (#47, #107, #170, #189), App Control blocking ffprobe (#128).
- CV on YouTube: a 403 on media unless deno and curl_cffi are present (#67, #156), macOS brew yt-dlp has no impersonation targets (#93), "YouTube not reachable" or egress blocks (#83, #135, #44).
- jkawamoto/mcp-youtube-transcript: broken for anyone without `bun` installed (#26). anaisbetts/mcp-youtube: "Sign in to confirm you're not a bot" (#6), Windows access denied on `downloads` (#14), a console window pops up (#18).
- mcp-video-analyzer: "Cannot find module ajv" (#8), "Failed to connect" via npx (#9), Loom frames silently fail because yt-dlp writes `.mp4.webm` (#24).
- claude-video-vision: Windows lavfi path escape returns empty results (#43), duplicate MCP instances after reconnect (#48).
- youtube-transcript-api: cloud-IP blocks dominate, with dozens of IpBlocked/RequestBlocked issues (#546, #550, #585, #593, #606, #613). Also PoTokenRequired with no workaround (#592).

### B. Wrong-language and wrong-caption handling
- CV hardcodes `--sub-langs "en.*"`, so non-English videos get machine-translated English captions (#144, #153, #240). Auto-selection picks the first `*-orig` track alphabetically, so dubbed videos get Bengali or Arabic (#247, #257). `parse_vtt` rejects valid `MM:SS.mmm` timestamps (#245).
- anaisbetts/mcp-youtube: only English subtitles available (#10). jkawamoto: language preference had to be added (#69). coyaSONG: users wanted caption source and translation provenance (#46).

### C. Silent failures and fake output
- CV: Whisper invents dialogue on silent videos and it is shown as a normal transcript (#222). `--fps` silently truncates coverage to the head of the video (#178). TikTok always says "no captions" because the metadata pass runs with `--no-write-subs` (#268). `watch.py` deletes a source file that sits inside `--out-dir` (#80). Gemini 503 with no bounded retry (#250).
- claude-video-vision: a 600s ffmpeg timeout silently returns an empty analysis (#58). The scenes array truncates at 1:09 on long films (#47). Whisper.cpp hallucinates on score-only segments and timestamps collapse to 00:00:00 (#40). Audio extraction fails when the video has no audio stream (#22).
- steipete/summarize: whisper.cpp drops words at every 30 s window (#543) and loops on long audio with about 75% content loss (#363). `--json` is ignored for local media (#562).
- mcp-video-analyzer: `warnings[]` had no contract and 14 sites leaked raw `e.message` (#46). The cache key was missing `maxWidth` (#28) and `skipFrames` (#29).

### D. Frame selection quality
- CV: the near-duplicate filter drops slides that differ only in text (#258). A hard 2 fps cap gives 1 frame on a 0.72 s clip, with no all-frames override (#37). Scene threshold default is too noisy in claude-video-vision (#45). Users wanted PNG for screen recordings (vision #33). `segments` returned one continuous 1 fps range instead of per-segment snippets (vision #46). LLMs misread `end_time` as a duration (vision #35).

### E. Where it can run
- CV does not work on Claude Web, Claude AI chat or Cowork (#20, #23). The slash command silently failed to register because of an `allowed-tools` YAML inline-list parse issue (#6). Sandboxes with network allowlists gave unclear errors (#43, #44).

### F. Security
- CV: option injection through the URL, fixed by inserting `--` (#2). Transcript prompt-injection hardening (#61). ZeroPointRepo/youtube-skills: its auth doc tells agents to bypass secret redaction and self-persist API keys (#10). youtube-transcript-api: a CLI video ID starting with `-` was parsed as a flag (#599). yt-dlp-mcp: `--ignore-config` broke proxy and cookie config (#12, #30), and numeric params failed because MCP serialized them as strings (#20, #29).

### G. Maintenance smells
- CV has about 75 issues in six months, nearly all open, and several are junk ("А", "Мои", "Video", "AskVLM"). Its test suite cannot pass on a developer machine because user config leaks in (#96).
- Several MCP repos are full of spam (directory pitches, conformance bots, ads). That shows open-issue counts mean little there.

## 3. Design mistakes

1. **Bloated instructions.** CV's SKILL.md is 17 KB and its README 27 KB. SKILL.md is paid for in context on every activation. Keep tapetum's under about 60 lines and push detail into `--help` and `tapetum doctor`.
2. **Pinned to a removable ffmpeg flag.** Using `-vsync` instead of feature-detecting `-fps_mode` broke every modern install.
3. **English hardcoded, and caption choice by alphabetical order.** Pick by the video's declared original language, prefer manual over auto, never use the auto-translated track, and report which track was used.
4. **No JSON contract.** CV closed "add --json" (#25) but prose is still the default, and every MCP invents its own shape.
5. **Weak or no cache.** Re-running re-downloads. mcp-video-analyzer's sidecar cache had key bugs (#28, #29), so the key must include every parameter that changes output.
6. **Silent degradation.** Empty analysis on timeout (vision #58), zero frames (CV #99), hallucinated transcript (CV #222). Every degraded path needs a coded warning.
7. **Keys as the default path.** CV's fallback transcription wants Groq or OpenAI keys. Groq 403s behind VPNs and the message reads like a bad key (CV #137). Local whisper should be the default.
8. **Frame dedup by pixels only.** Slides that change text but not layout get dropped (CV #258).
9. **Fixed fps caps with no override** (CV #37, #178).
10. **Claude-plugin-first.** Does not run in chat surfaces and broke on a YAML parse quirk (CV #6, #20, #23).
11. **Captions-only is a moving target.** Cloud-IP blocks and PoToken (transcript-api #592, #593) mean a media-download path with local Whisper is the stable fallback.

## 4. Features users keep asking for

- Non-English and native-language captions (CV #144, #153, #240; mcp-youtube #10).
- `--json` output (CV #25) and caption provenance (coyaSONG #46).
- Keyless local transcription (CV #137; SenseVoice/FunASR in CV #29).
- Longer videos: chunking and a `--no-frames` flag (CV #25 thread, PR #22).
- All-frames mode for short clips (CV #37), PNG for screen recordings (vision #33), per-segment snippets (vision #46).
- Cookies or auth for private videos (CV #48). This conflicts with tapetum's zero-cookie promise.
- Audio tagging for music and non-speech (vision #41).
- Pagination or trimming for long transcripts (jkawamoto #28, #50, #97; yt-dlp-mcp #17; anaisbetts #1).
- Metadata, description and timestamps in output (jkawamoto #35, #46).
- Transcript snippet de-duplication (transcript-api #608); speaker names (#564).
- Broader site support: Loom, Bilibili, Xiaoyuzhou, reels (summarize #353, #364, #533; analyzer #18).
- Fixing machine mishearing (CV #66, a wish).

## 5. Good ideas worth copying (with attribution)

- Detail dial and the "Choose your app" install table: bradautomates/claude-video.
- Honest image-token cost table: khou/watch-video.
- Setup wizard and the "perception layer, not interpretation layer" framing: jordanrendric/claude-video-vision.
- Skill falls back to a bundled CLI when MCP is absent; `warnings[]` contract; sidecar cache; a known-speech test fixture gated by an env var that never silently skips (#30): guimatheus92/mcp-video-analyzer.
- Insert `--` before the URL in yt-dlp argv, and treat transcripts as untrusted input: CV #2, #61.
- Cursor pagination for long transcripts and timestamp deep links in answers: jkawamoto/mcp-youtube-transcript, coyaSONG/youtube-mcp-server.
- HTML report as an output: kar2phi/video-lens. Avoid its bugs: a `</script>` in a title breaks the page (#2), and Windows paths break the served URL (#4).
- Whisper hallucination guard using the no-speech probability the pipeline already computes (proposal in CV #222).
- whisper.cpp fixes: `-mc 0` against repetition loops (summarize #363), no `--no-timestamps` at window boundaries (#543).

## 6. MUST FIX / MUST HAVE for tapetum (ranked)

Rank is by how many users are hit, times how cheap the fix is.

1. **Never depend on a removable ffmpeg flag, and ship a tested ffmpeg matrix.** About 20 duplicate issues in CV (#99, #117, #122, #141, #161, #163, #195, #246 and others). Use `-fps_mode` with a `-vsync` fallback chosen by probing, and run CI on ffmpeg 6/7/8 on Linux, macOS and Windows.
2. **Windows and unicode correctness from day one.** Force UTF-8 for all subprocess I/O and stdout, give every file read an explicit encoding, and test emoji and CJK titles and non-ASCII paths. CV #51, #108, #109, #134, #150, #238.
3. **Language-aware caption selection.** Use the video's original language, prefer manual tracks, never take the auto-translated one, and put `track`, `language` and `kind` (manual/auto/whisper) in the output. CV #144, #153, #240, #247, #257; coyaSONG #46.
4. **Versioned JSON contract plus a coded warnings array.** `--format json|md`, `schema_version`, stable exit codes, and a warning for every degradation (no frames, timeout, fallback used). CV #25; analyzer #46; vision #58; summarize #562.
5. **Keyless local Whisper as the default fallback, with a hallucination guard.** Use faster-whisper or whisper.cpp, drop segments by no-speech probability and repetition, and report "no speech" instead of inventing text. CV #137, #222; vision #40; summarize #363, #543.
6. **Slide-aware frame selection.** Dedup on OCR text delta as well as pixels. CV #258; vision #45. Add `--all-frames` or `--fps N` that never silently truncates (CV #37, #178) and a PNG option for screen content (vision #33).
7. **Two-pass, time-range addressing.** `--at 12:30-13:10 --dense` gives per-segment frames, with absolute timestamps stated in the help. Vision #46 and #35 show agents misuse vague range parameters.
8. **Token budget flag.** `--budget 20k` picks frame count and size, and the output states estimated tokens. Only khou publishes costs today.
9. **Tiny SKILL.md (under about 60 lines), no install maze, and `tapetum doctor`.** Doctor reports ffmpeg, yt-dlp, JS runtime and impersonation status, with fixes. CV #6, #67, #93, #156.
10. **Cache keyed on every output-affecting parameter.** URL id, engine, fps, width, skipFrames and so on. Analyzer #28 and #29 are the cautionary tale.
11. **Long-video handling.** Chunked transcription, transcript pagination or trim-to-range, and a `--no-frames` mode. CV #25 and PR #22; jkawamoto #28, #50, #97; yt-dlp-mcp #17.
12. **Security defaults.** `--` before every URL, reject IDs that start with `-`, wrap and label transcript and OCR text as untrusted, and never advise bypassing secret redaction. CV #2, #61; youtube-skills #10; transcript-api #599.
13. **Works where agents run.** One CLI usable from any shell, a thin MCP with string-tolerant numeric params (yt-dlp-mcp #20), and a clear message when a sandbox blocks the network (CV #44).
14. **A media-download path that survives YouTube blocks,** with an honest error for cloud-IP and PoToken failures. transcript-api #592, #593, #606; CV #83, #135, #156.
15. **Report caption state correctly on non-YouTube sites.** Fetch subs in the same pass as metadata so TikTok and Reddit do not claim "no captions" (CV #267, #268). Add Loom, Bilibili and reels (summarize #353, #533; analyzer #18).
16. **Never destroy user files.** Do not write into or clean a directory that holds the source (CV #80); keep a separate cache dir.
17. **Later:** audio tagging for music (vision #41), a Gemini engine behind an explicit flag with bounded retries (CV #250, #261), and the HTML viewer (video-lens, with its `</script>` and Windows path lessons).

## 7. Positioning takeaway

The leader's open-issue list is a free test plan. Almost all of it is boring reliability: ffmpeg flags, Windows encodings, caption language, silent failures. Tapetum wins by shipping a tested, honest tool with a JSON contract and a doctor command, and by using the bug list above as its regression suite from the first release.
