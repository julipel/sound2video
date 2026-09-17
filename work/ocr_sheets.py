from pathlib import Path
import json
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parent
groups=json.loads((root/'ocr-groups.json').read_text(encoding='utf-8'))
active=[g for g in groups if g['text']]
for offset in range(0,len(active),20):
    chunk=active[offset:offset+20]
    sheet=Image.new('RGB',(1280,len(chunk)*140),'#e0e0e0')
    draw=ImageDraw.Draw(sheet)
    for row,g in enumerate(chunk):
        frame=(g['first']+g['last'])//2
        im=Image.open(root/'ocr-frames'/f'{frame:06d}.png').crop((0,115,1280,220))
        sheet.paste(im,(0,row*140+30))
        draw.text((10,row*140+6),f"GROUP {g['group']} | {(g['first']-1)/2:.1f}s",fill='black')
    sheet.save(root/f'ocr-sheet-{offset//20:02d}.png')
