# 원문 대조 편집기 공유판(claude.ai 아티팩트) 만들기 → OUT/index.html · data.json(모든 편 글) · p/<번호>.json(편마다 사진 묶음)
#   python3 tools/series/compare_site.py      (OUT: SERIES_COMPARE_OUT, 기본 state/compare_site)
#   아티팩트 한 판의 파일은 512개까지라 사진은 편마다 한 묶음으로. 고친 내용은 아티팩트 db(edits · log)에 모이고,
#   pull_edits.py로 fix --from 용 JSON을 만든다. 사진은 소장처 동의 조건 — 공유 범위는 저장소 주인이 정함.
import _paths as P
import sys, os, re, csv, json, glob, base64, io
from PIL import Image
sys.path.insert(0, P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts')
import studio as ST
EX = P.REPO + '/examples'; OUT = os.environ.get('SERIES_COMPARE_OUT') or P.STATE + '/compare_site'
MAXPX, Q = int(os.environ.get('MAXPX', 1300)), int(os.environ.get('Q', 72))
os.makedirs(OUT, exist_ok=True)
idx = []; tot = 0; nimg = 0; ALL = {}
for sp in sorted(glob.glob(EX + '/*/selection.csv')):
    d = os.path.dirname(sp); key = os.path.basename(d)
    rows = list(csv.DictReader(open(sp, encoding='utf-8-sig')))
    title = json.load(open(d + '/theme.json', encoding='utf-8')).get('title', key) if os.path.exists(d + '/theme.json') else key
    ep = json.load(open(d + '/record.json', encoding='utf-8')).get('episode', '') if os.path.exists(d + '/record.json') else ''
    ex = open(d + '/exhibit.html', encoding='utf-8').read() if os.path.exists(d + '/exhibit.html') else ''
    imgs = [(re.search(r'src="data:image/[a-z]+;base64,([^"]+)"', seg) or [None, ''])[1] for seg in ex.split('<section class="panel">')[1:]]
    al = json.load(open(d + '/align.json', encoding='utf-8')) if os.path.exists(d + '/align.json') else {}
    docs = []; pack = {}
    for i, r in enumerate(rows):
        doc = ST.compare_doc(r, '', al); b = imgs[i] if i < len(imgs) else ''
        if b:
            im = Image.open(io.BytesIO(base64.b64decode(b))).convert('RGB'); im.thumbnail((MAXPX, MAXPX)); bio = io.BytesIO(); im.save(bio, 'JPEG', quality=Q, optimize=True, progressive=True)
            pack[str(r['순서'])] = 'data:image/jpeg;base64,' + base64.b64encode(bio.getvalue()).decode(); tot += len(bio.getvalue()); nimg += 1
        docs.append(doc)
    os.makedirs(OUT + '/p', exist_ok=True); json.dump(pack, open(f'{OUT}/p/{len(idx)}.json', 'w'), separators=(',', ':'))
    ALL[key] = {'key': key, 'title': title, 'pk': len(idx), 'docs': docs}
    idx.append({'key': key, 'title': title, 'ep': ep, 'n': len(docs)})
json.dump(ALL, open(OUT + '/data.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
num = lambda x: int(re.sub(r'\D', '', x['ep']) or 9999)
idx.sort(key=lambda x: (num(x), x['key']))
site = open(os.path.join(P.CODE, 'compare_site.js'), encoding='utf-8').read()
page = ST.compare_page('site', {'index': idx}, font=True).replace('<!--SITE-->', '<script>\n' + site + '\n</script>')
open(OUT + '/index.html', 'w', encoding='utf-8').write(page)
print('편', len(idx), '사진', nimg, f'{tot/1e6:.1f}MB', 'index', os.path.getsize(OUT + '/index.html'))
