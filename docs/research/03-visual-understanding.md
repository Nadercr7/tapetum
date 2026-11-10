# 03 - Visual understanding for real-eyes

Research date: Nov 2026. Method: web searches only, no hands-on benchmarking. Numbers marked (approx) came from third-party blogs, not vendor docs. Check vendor docs before hard-coding any token math.

## TL;DR recommendations

1. Default pipeline: ffmpeg decode at low fps, then a cheap frame-difference/perceptual-hash pass, then a hard cap on frames. Skip heavy scene-detection deps unless the user opts in.
2. Always hand the agent a timeline document (markdown) where transcript segments and frame filenames share timestamps. Frames are files on disk the agent opens on demand, not a giant blob pushed into context.
3. Burn the timestamp into each frame (or into a contact-sheet cell). It costs nothing and lets the model cite moments.
4. OCR is the best value add for screen recordings, slides, code. Use RapidOCR (ONNX, CPU, light) as the default. Treat Arabic as "needs testing", and fall back to letting the host model read the image.
5. Do not bundle a local VLM by default. Make it an optional plugin. The host agent (Claude, GPT, Gemini) is already a far better captioner than anything that runs on a laptop CPU.

## 1. Keyframe selection

| Method | How it works | Pros | Cons |
|---|---|---|---|
| Fixed interval (ffmpeg `fps=1/N`) | Uniform sampling | Trivial, deterministic, no deps | Wastes frames on static talking heads; misses fast slide flips |
| ffmpeg `select='gt(scene,0.3)'` | Global threshold on frame-to-frame diff | Zero extra deps; fast. 0.3-0.4 catches most hard cuts (approx) | One fixed threshold, no adaptation; silent on slow dissolves and on lectures with no cuts |
| PySceneDetect (github.com/Breakthrough/PySceneDetect) | ContentDetector, AdaptiveDetector (rolling-average threshold, better with camera motion), ThresholdDetector (fades) | Mature, tunable, gives scene boundaries as well as frames | Needs OpenCV (heavy install); built for cuts, so lectures/screencasts can still be missed |
| Perceptual-hash dedup (`imagehash`, or a tiny dHash in numpy) | Sample densely (1-2 fps), drop frames whose hash is within Hamming distance N of the last kept frame | Great for slides and screencasts; removes lighting flicker and wobble false positives from scene detection | Needs the dense sample first; threshold tuning per content type |
| Motion / entropy sampling | Keep frames with high motion or high information | Catches demos and action | Noisy; extra code for modest gain over hash dedup |
| Transcript-aligned | Pick one frame at each speech segment start or midpoint, or when the speaker says "as you can see", "this slide" | Frames land exactly where the words refer to them | Needs a transcript; does nothing for silent video |
| Query-aware selection (research) | Rank frames by relevance to the question and diversity | Best accuracy per frame budget | Needs embeddings (CLIP/SigLIP) plus a question; see section 6 |

Practical recipe that existing tools converge on: scene-change detection, then pixel or hash dedup, with a density floor (a minimum number of frames per minute) so static videos still get uniform samples. crv and mcp-video-analyzer both work this way (see section 6).

Suggested real-eyes default:
- Decode at 1 fps, downscaled to ~320 px wide, in one ffmpeg pass piped to numpy.
- Compute a 64-bit dHash plus mean absolute pixel diff vs the last kept frame. Keep when the difference is over a threshold.
- Density floor: at least one frame every 30-60 s. Ceiling: a user-set max (say 40-60 frames) with the lowest-change frames dropped first.
- Add transcript-aligned frames only when a transcript exists and the visual stream gives fewer than N frames.
- Re-extract the chosen timestamps at full quality (`ffmpeg -ss T -i in -frames:v 1`) rather than saving the downscaled analysis frames.
- Expose modes: `--mode slides|talk|action|uniform`, each just a different threshold preset.

## 2. Presenting frames to an LLM cheaply

Token math (approx, verify per vendor):
- Claude: about width x height / 750 tokens per image, minimum ~100. Long edge was capped at 1568 px on older models; one source says 2576 px on newer Opus. So a 1568x882 frame is ~1,800 tokens and a 768x432 frame is ~440. One blog estimated a 720p JPEG at ~1,200 tokens.
- Gemini: widely reported as 258 tokens for a small image, with tiling (768x768 tiles at 258 each) for large ones. Gemini also takes native video (about 1 fps sampling), which real-eyes cannot rely on from other hosts.
- OpenAI: legacy tile scheme (85 + 170 per 512 tile; 1024x1024 = 765). Newer models are reported to use 32x32 patches. A cross-provider blog measured a 1024x1024 image at roughly 765 (GPT-5 family), 1,032 (Gemini), 1,398 (Claude).

What this means for design:
- Cost scales with pixels, so resolution is the main knob. Text-heavy frames (slides, code) need ~1024-1280 px wide to stay legible. Talking heads and b-roll are fine at 512-768 px.
- Contact sheets (grid of 4-12 thumbnails in one image) cut per-image overhead and give the model temporal context in a single view. Downsides: each cell is small, so text becomes unreadable above about a 3x3 grid on a 1568 px canvas, and a tool that scales the sheet down will make it worse. Rule of thumb: contact sheet 3x3 at ~1500 px wide for a "what happens in this segment" overview, individual full-res frames for anything with text.
- Two-tier output works well: (a) one overview contact sheet per ~2-5 minutes, (b) individual frames listed in the timeline for the agent to open when it needs detail. The agent pays for detail only on demand.
- Burn in timestamps with ffmpeg `drawtext` (needs a font file, which is a known pain on Windows; use Pillow instead to avoid the fontconfig problem) in a corner with a dark box behind it. For contact sheets, label each cell with `mm:ss`. Also put the timestamp in the filename (`f_0123.4s.jpg`).
- JPEG quality ~75-85 is enough. File size does not drive token cost, but it matters for MCP/base64 transport limits.
- Hosts differ on how they take images: some agents read files via a file tool, MCP can return image content blocks. Support both: write files to a cache dir AND offer a base64 return path.

## 3. OCR

| Engine | Notes |
|---|---|
| Tesseract | Apache 2.0, CPU, needs a system binary. Fine for clean printed text; weak on screenshots with colored backgrounds and small code fonts. Has `ara` traineddata. |
| RapidOCR (github.com/RapidAI/RapidOCR) | PaddleOCR models exported to ONNX, runs on onnxruntime, small wheel, no paddle framework. Best default for a pip-installable tool. Arabic needs a separately selected recognition model; check availability and quality before promising it. I found no Arabic benchmarks for it. |
| PaddleOCR | Strongest open general OCR, fast, multilingual including Arabic in newer PP-OCR versions. Heavy install (paddlepaddle). Good optional backend. |
| EasyOCR | PyTorch, easy API, Arabic supported, slower on CPU and a big torch dependency. Used by VideoAnalyzer (below). |
| Surya | Good layout and 90+ languages, GPU-friendly, GPL-3.0 reported by one source (check; licensing could clash with a permissive project). |

Arabic caveat: the KITAB-Bench paper (arxiv.org/abs/2502.14949) found VLMs beat EasyOCR, PaddleOCR and Surya on Arabic by a wide margin (about 60% lower character error rate), and that the classic engines lack Arabic-specific segmentation and diacritics handling. Implication: for Arabic on-screen text, the most accurate "OCR engine" available to real-eyes is the host model looking at the frame. So the OCR step should be optional and flagged by language, and the timeline should say "OCR text may be unreliable for Arabic, view frame X".

OCR speed tips:
- Only OCR the deduplicated keyframes, never every frame.
- Skip OCR on frames with low edge density (cheap Laplacian-variance check) to avoid junk text from faces and landscapes.
- Dedupe OCR output across consecutive frames (slides repeat). Store only the diff or a similarity-gated version.
- Crop the bottom third first for burned-in subtitles; that text is a transcript source in its own right.

## 4. Local VLM captioning

Candidates:
- SmolVLM2 256M / 500M / 2.2B (Hugging Face): treats video as a sequence of images, runs on CPU, tiny. Captions are generic.
- Moondream 2 (and Moondream 3 preview, 9B MoE with ~2B active): good at short captions and object queries, per-frame only.
- Qwen2.5-VL / Qwen3-VL 2B / 4B / 8B (Apache 2.0): strong OCR, document and video understanding for their size. 8B is the realistic quality bar but needs a decent GPU or patience; I saw an Intel-CPU report that it ran acceptably for single images.

Verdict: not worth bundling. Reasons: (1) the host agent already sees the image and does it better; (2) pulling several GB of weights breaks the "install and go, no keys" promise; (3) captions from a 500M model add tokens of low-value text that the agent then has to reason about, sometimes wrongly; (4) CPU captioning of 50 frames takes minutes. A good case for it: headless pipelines where the consumer is a text-only LLM (cheap model, no vision) or when the user wants a searchable index. Ship it as `real-eyes[caption]` extra with Qwen3-VL-2B or SmolVLM2 via an Ollama/llama.cpp endpoint rather than in-process torch. I found no 2026 head-to-head caption benchmark of these models on video frames, so I would not claim a winner without a local test.

## 5. Other detection ideas

- Slide-change detection: hash dedup with a stricter threshold on a cropped content region, then OCR title line as the slide label. Gives a "slide index" with start and end timestamps.
- Face detection (OpenCV YuNet or MediaPipe): count of faces per frame is a cheap tag for "talking head vs screen share vs b-roll". Do not do identification; privacy and liability.
- Layout classification via simple heuristics: ratio of text pixels, edge density, color histogram variance, presence of a face: classify as `slide`, `code`, `talking_head`, `demo`, `black/title`. Lets the sampler choose per-type resolution.
- Black frame / freeze detection: ffmpeg `blackdetect`, `freezedetect` are free and good for trimming intros.
- Object detection (YOLO): heavy for what it buys in a tool aimed at agents; VideoAnalyzer uses YOLOv8, but I would skip this by default.
- CLIP/SigLIP embeddings per keyframe: unlocks "find the moment where X is shown" search without any generation, and enables the query-aware selection described below. ~100-400 MB model, acceptable as an optional extra.
- Cursor / click detection for screencasts: diff regions localised to small areas indicates typing or UI actions. Interesting for tutorials, speculative.

## 6. Existing projects and ideas to steal

Tools (checked only via search snippets, not repo activity; verify stars/commits before citing):
- mcp-video-analyzer (github.com/guimatheus92/mcp-video-analyzer): MCP server with transcript (native captions, Whisper fallback), keyframes via scene detection with a 1 fps dense mode and uniform fallback for static clips, OCR, metadata, and an annotated merged timeline. Closest to the real-eyes goal; worth reading its timeline format.
- VideoAnalyzer (dev.to write-up by chrisk60331): ffprobe + faster-whisper + YOLOv8 + EasyOCR + audio classification, scene segmentation. Heavier, shows the "everything" end of the spectrum.
- claude-real-video / crv (MIT; HUANGCHIHHUNGLeo): ffmpeg scene detection, density floor, pixel dedup, no OCR. Shows the light end.
- Apify "video-to-scenes" actor: hosted, closed. Notes that dissolves are not split.
- Also relevant: the dev.to posts "Claude Real Video: feeding an LLM the frames that actually matter" and "How I taught my AI agent to watch YouTube videos". Worth skimming for pitfalls.

Research on long-video QA (all arXiv, mostly self-reported gains; treat numbers loosely):
- VideoAgent (arxiv.org/abs/2403.10517): LLM acts as an agent, starts with few frames, iteratively asks for more until it can answer. 60.2% on an EgoSchema subset with 8.4 frames on average. Idea to steal: do not preload everything; let the agent request more frames around a timestamp.
- LVNet (arxiv.org/abs/2406.09396): hierarchical keyframe selector, few frames per question.
- AdaRD-Key (2510.02778): relevance plus diversity selection, training-free.
- QCA (2607.00983): query- and content-aware selection; with Qwen3-VL-8B at 64 frames reports 66.9% on LongVideoBench.
- GCR "Ground, Cover, Refine" (2608.01660): evidence-centric frame selection for fixed budgets (8/32/64 frames).
- ReMem (2607.24794): granularity-adaptive selection with memory.
- I did not find a paper specifically named Video-RAG in my searches, so I cannot confirm what that approach does here.

Ideas worth stealing, ranked by value per effort:
1. A `frames` tool/command that accepts a time range or a timestamp list, so the agent can zoom in. Agentic retrieval beats a big up-front dump (VideoAgent).
2. Relevance plus diversity: if the user passes a question or query, rank candidate frames by CLIP similarity to the query and greedily keep diverse ones. Only needed once an embedding extra exists.
3. Coarse-to-fine: first pass gives a contact-sheet storyboard plus transcript; the agent asks for detail on specific moments.
4. Fixed frame budgets (8/32/64) are the benchmark norm; expose `--budget` rather than an interval.
5. Density floor so static videos do not return one frame.

## 7. Audio-visual alignment: one timeline document

Align everything on a single clock in seconds. Sources: transcript segments (start, end, text), keyframes (t, path, OCR text, tag), scene or slide boundaries.

Merge algorithm: build a list of events, sort by start time. Group into chapters either by platform chapters (if the URL source provides them), by slide/scene boundaries, or by fixed windows of 30-60 s. Inside each chapter, list the frame references first, then the speech.

Suggested markdown shape:

```
# Title - 12:34 - source URL
## Overview
contact_sheet_00.jpg (frames 0:00-5:00)

## [00:00-01:10] Slide 1: "Intro to X"
Frames: f_0000.jpg (0:00), f_0045.jpg (0:45)
On-screen text: "Intro to X / Speaker name"
Speech:
- [00:03] Hi everyone, ...
- [00:21] ...
```

Details that matter:
- Use a consistent timestamp format (`mm:ss`, or `h:mm:ss` over an hour) so the model can cite and the user can jump with `?t=` links.
- Put the frame reference at the moment it appears, then the speech that follows, since speech usually explains what is on screen.
- Mark OCR text distinctly and mark low-confidence or non-Latin results.
- Offer a JSON sidecar with the same data for programmatic use.
- Keep the markdown compact: it is the part that always enters context. A 10-minute talk should fit in a few thousand tokens plus the images the agent chooses to open.
- Where captions overlap, trust ASR timestamps from Whisper-class tools over auto-captions for alignment, but expect drift of a second or two; align frames to segment start, not word level.

## Open questions to test locally before committing

- RapidOCR vs PaddleOCR on real Arabic screenshots and Arabic-subtitled video (speed and error rate).
- Claude token counts per image size on the current model, measured with the token-counting endpoint.
- Whether `imagehash` is worth the dependency vs a 20-line numpy dHash (likely not).
- Best default threshold per mode on 5-10 sample videos (lecture, screencast, vlog, news).

## Sources

- mcp-video-analyzer: https://github.com/guimatheus92/mcp-video-analyzer
- VideoAnalyzer write-up: https://dev.to/chris_king_bcff3b9663e84a/i-open-sourced-videoanalyzer-turn-raw-video-into-structured-ai-context-4l9i
- crv write-up: https://dev.to/renolu/claude-real-video-feeding-an-llm-the-frames-that-actually-matter-ge
- How to Let Claude Watch a Video: https://mcp.directory/blog/claude-real-video-understanding-2026
- KITAB-Bench: https://arxiv.org/abs/2502.14949
- Vision token counts: https://blog.roboflow.com/image-token-cost-vlm/
- Local VLMs: https://blog.roboflow.com/local-vision-language-models/
- SmolVLM paper: https://arxiv.org/html/2504.05299v1
- PySceneDetect: https://github.com/Breakthrough/PySceneDetect and https://www.scenedetect.com
- VideoAgent: https://arxiv.org/pdf/2403.10517
- LVNet: https://arxiv.org/html/2406.09396v6
- AdaRD-Key: https://arxiv.org/pdf/2510.02778
- QCA: https://arxiv.org/pdf/2607.00983
- GCR: https://arxiv.org/pdf/2608.01660
- ReMem: https://www.alphaxiv.org/abs/2607.24794.md
