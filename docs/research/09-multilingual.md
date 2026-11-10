# Multilingual transcription, translation and OCR for tapetum (research, Nov 2026)

Scope: how tapetum can transcribe, translate and read on-screen text for videos in many languages, using open models that run locally and install with pip. The earlier note in `02-speech-to-text.md` covers Arabic and Egyptian in depth, so this note does not repeat that work. It covers the wider language set and the parts around transcription: language ID, code-switching, translation, platform subtitles and OCR.

## Bottom line

Use one default that covers almost everything, and add optional engines for specific language groups.

- **Default:** faster-whisper with large-v3-turbo (int8), plus Silero VAD. Whisper covers about 99 languages under the MIT license. It is the only option here that is both broad and easy to install.
- **Better per group, opt-in:** Qwen3-ASR (Apache 2.0) for Chinese dialects and as a second opinion for Arabic. Cohere Transcribe (Apache 2.0) for its 14 languages, if the machine can run it.
- **Translation:** MADLAD-400 3B for coverage (419 languages, Apache 2.0 per its Hugging Face metadata, but heavy). Argos Translate as the light pip-only fallback (MIT).
- **Avoid as defaults:** NLLB-200 and SeamlessM4T v2 are CC-BY-NC 4.0, and MMS-LID-256 is also non-commercial. tapetum cannot ship them as defaults if it might ever be used commercially.
- **OCR:** PaddleOCR (Apache 2.0) as the default for non-Latin text. Tesseract as the fallback.

Almost none of the WER numbers below were measured on the target machine, and several come from vendor or secondary sources. Section 7 lists what still needs a real test.

## 1. Transcription by language group

| Language group | Best open option found | Evidence | License | Notes |
|---|---|---|---|---|
| English, Spanish, French, German, Italian, Portuguese, Dutch, Polish, Russian | Whisper large-v3-turbo; Cohere Transcribe for the 14 languages it covers; NVIDIA Canary-1B-v2 for 25 European languages | Cohere reports 5.42 average WER on the Open ASR leaderboard (vendor claim). TechCrunch reported Cohere trailing rivals on Portuguese, German and Spanish. Canary-1B-v2 mirror card: 8.40% WER on FLEURS-25 (not verified on the official card). | Whisper MIT; Cohere Apache 2.0; Canary-1B-v2 CC-BY-4.0 | Canary-1B-v2 is licensed for commercial use. The older canary-1b is CC-BY-NC, so do not confuse the two. |
| Arabic (MSA and dialects, including Egyptian) | Cohere Transcribe Arabic; Qwen3-ASR as a second opinion. Details in `02-speech-to-text.md`. | Cohere Arabic average WER 25.87 on the Arabic leaderboard (per the earlier note). Stock turbo about 48% WER on Egyptian. | See note 02 | Arabic is not in Canary-1B-v2's language list. |
| Chinese (Mandarin, Cantonese, other dialects) | Qwen3-ASR (1.7B, or 0.6B on CPU); Whisper; Cohere | Qwen3-ASR covers 30 languages and 22 Chinese dialects, per the model card as reproduced on GGUF pages. Figures from secondary sites are inconsistent. | Qwen3-ASR Apache 2.0 (secondary sources; confirm on the official card) | Chinese output is scored by CER, not WER. |
| Japanese, Korean | Whisper large-v3-turbo; Cohere; Qwen3-ASR | Cohere lists both. No per-language WER verified for Whisper turbo. | Apache 2.0 for Cohere and Qwen3-ASR | Scored by CER. |
| Hindi, Urdu | Whisper large-v3-turbo; Omnilingual ASR; Qwen3-ASR (only if it lists them, which was not verified) | No per-language WER verified. Omnilingual reports CER below 10 for 78% of its 1,600 languages, with a 95% rate for languages that have at least 10 hours of training audio. | Omnilingual Apache 2.0 | Hindi and Urdu share most of their speech. Test both with the same model and script handling. |
| Turkish | Whisper large-v3-turbo; Cohere is not on its list | Community turbo fine-tune reports about 18.9% WER (selimc); small Turkish fine-tune reports 7.75% (emredeveloper). Different sets, so not comparable. Base turbo number not found. | Whisper MIT | Turkish is not in Canary-1B-v2's list. |
| Persian | Whisper large-v3-turbo; Omnilingual | No verified per-language WER. Persian and Arabic share a script, so Arabic-script language ID can confuse them. | Whisper MIT; Omnilingual Apache 2.0 | Watch for Persian labelled as Arabic or Urdu on short clips. |
| Indonesian | Whisper large-v3-turbo; Qwen3-ASR (check the list) | No verified per-language number. Community fine-tunes exist on Hugging Face. | Whisper MIT | Usually one of Whisper's better-covered languages. |
| Any language not listed above | Omnilingual ASR (1,600+ languages, with a 7B LLM variant) | CER-based results only, from Meta. | Apache 2.0 | Heavy. Use as an opt-in fallback when Whisper returns no usable text. |

**Models not recommended for this use:**

- **SeamlessM4T v2:** CC-BY-NC 4.0. Covers 101 languages for speech input. A secondary source reports 18.5% ASR WER on FLEURS-77, but the official metrics were not checked.
- **MMS (ASR):** Meta's older MMS models are CC-BY-NC for the released checkpoints. Check the card before any use.
- **distil-whisper:** English only.
- **Parakeet TDT 0.6B v3 / Canary-1B-v2:** European languages only. No Arabic, Hindi, Turkish, Persian or CJK.

## 2. Language identification and code-switching

### Auto-detection

- **Whisper** detects the language from the first 30 seconds. Silence, music or an intro in another language can make it pick the wrong one. Safe practice: pass `language=` when the user supplies it, and otherwise run detection on several windows (start, middle, end) and take a majority vote.
- **Qwen3-ASR** includes its own language identification step. Compare it with Whisper on the same clips before relying on either one.
- **Standalone LID, text-based:** fastText `lid.176` (MIT, about 126 MB, 176 languages) is fast and easy to install. It works on a transcript, not on audio, so use it to double-check a transcript's language rather than to pick the language before transcribing.
- **Standalone LID, audio-based:** MMS-LID covers 4,000+ languages, but the checkpoints found (`mms-lid-256`) are CC-BY-NC 4.0. The larger `mms-lid-4017` checkpoint exists, but its license was not confirmed. GlotLID and OpenLID are alternatives, and their licenses still need checking.
- **Accuracy:** no head-to-head accuracy numbers were found for these LID tools on the same test set. Measure them yourself.

### Code-switching (Arabic and English)

- The Casablanca paper (arXiv 2410.04527) reports that whisper-large-v3 failed on code-switched Arabic-English. It produced transliteration rather than mixed text. With the language set to English, it translated instead of transcribing. This is the main risk for tapetum: English words in an Arabic video may come out translated or transliterated.
- A fine-tune on Arabic-English code-switched data exists (`MohamedRashad/Arabic-Whisper-CodeSwitching-Edition`). Its accuracy numbers were not verified.
- **Practical plan:**
  1. Set the primary language explicitly when known.
  2. Keep English words as they come out. Do not try to force them into Arabic.
  3. Where the script changes, split the transcript by script (Arabic letters vs Latin letters) after decoding. This is a cheap way to label English spans, and tapetum can do it without another model. Treat it as a suggestion to test, not a verified method.
  4. If a video is mostly code-switched, consider a fine-tune or a second pass with Qwen3-ASR.

## 3. Translation (offline, free)

Translation would let the agent call `--translate en` on any transcript.

| Model / tool | Coverage | Size (approx.) | License | Quality evidence |
|---|---|---|---|---|
| **MADLAD-400 3B-MT** | 419 languages | About 3B parameters; heavy on CPU | Apache 2.0 (per the Hugging Face metadata) | Widest coverage found. One guide says NLLB-3.3B beats it on well-resourced pairs. Test your own pairs. |
| **NLLB-200 (600M / 1.3B / 3.3B)** | 200 languages | 600M is light enough for CPU | **CC-BY-NC 4.0** (non-commercial) | Strong on low-resource pairs. Ruled out as default by the license. |
| **TranslateGemma (4B / 12B / 27B)** | 55 languages | 4B is the practical CPU size | Gemma terms | A guide reports 12B beating Gemma 3 27B on WMT24++ (MetricX 3.60 vs 4.04, lower is better). No direct comparison to NLLB or MADLAD was found. |
| **Opus-MT (Helsinki-NLP)** | One model per language pair | About 300 MB per pair | Check the model card; likely CC-BY-4.0 but not verified | Smaller and faster. One personal test found its output more natural but less accurate. |
| **Argos Translate** | Around 15+ languages on the 1.5 list (Arabic, Chinese, Hindi, Turkish, Japanese, Korean, Russian, Spanish, Polish, Portuguese, Vietnamese and others) | About 100 MB per pair (not verified) | MIT (code). Model licenses may vary. | Built on CTranslate2. Pip install, offline. It can pivot through English when a direct pair is missing. Check the current language list before use. |

**Recommendation for tapetum:**

- Default: MADLAD-400 3B (if the machine has the RAM) or Argos Translate (light, pip-only). Argos covers the common languages with small files.
- Avoid NLLB and SeamlessM4T in the default path because of their license. They can be offered as an explicit opt-in with a warning.
- For translation quality, expect better results with an LLM, but that means a remote or local LLM, which is outside this scope.

## 4. Platform subtitle quirks (YouTube and others)

- **Three kinds of track:**
  - Manual subtitles: written by the creator or a translator. Usually the most accurate.
  - Auto-generated captions: YouTube's speech recognition in the spoken language.
  - Auto-translated tracks: machine translations of caption text into other languages. They stack two machine steps, so errors add up.
- **Order to use:** prefer manual subtitles in the spoken language, then auto-generated captions in the spoken language, and skip auto-translated tracks unless the user asks for them.
- **yt-dlp flags:** `--write-subs` fetches manual tracks and `--write-auto-subs` fetches auto-generated ones. Use `--sub-langs` to limit the list. In the Python API, manual tracks are under `info["subtitles"]` and auto-generated ones under `info["automatic_captions"]`.
- **Gotcha:** one yt-dlp issue reports that translated English tracks get downloaded even when not requested. Filter by language code explicitly.
- **Rate limits:** HTTP 429 errors have been reported on translated tracks more than on manual tracks or original-language auto-captions.
- **Language codes:** YouTube uses codes like `en`, `en-US`, `ar`, `ar-EG`. Match on the base code first and fall back to the regional one.
- **Tapetum rule:** record which track was used (manual, auto, or translated) in the output metadata, so the agent knows how much to trust it. A manual track needs no ASR. Auto-generated and translated tracks should be checked against the audio when accuracy matters.

## 5. OCR for on-screen text

| Engine | Scripts | License | Notes |
|---|---|---|---|
| **PaddleOCR** (v3.x, latest release 2026) | Arabic, Chinese, Japanese, Korean, Devanagari and many more through language models | Apache 2.0 (code). Check the weights for each model. | Best accuracy among the open options in the sources found. Heavier (about 500 MB to 1 GB of memory, per one source). |
| **Tesseract 5** | 100+ languages with traineddata | Apache 2.0 | Lightweight, fast, pip-friendly through `pytesseract` (needs the binary installed). Weaker on stylized or curved Arabic text. Good fallback. |
| **EasyOCR** | Around 80 languages | Check the repository (not verified in the search) | Uses PyTorch, so it is heavier (1 to 2 GB). Known issues with some symbols. |
| **RapidOCR** | Inherits PaddleOCR's models | Not verified | Lighter PaddleOCR-style stack on ONNX. Worth testing as a lighter default. |
| **Surya** | 90+ languages | Code is GPL-3.0; weights have a separate license with limits | Avoid for an open-source default because of the license. |

**Recommendation for tapetum:** use PaddleOCR as the default for on-screen text, and fall back to Tesseract when PaddleOCR is not installed. Run OCR on sampled frames, not every frame, to save time. For Arabic and Devanagari, test on real frames first, since OCR accuracy on those scripts was not measured in this research.

## 6. Recommended tiered strategy (pip-installable)

**Tier 0. Always on, pip only**
- Transcription: `faster-whisper` with `large-v3-turbo`, int8, Silero VAD.
- Language: explicit `--lang` if given, otherwise Whisper detection on three windows, then a majority vote.
- Subtitles: use manual tracks first (yt-dlp `--write-subs`), then auto-generated tracks.
- Translation: `argostranslate` for common pairs.
- OCR: `pytesseract` with Tesseract installed on the system.

**Tier 1. Opt-in for better accuracy by group**
- Chinese and Arabic second opinion: Qwen3-ASR 0.6B (CPU) or 1.7B (GPU). Confirm the pip install path on the official card.
- Arabic and European languages: Cohere Transcribe, if the machine has the RAM (2B parameters).
- Translation: MADLAD-400 3B as the heavier, wider option.
- OCR: PaddleOCR (`paddleocr`) for non-Latin scripts.

**Tier 2. Rare or unlisted languages**
- Omnilingual ASR (Apache 2.0), as the fallback when Tier 0 and Tier 1 return little or nothing. It is large, so run it only on request.

**Never as defaults (license)**
- NLLB-200, SeamlessM4T v2, MMS-LID-256, Surya (weights).

**Agent interface:** let the agent ask for `--lang`, `--translate`, `--ocr` and `--engine`. Print the engine, the model, the language-ID method and the subtitle source with each result.

## 7. Open questions and what to test

- Per-language WER for Whisper large-v3-turbo on FLEURS for Hindi, Urdu, Turkish, Persian, Indonesian, Japanese and Korean. The official Whisper paper's appendix is the place to check.
- Qwen3-ASR's full language list and its official WER tables (arXiv 2601.21337).
- Omnilingual ASR's WER for Hindi and Urdu, since Meta reports CER only.
- Language-ID accuracy on code-switched Arabic-English clips for Whisper, Qwen3-ASR, and lid.176 on transcripts.
- Opus-MT and Argos model licenses, and Argos file sizes per pair.
- RapidOCR and EasyOCR licenses, and OCR accuracy on Arabic and Devanagari frames.
- CPU speed and memory for MADLAD-400 3B and Cohere Transcribe on the target laptop.

Suggested test: build a 20-clip test set per group (Arabic, Chinese, Hindi and Urdu, Turkish, Spanish, plus one code-switched Arabic-English set), score each candidate on the same normalized text, and record real-time factor. Use manual subtitles as reference text where the video has them.

## Sources

- Qwen3-ASR technical report (arXiv 2601.21337): https://arxiv.org/pdf/2601.21337
- Qwen3-ASR-1.7B GGUF card (license and language list, reproduced): https://huggingface.co/handy-computer/Qwen3-ASR-1.7B-gguf
- Meta Omnilingual ASR, Apache 2.0 models: https://huggingface.co/facebook/omniASR-LLM-7B
- Cohere Transcribe docs and release: https://docs.cohere.com/docs/transcribe and https://huggingface.co/coherelabs/cohere-transcribe-03-2026
- Cohere Transcribe coverage of TechCrunch's critique: https://techcrunch.com/?p=3106435
- NVIDIA Canary-1B-v2 mirror card: https://cloudfare-proxy.pages.dev/nvidia/canary-1b-v2 (verify on https://huggingface.co/nvidia/canary-1b-v2)
- SeamlessM4T v2 card (CC-BY-NC 4.0): https://huggingface.co/facebook/seamless-m4t-v2-large
- Whisper large-v3-turbo per-language comparisons (secondary): https://vexascribe.com/whisper-large-v3-vs-turbo
- Casablanca paper on Arabic dialects and code-switching (arXiv 2410.04527): https://arxiv.org/pdf/2410.04527
- Arabic-Whisper code-switching fine-tune: https://huggingface.co/MohamedRashad/Arabic-Whisper-CodeSwitching-Edition
- MMS-LID-256 card (CC-BY-NC 4.0): https://huggingface.co/facebook/mms-lid-256
- fastText language identification (lid.176, MIT): https://fasttext.cc/docs/en/language-identification
- MADLAD-400 3B card (Apache 2.0 per metadata): https://huggingface.co/google/madlad400-3b-mt
- NLLB vs MADLAD vs Opus-MT vs TranslateGemma comparison guide: https://insiderllm.com/guides/best-local-llms-translation/
- Argos Translate on PyPI: https://pypi.org/project/argostranslate
- yt-dlp auto-translated track issue: https://github.com/yt-dlp/yt-dlp/issues/13831
- OCR engine comparison (vendor-run, treat as rough): https://unstract.com/blog/best-opensource-ocr-tools/
- Earlier research note on Arabic and Egyptian: [02-speech-to-text.md](02-speech-to-text.md)
