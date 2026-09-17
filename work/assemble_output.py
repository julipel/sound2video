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

video = next((ROOT / 'outputs' / 'project' / 'input').glob('*.mp4'))
subs = json.loads((ROOT / 'outputs' / 'project' / 'subs' / 'subtitles.json').read_text(encoding='utf-8'))
fit_dir = ROOT / 'outputs' / 'project' / 'audio_fitted'
out_dir = ROOT / 'outputs' / 'project' / 'output'
out_dir.mkdir(parents=True, exist_ok=True)
silence_dir = ROOT / 'work' / '_silence'
silence_dir.mkdir(exist_ok=True)

video_duration = float(subprocess.run(
    [FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
     '-of', 'default=noprint_wrappers=1:nokey=1', str(video)],
    capture_output=True, text=True, check=True).stdout.strip())

def silence_path(dur: float) -> Path:
    p = silence_dir / f'sil_{dur:.3f}.wav'
    if not p.exists():
        subprocess.run([FFMPEG, '-y', '-f', 'lavfi', '-i', f'anullsrc=r={SR}:cl=stereo',
                         '-t', f'{dur:.3f}', '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(p)],
                        capture_output=True, text=True, check=True)
    return p

def probe_duration(path: Path) -> float:
    return float(subprocess.run(
        [FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
        capture_output=True, text=True, check=True).stdout.strip())

pieces = []
cursor = 0.0
delayed = []
for sub in subs:
    clip_path = fit_dir / f"{sub['id']:03d}.wav"
    clip_dur = probe_duration(clip_path)
    actual_start = max(sub['start'], cursor)
    if actual_start - sub['start'] > 0.02:
        delayed.append((sub['id'], actual_start - sub['start']))
    gap = actual_start - cursor
    if gap > 0.005:
        pieces.append(silence_path(gap))
    pieces.append(clip_path)
    cursor = actual_start + clip_dur
trailing = video_duration - cursor
if trailing > 0.005:
    pieces.append(silence_path(trailing))
elif trailing < -0.005:
    print(f'WARNING: narration overruns video by {-trailing:.2f}s; trailing audio will be cut by -shortest', flush=True)
if delayed:
    print(f'{len(delayed)} line(s) pushed later than their caption start (max delay '
          f'{max(d for _, d in delayed):.2f}s by the end): {delayed}', flush=True)

list_path = ROOT / 'work' / '_concat_list.txt'
with list_path.open('w', encoding='utf-8') as f:
    for p in pieces:
        f.write(f"file '{p.resolve().as_posix()}'\n")

track_path = out_dir / 'narration.wav'
r = subprocess.run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(list_path),
                     '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(track_path)],
                    capture_output=True, text=True)
if r.returncode != 0:
    raise RuntimeError(r.stderr)

track_duration = float(subprocess.run(
    [FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
     '-of', 'default=noprint_wrappers=1:nokey=1', str(track_path)],
    capture_output=True, text=True, check=True).stdout.strip())
print(f'video_duration={video_duration:.3f}  track_duration={track_duration:.3f}', flush=True)
assert abs(track_duration - video_duration) < 1.0, 'assembled track duration mismatch'

final_path = out_dir / (video.stem + '_dubbed.mp4')
r = subprocess.run([FFMPEG, '-y', '-i', str(video), '-i', str(track_path),
                     '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
                     '-c:a', 'aac', '-b:a', '192k', '-shortest', str(final_path)],
                    capture_output=True, text=True)
if r.returncode != 0:
    raise RuntimeError(r.stderr)

print(f'DONE: {final_path}', flush=True)
