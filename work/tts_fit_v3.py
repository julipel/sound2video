import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / 'outputs' / 'project' / 'tools' / 'ffmpeg-9.0.1-essentials_build' / 'bin'
FFMPEG = str(BIN / 'ffmpeg.exe')
SR = 44100

raw_dir = ROOT / 'outputs' / 'project' / 'audio_raw_v3'
fit_dir = ROOT / 'outputs' / 'project' / 'audio_fitted_v3'
fit_dir.mkdir(parents=True, exist_ok=True)

# Real recorded voice: never time-stretched, just converted to a consistent format.
for raw_path in sorted(raw_dir.glob('*.mp3')):
    fit_path = fit_dir / (raw_path.stem + '.wav')
    cmd = [FFMPEG, '-y', '-i', str(raw_path), '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(fit_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{raw_path.name} ffmpeg failed:\n{r.stderr}")
    print(f"{raw_path.name} -> {fit_path.name}", flush=True)

print('DONE', flush=True)
