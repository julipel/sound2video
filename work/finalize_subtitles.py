import json
from pathlib import Path
from datetime import timedelta
import srt
root=Path(__file__).resolve().parent
groups=json.loads((root/'ocr-timed.json').read_text(encoding='utf-8'))
# First caption fades in; use the first frame with visible glyph contrast,
# rather than the midpoint of its fade. Inspected at original frame cadence.
groups[0]['end']=4.963
groups[1]['start']=4.963
fixes={
4:'От 2 до 3 портов в зависимости модели',
5:'Модель E3 оснащена 3 портами',
13:'ID-пациента можно создать вручную или автоматически',
34:'μ-Scan\nПодавление зернистости и подчеркивание контуров структур',
46:'Есть 3 способа увеличения изображения',
59:'Также вы можете включить режим SR Flow',
63:'Нажмите SET и перемещайте трекбол для изменения размера рамки',
67:'Нажмите <PW> для включения режима импульсно-волнового допплера',
74:'Затем нажмите <UPDATE> для активации режима PW',
84:'кроме отображаемых внизу параметров режима PW',
85:'используйте кнопки <Baseline> и <Scale>',
96:'SonoHelp вызывается нажатием кнопки P2\nтакими как SonoHelp',
97:'SonoHelp вызывается нажатием кнопки P2\nКоторый даёт вам рекомендации по проведению обследования',
98:'SonoHelp - это учебник, показывающий расположение датчика,\nанатомические иллюстрации и стандартные примеры ультразвуковых изображений.',
100:'SonoHelp охватывает различные области применения,\nвключая печень, почки, сердце, молочные железы,\nщитовидную железу, акушерство, сосуды и т.д.',
118:'Нажмите клавишу <Calc>',
134:'По завершению обследования',
141:'или нажмите End Exam для сохранения на жестком диске сканера',
149:'такие "Название клиники", "Язык", "Время" и др.',
152:'вкладка "Сохранить" используется для изменения длительности сохраняемой кинопетли',
153:'А также для назначения функций настраиваемых клавиш P1 P2 F3 F4',
157:'На вкладке "Преднастройки обследования" (Exam Preset)',
169:'В меню "Измерения" расположены 3 вкладки',
198:'Не забудьте нажать клавишу Apply',
}
subs=[]
audit=[]
for g in groups:
    if not g['text']: continue
    text=fixes.get(g['group'],g['text']).replace('”','"').replace('“','"')
    text=text.replace('В-режим','B-режим')
    subs.append(srt.Subtitle(index=len(subs)+1,start=timedelta(seconds=g['start']),
               end=timedelta(seconds=g['end']),content=text))
    audit.append({'id':len(subs),'group':g['group'],'reference_frame':(g['first']+g['last'])//2,
                  'ocr_text':g['text'],'verified_text':text})
out=root.parent/'outputs/project/subs'
out.mkdir(exist_ok=True)
srt_path=out/'subtitles.srt'
srt_path.write_text(srt.compose(subs),encoding='utf-8')
parsed=[{'id':s.index,'start':s.start.total_seconds(),'end':s.end.total_seconds(),
         'duration':round((s.end-s.start).total_seconds(),3),'text':s.content}
        for s in srt.parse(srt_path.read_text(encoding='utf-8'))]
assert len(parsed)==len(subs)>0
assert all(0<=s['start']<s['end']<=786.507 for s in parsed)
assert all(a['end']<=b['start'] for a,b in zip(parsed,parsed[1:]))
(out/'subtitles.json').write_text(json.dumps(parsed,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'ocr-verification.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print('Saved and validated',len(parsed),'subtitles')
print('First:',parsed[0])
print('Last:',parsed[-1])
