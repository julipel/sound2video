import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent

for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ['YANDEX_API_KEY']
FOLDER_ID = os.environ['YANDEX_FOLDER_ID']
URL = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
VOICE = 'jane'

subs = json.loads((ROOT / 'work' / 'translation_ru.json').read_text(encoding='utf-8'))
out_dir = ROOT / 'outputs' / 'project' / 'audio_raw_v2'
out_dir.mkdir(parents=True, exist_ok=True)

def synthesize(text: str) -> bytes:
    data = urllib.parse.urlencode({
        'text': text,
        'lang': 'ru-RU',
        'voice': VOICE,
        'format': 'oggopus',
        'folderId': FOLDER_ID,
    }).encode('utf-8')
    req = urllib.request.Request(URL, data=data, headers={'Authorization': f'Api-Key {API_KEY}'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()

done = 0
for sub in subs:
    path = out_dir / f"{sub['id']:03d}.ogg"
    if path.exists() and path.stat().st_size > 0:
        continue
    text = sub['text'].replace('\n', ' ').replace('<', '').replace('>', '').strip()
    for attempt in range(3):
        try:
            audio = synthesize(text)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace')
            if attempt == 2:
                raise RuntimeError(f"id={sub['id']} failed: {e.code} {body}") from e
            print(f"retry id={sub['id']}: {e.code} {body}", flush=True)
            time.sleep(1.5)
    path.write_bytes(audio)
    done += 1
    print(f"{sub['id']:03d}/{len(subs)}: {len(audio)} bytes  {text[:60]}", flush=True)

print(f'DONE: generated {done} new clips (of {len(subs)} total) in {out_dir}', flush=True)
