# 연속 갤러리 뷰어용 IIIF 자료를 만든다 — 전시 웹페이지에 이미 실린 이미지(같은 바이트)만 꺼내 쓴다
#   archive-tools-next/iiif/<편>/<nn>.jpg · thumb/<nn>.jpg · manifest.json (IIIF Presentation 3.0)
#   archive-tools-next/iiif/collection.json (전체 묶음)
#   examples/viewer-data.json (examples/viewer.html이 읽는 목록)
#   이미지 권리: 소장처 · 자료관 것 — 라이선스를 정하지 않고(rights 없음) requiredStatement로 출처 · 동의 · 내림을 적는다
import _paths as P
import re, json, os, csv, glob, base64, io
from PIL import Image

R = P.REPO + '/examples/'
OUT = os.path.join(P.NEXT, 'iiif')
BASE = P.NEXT_URL.replace('/media/', '/iiif/')
SITE = 'https://changgi.github.io/archive-tools/examples/'
CREDIT = 'Song Chang-gi (chgsong@naver.com, github.com/changgi)'
KIND = {'royal-letters': '박물관', 'gujora': '마을', 'hagari': '마을', 'yongmunsa': '사찰', 'deokcheon': '서원', 'byeongsan': '서원',
        'jikjisa-temple': '사찰', 'susanri-village': '마을', 'namgye-seowon': '서원', 'myeongseong-letters': '박물관'}
for jp in glob.glob(P.DATA + '/new*/*.json'):
    try: M = json.load(open(jp, encoding='utf-8'))['meta']; KIND.setdefault(M['folder'], M.get('kind', '문중'))
    except Exception: pass

def put(path, data):
    """바뀐 때만 쓴다(커밋 잡음 줄이기)"""
    if os.path.exists(path) and open(path, 'rb').read() == data: return 0
    os.makedirs(os.path.dirname(path), exist_ok=True); open(path, 'wb').write(data); return 1

def L(s): return {'ko': [s]}
def MV(k, v): return {'label': L(k), 'value': L(v)}

# 편마다 릴스 · 가로 영상(archive-tools-next/media) — 갤러리 목록(index.html의 IT)에서 주소 · 길이를 읽는다
_IT = json.loads(re.search(r'const IT\s*=\s*(\[.*?\]);\s*\n', open(R + 'index.html', encoding='utf-8').read(), re.S).group(1))
VID = {i['f']: i for i in _IT if i.get('f') and i.get('reel')}
def vids(f):
    """[(라벨, 주소, 가로, 세로, 길이(초), 포스터, 자막)] — 릴스(세로 1080×1920) · 가로 영상(1920×1080)"""
    i = VID.get(f)
    if not i: return []
    out = [('릴스 (세로 영상)', i['reel'], 1080, 1920, float(i.get('dr') or 0), i.get('rp'), i.get('vtt'))]
    if i.get('wide'): out.append(('가로 영상', i['wide'], 1920, 1080, float(i.get('dw') or i.get('dr') or 0), i.get('wp'), i.get('vtt')))
    return out
nvid = 0
eps, coll_items, nimg, nchg, nbytes = [], [], 0, 0, 0
for rec in sorted(glob.glob(R + '*/record.json')):
    f = rec.split('/')[-2]
    ex, sp = R + f + '/exhibit.html', R + f + '/selection.csv'
    if not (os.path.exists(ex) and os.path.exists(sp)): continue
    r = json.load(open(rec, encoding='utf-8'))
    rows = list(csv.DictReader(open(sp, encoding='utf-8-sig')))
    imgs = [base64.b64decode(m) for m in re.findall(r'<img[^>]*src="data:image/jpeg;base64,([^"]+)"', open(ex, encoding='utf-8').read())]
    assert len(imgs) == len(rows), (f, len(imgs), len(rows))
    m = re.search(r'EP\.(\d+)', r.get('episode') or '')
    ep = int(m.group(1)) if m else None
    ctx = r.get('context', {})
    murl = f'{BASE}{f}/manifest.json'
    canvases, docs = [], []
    for i, (b, row) in enumerate(zip(imgs, rows), 1):
        im = Image.open(io.BytesIO(b)); w, h = im.size
        th = im.convert('RGB'); th.thumbnail((360, 360)); tb = io.BytesIO(); th.save(tb, 'JPEG', quality=78, optimize=True)
        nchg += put(f'{OUT}/{f}/{i:02d}.jpg', b) + put(f'{OUT}/{f}/thumb/{i:02d}.jpg', tb.getvalue())
        nimg += 1; nbytes += len(b) + tb.tell()
        name, year = row.get('문서명', ''), row.get('연도', '')
        cid = f'{BASE}{f}/canvas/{i}'
        md = [MV('연도', year or '미상'), MV('문서 유형', row.get('문서유형', ''))]
        for k in ('판독', '번역', '요약'):
            if row.get(k): md.append(MV(k, row[k]))
        md.append(MV('검토', row.get('검토') or '미검토 (판독 · 번역은 초안)'))
        if row.get('자료ID'): md.append(MV('자료 ID', row['자료ID']))
        canvases.append({'id': cid, 'type': 'Canvas', 'label': L(f'{name} ({year})' if year else name), 'width': w, 'height': h,
            'metadata': md,
            'thumbnail': [{'id': f'{BASE}{f}/thumb/{i:02d}.jpg', 'type': 'Image', 'format': 'image/jpeg', 'width': th.width, 'height': th.height}],
            **({'homepage': [{'id': row['뷰어링크'], 'type': 'Text', 'label': L('한국고문서자료관 원본 뷰어'), 'format': 'text/html'}]} if row.get('뷰어링크', '').startswith('http') else {}),
            'items': [{'id': cid + '/page', 'type': 'AnnotationPage', 'items': [{'id': cid + '/page/image', 'type': 'Annotation', 'motivation': 'painting', 'target': cid,
                'body': {'id': f'{BASE}{f}/{i:02d}.jpg', 'type': 'Image', 'format': 'image/jpeg', 'width': w, 'height': h}}]}]})
        docs.append({'n': i, 't': name, 'y': year, 'ty': row.get('문서유형', ''), 'w': w, 'h': h, 'tw': th.width, 'th': th.height,
                     'src': row.get('원문', '') or row.get('판독', ''), 'tr': row.get('번역', ''), 'sm': row.get('요약', ''), 'v': row.get('뷰어링크', '')})
    for j, (vl, vu, vw, vh, vd, vp, vt) in enumerate(vids(f), 1):  # 영상 캔버스 — IIIF Presentation 3.0 Video(길이 duration)
        cid = f'{BASE}{f}/canvas/v{j}'
        cv = {'id': cid, 'type': 'Canvas', 'label': L(vl), 'width': vw, 'height': vh, 'duration': round(vd, 1) or 60,
              'items': [{'id': cid + '/page', 'type': 'AnnotationPage', 'items': [{'id': cid + '/page/video', 'type': 'Annotation', 'motivation': 'painting', 'target': cid,
                  'body': {'id': vu, 'type': 'Video', 'format': 'video/mp4', 'width': vw, 'height': vh, 'duration': round(vd, 1) or 60}}]}]}
        if vp: cv['thumbnail'] = [{'id': SITE + vp, 'type': 'Image', 'format': 'image/jpeg'}]
        if vt: cv['annotations'] = [{'id': cid + '/subtitles', 'type': 'AnnotationPage', 'items': [{'id': cid + '/subtitles/ko', 'type': 'Annotation', 'motivation': 'supplementing', 'target': cid,
                  'body': {'id': SITE + vt, 'type': 'Text', 'format': 'text/vtt', 'language': 'ko', 'label': L('한국어 자막')}}]}]
        canvases.append(cv); nvid += 1
    title = r.get('title', f)
    label = f'EP.{ep} {title}' if ep else title
    man = {'@context': 'http://iiif.io/api/presentation/3/context.json', 'id': murl, 'type': 'Manifest', 'label': L(label),
        'summary': L(ctx.get('purpose', '')),
        'metadata': [MV('시리즈', ctx.get('series', '「고문서 한 장」')), MV('편', f'EP.{ep}' if ep else '기획 예시'), MV('소장처', ctx.get('holder', '')),
                     MV('출처', ctx.get('source_archive', '한국학중앙연구원 한국고문서자료관')), MV('판독 · 번역 · 해제', '초안 — 원본과 대조한 사람만 검토를 표시합니다'), MV('만든 사람', CREDIT)],
        'requiredStatement': MV('출처 · 권리', (r.get('rights', {}).get('images') or '고문서 이미지: 한국학중앙연구원 한국고문서자료관 소장 · 제공. 다시 쓰려면 자료관을 통한 소장처 동의가 필요하며, 문제가 있으면 내립니다.') + f' 엮은이: {CREDIT}'),
        'provider': [{'id': 'https://github.com/changgi', 'type': 'Agent', 'label': L('Song Chang-gi · 「고문서 한 장」'), 'homepage': [{'id': SITE, 'type': 'Text', 'label': L('고문서 한 장'), 'format': 'text/html'}]}],
        'homepage': [{'id': f'{SITE}{f}/exhibit.html', 'type': 'Text', 'label': L('전시 웹페이지'), 'format': 'text/html'}],
        'seeAlso': [{'id': f'{SITE}{f}/record.json', 'type': 'Dataset', 'label': L('기록 꾸러미(record.json)'), 'format': 'application/json'}],
        'partOf': [{'id': BASE + 'collection.json', 'type': 'Collection'}],
        'thumbnail': canvases[0]['thumbnail'] if canvases else [],
        'items': canvases}
    nchg += put(f'{OUT}/{f}/manifest.json', json.dumps(man, ensure_ascii=False, indent=1).encode())
    coll_items.append((ep if ep is not None else 10**6, {'id': murl, 'type': 'Manifest', 'label': L(label), 'thumbnail': man['thumbnail']}))
    vi = VID.get(f)
    eps.append({'ep': ep, 'f': f, 't': title, 'c': ctx.get('holder') or ctx.get('collection', ''), 'k': KIND.get(f, '문중'), 'd': docs,
                **({'v': {k: vi[k] for k in ('reel', 'rp', 'wide', 'wp', 'vtt', 'dr', 'dw') if vi.get(k)}} if vi else {})})

coll_items.sort(key=lambda x: x[0])
coll = {'@context': 'http://iiif.io/api/presentation/3/context.json', 'id': BASE + 'collection.json', 'type': 'Collection',
        'label': L('고문서 한 장 — 전체 편'), 'summary': L(f'편 {len(eps)}개 · 문서 {nimg}건 · 영상 {nvid}개(릴스 · 가로). 이미지는 각 전시 웹페이지에 실린 것과 같습니다.'),
        'requiredStatement': MV('출처 · 권리', f'고문서 이미지: 한국학중앙연구원 한국고문서자료관 소장 · 제공(각 소장처 기탁). 다시 쓰려면 자료관을 통한 소장처 동의가 필요하며, 문제가 있으면 내립니다. 엮은이: {CREDIT}'),
        'items': [x[1] for x in coll_items]}
nchg += put(f'{OUT}/collection.json', json.dumps(coll, ensure_ascii=False, indent=1).encode())
eps.sort(key=lambda e: (e['ep'] is None, e['ep'] or 0, e['f']))  # EP.1–EP.200 차례로, 편 번호 없는 기획 예시 3편은 맨 뒤
data = json.dumps({'base': BASE, 'eps': eps}, ensure_ascii=False, separators=(',', ':')).encode()
nchg += put(R + 'viewer-data.json', data)
print(f'■ IIIF: 편 {len(eps)}개 · 문서 {nimg}건 · 영상 캔버스 {nvid}개 · 이미지 {nbytes/1e6:.0f}MB · 바뀐 파일 {nchg}개 · viewer-data {len(data)/1e6:.1f}MB → {BASE}collection.json')
