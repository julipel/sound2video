import os
import re
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
os.environ['HF_HOME'] = str(ROOT / 'work' / 'hf-cache')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['HF_HUB_DISABLE_XET'] = '1'
from faster_whisper import WhisperModel

model_path = next((ROOT / 'work' / 'models' / 'models--Systran--faster-whisper-small' / 'snapshots').iterdir())
model = WhisperModel(str(model_path), device='cpu', compute_type='int8', cpu_threads=4,
                     download_root=str(ROOT / 'work' / 'models'))

src = Path(r"C:\Users\jpel4\Sound2video\mp3\mp3")
def key(p):
    m = re.match(r'(\d+)\.', p.name)
    return int(m.group(1)) if m else 999
files = sorted(src.glob('*.mp3'), key=key)

results = []
for f in files:
    segments, info = model.transcribe(str(f), language='ru', beam_size=5, vad_filter=True)
    text = ' '.join(s.text.strip() for s in segments)
    n = key(f)
    results.append({'n': n, 'file': f.name, 'text': text})
    print(f"{n:>2}  {text}", flush=True)

(ROOT / 'work' / 'voiceover_transcript.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('DONE', flush=True)
