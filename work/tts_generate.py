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

subs = json.loads((ROOT / 'outputs' / 'project' / 'subs' / 'subtitles.json').read_text(encoding='utf-8'))
out_dir = ROOT / 'outputs' / 'project' / 'audio_raw'
out_dir.mkdir(parents=True, exist_ok=True)

# Shortened phrasing for TTS only (subtitles.json/srt keep the original verbatim text).
# These lines' slots are too short to read the full caption at natural pace even
# at the 2x speed cap, so the wording is trimmed while keeping the meaning.
TTS_OVERRIDES = {
    71: 'Чтобы сместить объём в сосуде, двигайте трекбол',
    77: 'Допплеровский спектр запускается автоматически.',
    78: 'Для триплексного режима нажмите "Одноврем"',
    79: 'Выберите пункт меню и включите режим триплекса',
    82: 'Регулировка базовой линии',
    83: 'и шкалы скорости допплера',
    92: 'SonoHelp вызывается кнопкой P2',
    93: 'SonoHelp даёт рекомендации по проведению обследования',
    94: 'SonoHelp - это обучающий справочник по УЗИ.',
    95: 'Как справочник для менее опытных специалистов,',
    96: 'SonoHelp охватывает печень, почки, сердце, молочные железы, щитовидную железу, акушерство и сосуды.',
    110: 'Наведите курсор и нажмите Set',
    111: 'Появится второй курсор',
    112: 'Второй курсор — и снова Set',
    124: 'Изображения сохранятся на диске аппарата',
}

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
    text = TTS_OVERRIDES.get(sub['id'], sub['text'])
    text = text.replace('\n', ' ').replace('<', '').replace('>', '')
    text = text.replace('SonoScape', 'Соноскейп').strip()
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
