import os
import json
from pathlib import Path
from datetime import timedelta

ROOT = Path(__file__).resolve().parent.parent
os.environ['HF_HOME'] = str(ROOT / 'work' / 'hf-cache')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['HF_HUB_DISABLE_XET'] = '1'
from faster_whisper import WhisperModel
import srt

out = ROOT / 'outputs' / 'project' / 'subs'
print('Loading Whisper small on CPU (int8)', flush=True)
model_path = next((ROOT / 'work' / 'models' / 'models--Systran--faster-whisper-small' / 'snapshots').iterdir())
model = WhisperModel(str(model_path), device='cpu', compute_type='int8', cpu_threads=4,
                     download_root=str(ROOT / 'work' / 'models'))
segments, info = model.transcribe(str(ROOT / 'work' / 'speech.wav'),
    beam_size=5, vad_filter=True, word_timestamps=True)
print(f'Language: {info.language}, probability: {info.language_probability:.3f}', flush=True)
raw = []
with (ROOT / 'work' / 'transcript-progress.jsonl').open('w', encoding='utf-8') as progress:
    for segment in segments:
        item = {'id': len(raw)+1, 'start': round(segment.start,3),
                'end': round(segment.end,3), 'text': segment.text.strip(),
                'words': [{'start': round(w.start,3), 'end': round(w.end,3),
                           'word': w.word, 'probability': w.probability} for w in segment.words or []]}
        if not item['text'] or item['end'] <= item['start']:
            continue
        raw.append(item)
        progress.write(json.dumps(item, ensure_ascii=False)+'\n')
        progress.flush()
        print(f"{item['id']}: {item['start']:.2f} -> {item['end']:.2f} {item['text']}", flush=True)
subs = [srt.Subtitle(index=i['id'], start=timedelta(seconds=i['start']),
                    end=timedelta(seconds=i['end']), content=i['text']) for i in raw]
srt_path = out / 'subtitles.srt'
srt_path.write_text(srt.compose(subs), encoding='utf-8')
parsed = [{'id': s.index, 'start': s.start.total_seconds(), 'end': s.end.total_seconds(),
           'duration': round((s.end-s.start).total_seconds(),3), 'text': s.content}
          for s in srt.parse(srt_path.read_text(encoding='utf-8'))]
(out / 'subtitles.json').write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding='utf-8')
(ROOT / 'work' / 'whisper-details.json').write_text(json.dumps({
    'model': 'small', 'language': info.language, 'language_probability': info.language_probability,
    'segments': raw}, ensure_ascii=False, indent=2), encoding='utf-8')
assert len(parsed) == len(raw) and parsed
assert all(0 <= s['start'] < s['end'] <= info.duration + 0.1 for s in parsed)
assert all(a['end'] <= b['start'] + .001 for a,b in zip(parsed, parsed[1:]))
print(f'DONE: {len(parsed)} subtitles saved to {out}', flush=True)
