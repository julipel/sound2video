# sound2video

Pipeline that dubs an English product-demo video into Russian using OCR/ASR timing and Yandex SpeechKit TTS.

Built for a SonoScape E-Series ultrasound scanner training video, but the scripts are generic.

## What it does

The source video has English narration with Russian captions burned into the picture. Two independent dubbing variants are produced from it:

**Variant 1 — timed to the on-screen captions**
1. `work/transcribe.py` — rough speech-to-text pass with faster-whisper (used only to help verify timing)
2. `work/ocr.ps1` — Windows OCR over extracted video frames to read the burned-in Russian captions
3. `work/group_ocr.py` — collapses consecutive frames with the same caption into timed groups
4. `work/ocr_sheets.py` — contact sheets for manually checking OCR groups
5. `work/refine_times.py` — refines each caption's start/end by diffing frame pixels against a template
6. `work/check_fades.py` — sanity-checks fade in/out timing at a couple of boundaries
7. `work/finalize_subtitles.py` — applies manual OCR-error fixes, writes `outputs/project/subs/subtitles.srt` / `.json`
8. `work/tts_generate.py` — synthesizes each subtitle line with Yandex SpeechKit (voice `jane`)
9. `work/tts_fit.py` — time-stretches each line to its subtitle slot (natural pace when it fits, capped speed-up otherwise, silence-padded rather than over-stretched)
10. `work/assemble_output.py` — builds the full narration track and muxes it over the original video (audio replaced, video re-encoded not required — copied)

**Variant 2 — timed to the original English speech, translated**
1. `work/transcribe_en.py` — full English transcript with per-segment timing (faster-whisper)
2. Translated by hand into `work/translation_ru.json`, same segment ids/timing as the English transcript
3. `work/tts_generate_v2.py` / `work/tts_fit_v2.py` / `work/assemble_output_v2.py` — same TTS/fit/assemble approach as variant 1, but driven by the translated segments instead of the OCR subtitles

Both fit scripts push a line's start later (instead of overlapping voices) when even the speed-up cap can't make it fit; drift is usually reabsorbed by the next natural pause.

## Setup

```
py -3.12 -m venv work/py-venv
work/py-venv/Scripts/pip install faster-whisper
```

ffmpeg/ffprobe are expected at `outputs/project/tools/ffmpeg-9.0.1-essentials_build/bin/`.

Copy `.env.example` to `.env` and fill in a Yandex Cloud SpeechKit API key + folder id:

```
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
```

## Layout

```
outputs/project/
  input/            source video (not tracked)
  subs/             final subtitles.srt / subtitles.json (variant 1)
  audio_raw/        raw TTS per line, variant 1 (not tracked)
  audio_fitted/     time-fitted TTS per line, variant 1 (not tracked)
  audio_raw_v2/     raw TTS per line, variant 2 (not tracked)
  audio_fitted_v2/  time-fitted TTS per line, variant 2 (not tracked)
  output/           final dubbed videos (not tracked)
  tools/            portable ffmpeg build (not tracked)
work/
  *.py, ocr.ps1     pipeline scripts
  ocr-*.json(l)     OCR intermediate data
  transcript*.json  Whisper transcripts (English + progress logs)
  translation_ru.json  Russian translation used by variant 2
```

Generated media, the Whisper model cache, and Python environments are gitignored — rerunning the scripts regenerates them locally.
