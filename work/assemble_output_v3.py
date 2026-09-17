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
nocaptions = next((ROOT / 'outputs' / 'project' / 'output').glob('*_nocaptions.mp4'))
anchors = json.loads((ROOT / 'work' / 'va_anchors.json').read_text(encoding='utf-8'))
fit_dir = ROOT / 'outputs' / 'project' / 'audio_fitted_v3'
out_dir = ROOT / 'outputs' / 'project' / 'output'
silence_dir = ROOT / 'work' / '_silence_v3'
silence_dir.mkdir(exist_ok=True)

def probe_duration(path: Path) -> float:
    return float(subprocess.run(
        [FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
        capture_output=True, text=True, check=True).stdout.strip())

video_duration = probe_duration(video)

def silence_path(dur: float) -> Path:
    p = silence_dir / f'sil_{dur:.3f}.wav'
    if not p.exists():
        subprocess.run([FFMPEG, '-y', '-f', 'lavfi', '-i', f'anullsrc=r={SR}:cl=stereo',
                         '-t', f'{dur:.3f}', '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(p)],
                        capture_output=True, text=True, check=True)
    return p

# monotonic clamp: VA files play in numeric order, so their anchors can't run backwards
items = sorted(anchors.items(), key=lambda kv: int(kv[0]))
prev = 0.0
clamped = []
for n, t in items:
    t = max(t, prev)
    clamped.append((int(n), t))
    prev = t

pieces = []
cursor = 0.0
delayed = []
for n, anchor in clamped:
    clip_path = fit_dir / f'{n:02d}.wav'
    clip_dur = probe_duration(clip_path)
    actual_start = max(anchor, cursor)
    if actual_start - anchor > 0.02:
        delayed.append((n, actual_start - anchor))
    gap = actual_start - cursor
    if gap > 0.005:
        pieces.append(silence_path(gap))
    pieces.append(clip_path)
    cursor = actual_start + clip_dur

print(f'VA track covers 0 -> {cursor:.2f}s ({len(delayed)} clip(s) delayed, '
      f'max {max((d for _, d in delayed), default=0):.2f}s)', flush=True)

list_path = ROOT / 'work' / '_concat_list_v3.txt'
with list_path.open('w', encoding='utf-8') as f:
    for p in pieces:
        f.write(f"file '{p.resolve().as_posix()}'\n")

va_track = out_dir / 'narration_v3_partial.wav'
r = subprocess.run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(list_path),
                     '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(va_track)],
                    capture_output=True, text=True)
if r.returncode != 0:
    raise RuntimeError(r.stderr)

# From where the VA track ends, resume the ORIGINAL audio (in sync with picture)
# for the remainder of the video, which the VA recording never covered.
full_track = out_dir / 'narration_v3.wav'
r = subprocess.run([
    FFMPEG, '-y',
    '-i', str(va_track),
    '-ss', f'{cursor:.3f}', '-i', str(video),
    '-filter_complex',
    f'[1:a]atrim=start=0:duration={video_duration - cursor:.3f},asetpts=PTS-STARTPTS[tail];'
    f'[0:a][tail]concat=n=2:v=0:a=1[out]',
    '-map', '[out]', '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(full_track)],
    capture_output=True, text=True)
if r.returncode != 0:
    raise RuntimeError(r.stderr)

full_duration = probe_duration(full_track)
print(f'video_duration={video_duration:.3f}  full_track_duration={full_duration:.3f}', flush=True)

final_path = out_dir / (video.stem + '_ru_voiceover_dub.mp4')
r = subprocess.run([FFMPEG, '-y', '-i', str(nocaptions), '-i', str(full_track),
                     '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
                     '-c:a', 'aac', '-b:a', '192k', '-shortest', str(final_path)],
                    capture_output=True, text=True)
if r.returncode != 0:
    raise RuntimeError(r.stderr)

print(f'DONE: {final_path}', flush=True)
