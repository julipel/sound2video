import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / 'outputs' / 'project' / 'tools' / 'ffmpeg-9.0.1-essentials_build' / 'bin'
FFMPEG = str(BIN / 'ffmpeg.exe')

VIDEO = next((ROOT / 'outputs' / 'project' / 'input').glob('*.mp4'))
OUT = ROOT / 'outputs' / 'project' / 'output' / (VIDEO.stem + '_nocaptions.mp4')

W, H = 640, 360
FPS = Fraction(24000, 1001)
MASK_Y0, MASK_Y1 = 283, 360          # caption band, full width
CROP_Y0 = 200                         # crop a taller strip for inpaint context, cheaper than full frame
PAD = 0.08                            # seconds of margin around each caption interval

subs = json.loads((ROOT / 'outputs' / 'project' / 'subs' / 'subtitles.json').read_text(encoding='utf-8'))
intervals = [(s['start'] - PAD, s['end'] + PAD) for s in subs]
intervals.sort()

mask_strip = np.zeros((H - CROP_Y0, W), dtype=np.uint8)
mask_strip[MASK_Y0 - CROP_Y0:MASK_Y1 - CROP_Y0, :] = 255

def needs_inpaint(t: float) -> bool:
    for a, b in intervals:
        if a <= t <= b:
            return True
        if t < a:
            return False
    return False

reader = subprocess.Popen(
    [FFMPEG, '-v', 'error', '-i', str(VIDEO), '-f', 'rawvideo', '-pix_fmt', 'bgr24', 'pipe:1'],
    stdout=subprocess.PIPE, bufsize=10 ** 8)

writer = subprocess.Popen(
    [FFMPEG, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
     '-r', f'{FPS.numerator}/{FPS.denominator}', '-i', 'pipe:0',
     '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', str(OUT)],
    stdin=subprocess.PIPE, bufsize=10 ** 8)

frame_size = W * H * 3
i = 0
inpainted = 0
while True:
    buf = reader.stdout.read(frame_size)
    if len(buf) < frame_size:
        break
    t = i / float(FPS)
    frame = np.frombuffer(buf, dtype=np.uint8).reshape(H, W, 3).copy()
    if needs_inpaint(t):
        strip = frame[CROP_Y0:H, :, :]
        strip = cv2.inpaint(strip, mask_strip, 7, cv2.INPAINT_TELEA)
        frame[CROP_Y0:H, :, :] = strip
        inpainted += 1
    writer.stdin.write(frame.tobytes())
    i += 1
    if i % 1000 == 0:
        print(f'{i} frames processed ({inpainted} inpainted), t={t:.1f}s', flush=True)

writer.stdin.close()
reader.stdout.close()
reader.wait()
writer.wait()
print(f'DONE: {i} frames total, {inpainted} inpainted -> {OUT}', flush=True)
