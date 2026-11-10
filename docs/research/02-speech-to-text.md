# Speech-to-text for real-eyes: local and free options (research, Nov 2026)

Scope: how real-eyes can turn the audio track of a video into text on the user's machine, with no API keys. The focus is on a CPU-only Windows laptop, Arabic quality (especially Egyptian), word timestamps, speaker labels, silence skipping, and language detection.

## Bottom line

For a free, local, pip-installable pipeline, use **faster-whisper** with **whisper large-v3-turbo** (int8 on CPU), plus **Silero VAD** to cut silence. For Arabic, the best open-weight option found in this research is **Cohere Transcribe Arabic** (Apache 2.0, 2B parameters, released July 2026). It is heavier, though, and I could not verify its CPU speed. Plan to test both on the same Egyptian clips before choosing.

Fine-tuned Egyptian Whisper checkpoints exist on Hugging Face, but the published numbers are self-reported, use different test sets, and mostly predate 2026. Treat them as leads, not as settled results.

## Recommendation table

Speed figures are rough and depend heavily on the machine. Nothing below was measured on the target laptop; the "Speed" column reflects relative expectations, not benchmarks. Run a timing test before committing.

| Model / tool | Speed (CPU laptop) | Arabic quality | Install difficulty | License |
|---|---|---|---|---|
| **faster-whisper + large-v3-turbo (int8)** | Medium. Usable on CPU, slower than real time for long videos unless VAD trims the audio. | Stock Whisper is weak on Egyptian. One source reports about 48% WER on Egyptian for stock turbo, and about 36% for large-v3 on the same set. Fine-tunes reach the 30s. | Easy. `pip install faster-whisper`. Model downloads automatically. | MIT (code). Whisper weights are MIT. |
| **whisper.cpp (large-v3-turbo, quantized)** | Similar to faster-whisper on CPU. Much faster on Apple Silicon (Metal) or with GPU backends. | Same model, so same Arabic quality as above. | Medium. Needs a C++ build or prebuilt binary. Python bindings exist but are less polished. | MIT |
| **Cohere Transcribe Arabic (2B)** | Slow on CPU. Likely needs a GPU for comfortable use. Not measured. | Best open-weight Arabic result found. Hugging Face reports average WER 25.87 on the Arabic leaderboard. Tested sets cover Egyptian, Gulf, Levantine and Maghrebi, but sources disagree on the exact composition. | Medium. Transformers-based. Check the model card for the exact install path. | Apache 2.0 (weights). Training data and code may not be public. |
| **Whisper fine-tunes for Egyptian (e.g., MAdel121 medium, WafaaFraih small, dev-ahmedhany turbo LoRA)** | Small and medium variants are CPU-friendly. | Self-reported WER ranges from about 18% (medium, validation split) to about 41-48% (small, various sets). Not comparable with each other. | Easy to medium, same stack as Whisper. | Check each card. Whisper base license is MIT. |
| **distil-whisper** | Fast (about 6x faster than large, per its authors). | **Not usable for Arabic.** Distil models are English-only. | Easy. | MIT |
| **NVIDIA Parakeet TDT 0.6B v3 / Canary 1B v2** | Fast, mainly on GPU via NeMo. | **No Arabic.** Covers 25 European languages. Not an option for this use. | Hard (NeMo stack, heavy dependencies). | CC-BY-4.0 |
| **Moonshine (v2, Feb 2026)** | Very fast, designed for edge devices. | An Arabic-specialized Moonshine model exists from Sept 2025 (Flavors of Moonshine). Accuracy on Egyptian is unverified. | Easy. Pip package available. | Code MIT. Check model weights before commercial use. |
| **Qwen3-ASR (0.6B / 1.7B, 2026)** | 0.6B is light enough for CPU testing. | Community fine-tunes report 22-35% average WER on mixed Arabic sets. Self-reported, unverified. Base model's Arabic score not found. | Medium. | Open weights, check card. |

Recommended order to test on Egyptian clips:

1. faster-whisper + large-v3-turbo as the baseline (fastest to set up).
2. A community Egyptian fine-tune in the same faster-whisper format, if one converts cleanly to CTranslate2.
3. Cohere Transcribe Arabic on a GPU or a cloud-free machine with enough RAM, to see whether the accuracy gain justifies the cost.

## Speed on CPU vs GPU

- No reliable 2026 head-to-head of faster-whisper and whisper.cpp on Windows CPU was found. Most public comparisons time one 30-second clip on a pre-loaded model. They do not match real video workloads.
- faster-whisper uses CTranslate2. On CPU, int8 quantization is the usual choice. A widely cited README table shows int8 runs roughly twice as fast as fp32, and uses less memory.
- whisper.cpp is the stronger choice on Apple Silicon. A 2026 secondary source reports about 10x real time with Metal on a high-end Mac, versus about 3x for faster-whisper on CPU. That is a Mac-vs-CPU comparison, so it does not transfer to a Windows laptop.
- whisper.cpp 1.8.3 added a large speedup on integrated AMD and Intel GPUs (Vulkan path, per Phoronix). That may help a laptop with integrated graphics, but it is unverified for this use.
- Practical rule: on a CPU-only laptop, expect large-v3-turbo to run below real time on long videos. Cut silence with VAD first, and consider a smaller model (small or medium) for a quick pass.

## Arabic and Egyptian accuracy

- **Stock Whisper is weak on Egyptian.** One Egyptian-focused project reported about 65% WER for stock Whisper on Egyptian, and about 44% for its turbo baseline on a mixed dialect set, before fine-tuning. Fine-tuning brought the validation figure to about 33%.
- **Stock large-v3-turbo on a benchmark with Egyptian data:** about 48.2 WER (Egyptian), versus about 35.7 for large-v3 on the same set, and about 18.5 on Modern Standard Arabic. Source: Arab Voices benchmark, arXiv 2601.13319.
- **Best open-weight Arabic model found:** Cohere Transcribe Arabic, average WER 25.87 on the Hugging Face Arabic leaderboard, about 2.45 points ahead of Meta's OmniASR-LLM-7B. The leaderboard covers MSA and several dialects.
- **Egyptian fine-tunes:** community checkpoints report WER between about 18% and 48%. The numbers use different test sets and normalization, so they cannot be ranked. None is a Common Voice Egyptian score for turbo.
- **NADI 2025 validation:** a SeamlessM4T-v2 Egyptian model reached about 30% WER, and a Whisper-medium system about 39%. The NADI 2026 shared task includes top systems built on large-v3 and cohere-transcribe-arabic.
- **Key test before choosing:** build a 20-30 clip Egyptian test set from real videos the user cares about, transcribe with each candidate, and score WER after the same normalization (diacritics and alef forms removed). Public numbers will not predict performance on the user's own content.

## Word-level timestamps

- faster-whisper: pass `word_timestamps=True`. Works on CPU. Output is a list of words with start and end times.
- whisper.cpp: `--max-len 1 --split-on-word` gives per-word output, or use token timestamps.
- Cohere and NeMo models: word timing depends on the toolkit; check the model card.

## Speaker diarization

- **pyannote.audio** (`speaker-diarization-community-1`, and the older 3.1 pipeline): the usual open choice. It requires a Hugging Face account, accepting the model's terms, and a read token. Setup is a few steps, and first run can fail with HTTP 401 if the terms were not accepted.
- License is unclear across sources. One aggregator lists the weights as CC-BY-4.0. Another says the code is MIT and models are free to use commercially. A WhisperX troubleshooting page describes them as research-only. **Check the current model cards on Hugging Face before any commercial use.**
- Diarization is CPU-heavy. Expect it to add a large fraction of the total transcription time on a laptop.
- Simpler alternative: skip diarization and label speakers by visual cues or by asking the user. Most agent use cases do not need full speaker labels.

## Silence skipping (VAD)

- **Silero VAD** is the standard choice. Install with `pip install silero-vad`. It is about 2 MB, processes a 30 ms chunk in under 1 ms on one CPU thread (maintainer claim), and has an ONNX path that avoids heavy torch use.
- Licensing: the repository is MIT. Some PyPI mirror pages show a CC BY-NC badge, so check the upstream LICENSE file before shipping.
- faster-whisper includes Silero VAD built in (`vad_filter=True`), so no separate install is needed for a basic setup.

## Language auto-detection

- Whisper-family models detect the language from the first 30 seconds. Set `language="ar"` to force Arabic when the user knows the video is Arabic. Auto-detect often misfires on Egyptian and can label it as another Arabic variant or as Persian/Urdu on short or noisy clips.
- For mixed-language videos (Arabic with English), auto-detect per segment is not reliable in Whisper. Consider a separate language check on short windows.

## Install and setup

| Path | Steps | Difficulty |
|---|---|---|
| faster-whisper | `pip install faster-whisper`, then load `large-v3-turbo` with `compute_type="int8"` | Easy |
| whisper.cpp | Download prebuilt binary or build with CMake, then download a GGML model | Medium |
| Cohere Arabic | Install transformers and dependencies, then load from Hugging Face | Medium |
| pyannote | Create HF account, accept terms, create token, pass it to `Pipeline.from_pretrained` | Medium |
| Silero VAD | `pip install silero-vad` | Easy |

## Recommendation for real-eyes

1. Default: faster-whisper, large-v3-turbo, int8, with Silero VAD on. Force `language="ar"` when the caller says so.
2. Offer a `--model` option so users can swap in a stronger Arabic model (Cohere) when they have a GPU or more time.
3. Keep diarization optional. Make it a separate step that needs a Hugging Face token.
4. Before shipping, run the 20-30 clip Egyptian test and record WER and real-time factor on the target laptop. Replace the estimates in this document with those numbers.

## Open questions

- Measured CPU speed on the target Windows laptop for each candidate (not done).
- Whether a faster-whisper-compatible Egyptian fine-tune exists with a verified WER on a shared test set.
- Exact license terms for pyannote community-1 weights, from the model cards.
- Cohere Transcribe Arabic CPU feasibility and memory footprint.

## Sources

- Cohere Transcribe Arabic release (July 2026): https://huggingface.co/blog/CohereLabs/cohere-transcribe-arabic-07-2026-release and https://cohere.com/blog/transcribe-arabic
- Arab Voices benchmark, arXiv 2601.13319: https://arxiv.org/pdf/2601.13319
- Egyptian Whisper fine-tunes: https://huggingface.co/MAdel121/whisper-medium-egy, https://huggingface.co/WafaaFraih/whisper-small-egyptian-arabic-All, https://huggingface.co/dev-ahmedhany/whisper-large-v3-turbo-arabic-ft-lora
- Turbo Arabic fine-tune on Common Voice: https://huggingface.co/mboushaba/whisper-large-v3-turbo-arabic
- Dialect-balanced fine-tunes (oddadmix): https://huggingface.co/oddadmix/whisper-large-v3-arabic-dialectal-v2
- NADI 2025 system paper: https://arxiv.org/pdf/2511.10090
- NADI 2026 shared task: https://arxiv.org/pdf/2609.27086
- Open Universal Arabic ASR Leaderboard: https://github.com/Natural-Language-Processing-Elm/open_universal_arabic_asr_leaderboard
- Qwen3-ASR community fine-tunes: https://friendli.ai/models/oddadmix/qwen3-asr-0.6b-arabic-dialectal
- Whisper.cpp vs faster-whisper discussion: https://dev.to/tildalice/whispercpp-vs-faster-whisper-why-speed-tests-lie-107o
- Phoronix on whisper.cpp 1.8.3 GPU speedup: https://phoronix.com/news/whisper-cpp-1.8.3-12x-perf
- NVIDIA Canary-1B-v2 and Parakeet-TDT-0.6B-v3: https://arxiv.org/html/2509.14128v2
- Moonshine v2 paper (Feb 2026): https://arxiv.org/abs/2602.12241
- Flavors of Moonshine (Sept 2025): https://arxiv.org/abs/2509.02523
- Silero VAD on PyPI: https://pypi.org/project/silero-vad/
- pyannote.audio on PyPI: https://pypi.org/project/pyannote.audio
