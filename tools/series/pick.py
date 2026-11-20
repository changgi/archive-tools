# 작업 폴더의 edit/story 선별표를 정확히 고른 문서로 다시 만든다(순서대로)
#   python3 pick.py <work> "문서명 정규식1" "정규식2" ...   — 각 정규식에 처음 맞는 문서(이미지를 받은 것) 하나씩
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import csv, glob, json, os, re, shutil, sys
sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts'))
import studio as ST
from PIL import Image
W = sys.argv[1] if sys.argv[1].startswith('/') else (P.WORK + '/') + sys.argv[1]
meta = list(csv.DictReader(open(W + '/metadata.csv', encoding='utf-8-sig')))
docs = {d['id']: d for d in json.load(open(W + '/docs.json', encoding='utf-8'))}
ed = W + '/edit/story'; shutil.rmtree(ed, ignore_errors=True); os.makedirs(ed + '/images')
rows = []
for i, rx in enumerate(sys.argv[2:], 1):
    rx, _, page = rx.partition('@')  # 「정규식@003」: 그 면을 대표장으로
    m = next((r for r in meta if re.search(rx, r['문서명']) and glob.glob(os.path.join(W, 'out', '*', f"*_{r['문서명']}", '001.jpg').replace('[', '[[]'))), None)
    if not m: sys.exit(f'없음: {rx}')
    pages = sorted(glob.glob(os.path.join(W, 'out', '*', f"*_{m['문서명']}", '*.jpg').replace('[', '[[]')))
    src = next((q for q in pages if os.path.basename(q) == f'{page}.jpg'), pages[0]) if page else pages[0]
    im = Image.open(src).convert('RGB'); im.thumbnail((1600, 1600)); im.save(f'{ed}/images/{i:02d}.jpg', quality=90)
    ys = m.get('시작연도') or ''
    r = {'순서': i, '자료ID': m['자료ID'], '문서명': m['문서명'], '연도': ys, '문서유형': m['문서유형'], '인물': m.get('인명·기관', ''),
         '유형설명': ST.glossary(m['문서유형']), '대표장': os.path.basename(src), '이미지': f'images/{i:02d}.jpg', '원본경로': os.path.relpath(src, W),
         '캡션': '', '이야기': '', '판독': '', '원문': '', '번역': '', '해제': '', '요약': '', '검토': '', '뷰어링크': m.get('뷰어링크', ''), '공유이미지': '', '연도근거': m.get('연도근거', '')}
    rows.append(r); print(i, ys, m['문서명'], src.split('/out/')[1])
with open(ed + '/selection.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
coll = json.load(open(W + '/collection.json', encoding='utf-8'))['name']
json.dump({'id': 'story', 'title': coll, 'selected': len(rows)}, open(ed + '/theme.json', 'w', encoding='utf-8'), ensure_ascii=False)
