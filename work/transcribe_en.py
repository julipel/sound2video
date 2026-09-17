import os
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
os.environ['HF_HOME'] = str(ROOT / 'work' / 'hf-cache')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['HF_HUB_DISABLE_XET'] = '1'
from faster_whisper import WhisperModel

model_path = next((ROOT / 'work' / 'models' / 'models--Systran--faster-whisper-small' / 'snapshots').iterdir())
print('Loading Whisper small on CPU (int8)', flush=True)
model = WhisperModel(str(model_path), device='cpu', compute_type='int8', cpu_threads=4,
                     download_root=str(ROOT / 'work' / 'models'))
segments, info = model.transcribe(str(ROOT / 'work' / 'speech.wav'),
    language='en', beam_size=5, vad_filter=True, word_timestamps=True)
print(f'Language: {info.language}, probability: {info.language_probability:.3f}, duration: {info.duration:.1f}', flush=True)

raw = []
progress_path = ROOT / 'work' / 'transcript-en-progress.jsonl'
with progress_path.open('w', encoding='utf-8') as progress:
    for segment in segments:
        item = {'id': len(raw) + 1, 'start': round(segment.start, 3),
                 'end': round(segment.end, 3), 'text': segment.text.strip()}
        if not item['text'] or item['end'] <= item['start']:
            continue
        raw.append(item)
        progress.write(json.dumps(item, ensure_ascii=False) + '\n')
        progress.flush()
        print(f"{item['id']}: {item['start']:.2f} -> {item['end']:.2f} {item['text']}", flush=True)

(ROOT / 'work' / 'transcript-en.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'DONE: {len(raw)} English segments saved', flush=True)
