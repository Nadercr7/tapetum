# What we measured ourselves

Machine: Windows laptop, CPU only (an NVIDIA GPU is present but its CUDA libraries are not, so tapetum fell back to CPU). Video: an Egyptian Arabic explainer, 7:14, no platform captions. Date: 2026-11-10.

| Model | Wall time | Quality on Egyptian Arabic |
|---|---|---|
| Whisper `small` (int8) | about 2m40 including audio download | Garbled. Misheard words throughout ("سمير وشهير وبهير" for the intro characters). Usable only for the gist. |
| Whisper `large-v3-turbo` (int8) | first run about 15 min, almost all of it the one-time 1.6 GB model download. Re-timed with the model cached: 158 s for 434 s of audio (0.36x real time, 20 threads) | Far better. Technical terms, the physics formula and "سنة 1905" came out right. Some dialect words still wrong. |

Takeaways:
- For Arabic, `--quality accurate` is worth the wait. tapetum warns when the small model meets Arabic, Persian, Urdu or Hindi.
- First run pays a model download. Later runs on the same machine skip it.
- faster-whisper's `BatchedInferencePipeline` hard-crashed the process on this machine (no Python error, exit 127), so tapetum stays sequential.
- Not measured: GPU speed, other languages, the Cohere and Qwen models from notes 02 and 09.

Bugs found by running it, now fixed:
- faster-whisper 1.2.1 crashes on PyAV 19 (`metadata_errors`). tapetum decodes audio itself.
- A GPU without CUDA libraries crashed Whisper. tapetum retries on CPU.
- yt-dlp needs `yt-dlp-ejs` (the `yt-dlp[default]` extra) to solve YouTube's n-challenge; without it audio formats vanish.
- Picking `bestaudio` could grab YouTube's HLS or "-drc" tracks, which stalled for minutes. The audio selector now prefers small plain-HTTP tracks.
- Videos with no audio track returned an error instead of a frames-only result.

## Second pass (code review, 2026-11-10)

An independent review found 20 defects. All are fixed and most have a regression test in `tests/test_core.py`:
- `--fresh` used to delete the whole `--out` folder. It now removes only files tapetum wrote.
- A video title could inject script into the viewer page. JSON in the page is now escaped.
- The cache could return another video's result, cache failures forever, and mix up local files with the same name. Fixed by keying on the source, never caching failed runs, and hashing local paths.
- YouTube's rolling auto-captions came out with most words doubled. The parser now dedupes line by line.
- Caption choice could return a machine translation as if it were the original. Track choice now prefers human captions, then the original language, and flags translations.
- Live streams and playlists hung or downloaded everything. Both now fail fast with a clear code.
- Frame timestamps were half a sampling step late (checked with a synthetic video: the default `fps` filter labels frame i at (i+0.5)/fps). Now `fps=...:round=up`.
- Zoom on local files ignored `--at`; Windows non-UTF-8 ffmpeg output could crash; `--budget` under 6 was ignored; the MCP tool only showed the first sheets of long videos. All fixed.
