import json, re
from collections import Counter
from pathlib import Path
from difflib import SequenceMatcher
root=Path(__file__).resolve().parent
data=[json.loads(l) for l in (root/'ocr-frames.jsonl').read_text(encoding='utf-8').splitlines()]
seen=set()
for r in data:
    for line in r['lines']:
        if 90 < line['top'] < 158 and line['text'] not in seen:
            print('MIDDLE',r['frame'],line)
            seen.add(line['text'])
groups=[]
for r in data:
    text='\n'.join(x['text'] for x in r['lines'] if x['top']>=120).strip()
    frame=int(r['frame'])
    if groups and (groups[-1]['texts'][-1]==text or (text and groups[-1]['texts'][-1] and SequenceMatcher(None,groups[-1]['texts'][-1],text).ratio()>.90)):
        groups[-1]['last']=frame
        groups[-1]['texts'].append(text)
    else:
        groups.append({'first':frame,'last':frame,'texts':[text]})
for i,g in enumerate(groups):
    g['text']=Counter(g.pop('texts')).most_common(1)[0][0]
    g['group']=i
    print(i, (g['first']-1)*.5, (g['last'])*.5, repr(g['text']))
(root/'ocr-groups.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2),encoding='utf-8')
