import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / 'outputs' / 'project' / 'tools' / 'ffmpeg-9.0.1-essentials_build' / 'bin'
FFMPEG = str(BIN / 'ffmpeg.exe')
FFPROBE = str(BIN / 'ffprobe.exe')
SR = 44100
MAX_TEMPO = 2.0  # cap on speed-up; never slow down, never speed up beyond this

subs = json.loads((ROOT / 'work' / 'translation_ru.json').read_text(encoding='utf-8'))
raw_dir = ROOT / 'outputs' / 'project' / 'audio_raw_v2'
fit_dir = ROOT / 'outputs' / 'project' / 'audio_fitted_v2'
fit_dir.mkdir(parents=True, exist_ok=True)

def probe_duration(path: Path) -> float:
    out = subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
                           '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                          capture_output=True, text=True, check=True)
    return float(out.stdout.strip())

still_over = []
for sub in subs:
    raw_path = raw_dir / f"{sub['id']:03d}.ogg"
    fit_path = fit_dir / f"{sub['id']:03d}.wav"
    target = sub['end'] - sub['start']
    if fit_path.exists():
        fit_path.unlink()
    raw_dur = probe_duration(raw_path)
    tempo = min(raw_dur / target, MAX_TEMPO) if raw_dur > target else 1.0
    post_dur = raw_dur / tempo
    fits = post_dur <= target + 0.02

    if tempo == 1.0 and fits:
        filt = 'apad'
    elif tempo == 1.0:
        filt = None
    elif fits:
        filt = f'rubberband=tempo={tempo:.4f},apad'
    else:
        filt = f'rubberband=tempo={tempo:.4f}'

    cmd = [FFMPEG, '-y', '-i', str(raw_path)]
    if filt:
        cmd += ['-filter:a', filt]
    if fits:
        cmd += ['-t', f'{target:.3f}']
    cmd += ['-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(fit_path)]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"id={sub['id']} ffmpeg failed:\n{r.stderr}")

    out_dur = probe_duration(fit_path)
    flag = '' if fits else f'  OVERFLOW +{out_dur - target:.2f}s'
    print(f"{sub['id']:03d}/{len(subs)}: raw={raw_dur:.2f}s target={target:.2f}s tempo={tempo:.2f} out={out_dur:.2f}s{flag}", flush=True)
    if not fits:
        still_over.append((sub['id'], out_dur - target))

print(f'DONE: fitted {len(subs)} clips in {fit_dir}', flush=True)
if still_over:
    print(f'{len(still_over)} lines still overflow their slot even at {MAX_TEMPO}x '
          f'(total excess {sum(x[1] for x in still_over):.1f}s)', flush=True)
