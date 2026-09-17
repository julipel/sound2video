import av,json,numpy as np
from pathlib import Path
root=Path(__file__).resolve().parent
video=next((root.parent/'outputs/project/input').glob('*.mp4'))
groups=json.loads((root/'ocr-timed.json').read_text(encoding='utf-8'))
for gid,t0,t1 in [(1,4.7,6.3),(204,768.0,769.7)]:
    g=groups[gid]
    n=(g['first']+g['last'])//2
    with av.open(str(root/'ocr-frames'/f'{n:06d}.png')) as c:
        template=next(c.decode(video=0)).reformat(width=640,height=110,format='gray').to_ndarray()[77:98,8:632]<100
    vals=[]
    with av.open(str(video)) as c:
        s=c.streams.video[0];c.seek(int(t0/s.time_base),stream=s)
        for f in c.decode(s):
            if f.time<t0:continue
            if f.time>t1:break
            a=f.to_ndarray(format='gray')[327:348,8:632]
            vals.append((round(f.time,3),round(float(a[template].mean()),1)))
    print(gid,vals)
