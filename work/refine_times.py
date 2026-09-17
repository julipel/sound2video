import json
from pathlib import Path
import av
import numpy as np
root=Path(__file__).resolve().parent
groups=json.loads((root/'ocr-groups.json').read_text(encoding='utf-8'))
templates=[]
for g in groups:
    n=(g['first']+g['last'])//2
    with av.open(str(root/'ocr-frames'/f'{n:06d}.png')) as im:
        f=next(im.decode(video=0))
        a=f.reformat(width=640,height=110,format='gray').to_ndarray()
        templates.append(a[77:98,8:632]<150 if g['text'] else np.zeros((21,624),dtype=bool))
video=next((root.parent/'outputs/project/input').glob('*.mp4'))
boundaries=[(g['first']-1)*.5 for g in groups[1:]]
samples=[[] for _ in boundaries]
with av.open(str(video)) as c:
    st=c.streams.video[0]
    st.thread_type='AUTO'
    j=0
    for f in c.decode(st):
        t=float(f.time)
        while j<len(boundaries) and t>boundaries[j]+.7:
            j+=1
        if j>=len(boundaries): break
        if t<boundaries[j]-.8: continue
        a=f.to_ndarray(format='gray')[327:348,8:632]<150
        for k in range(j,min(j+3,len(boundaries))):
            if boundaries[k]-.8 <= t <= boundaries[k]+.7:
                old=np.mean(a!=templates[k]); new=np.mean(a!=templates[k+1])
                samples[k].append((t,float(old),float(new)))
starts=[0.0]
report=[]
for i,rows in enumerate(samples):
    if not rows: raise ValueError(f'No frames at boundary {i}')
    costs=[sum(r[1] for r in rows[:k])+sum(r[2] for r in rows[k:]) for k in range(len(rows))]
    k=int(np.argmin(costs))
    t=round(rows[k][0],3)
    starts.append(t)
    report.append({'group':i+1,'coarse':boundaries[i],'refined':t,'edge':k in (0,len(rows)-1)})
for i,g in enumerate(groups):
    g['start']=starts[i]
    g['end']=starts[i+1] if i+1<len(starts) else 786.506
    assert g['start']<g['end'], g
(root/'ocr-timed.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'timing-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Refined',len(report),'boundaries; edge cases:',[r for r in report if r['edge']])
