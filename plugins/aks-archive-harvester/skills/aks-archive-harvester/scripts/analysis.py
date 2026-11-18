#!/usr/bin/env python3
"""통합 분석 — 여러 편(테마)의 문서 · 노트 · 결과물을 모아 한 장에서 전체를 읽는 분석 페이지.

  python3 analysis.py --list series.tsv --out site/analysis.html [--title "시리즈 제목"]
  (옆에 analysis-data.json(집계) · analysis-episodes.csv(편별 표), 모아 보기 search.html · types.html · quotes.html · timeline.html · people.html · questions.html도 저장)

  (series.py 가 사이트를 만들 때 analysis.html 도 함께 만듭니다.)

보여 주는 것: 핵심 수치 · 자동 요약 · 세기 · 연도 분포 · 문서 유형 · 유형×세기 · 소장처 종류 · 지역 ·
            핵심 정서 · 판독 난도 · 원문 인용 모음 · 자주 나온 인물 · 남겨 둔 질문 · 편별 표 · 데이터의 한계.
모든 수치는 selection.csv(문서명에서 뽑은 연도·유형·인물 포함)와 curator.md · delivery.md에서 셉니다.
"""
import argparse, collections, csv, glob, html, json, os, re, sys

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(errors='replace')
    except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio as ST
from urllib.parse import quote

h = html.escape
HAN = re.compile(r'[㐀-䶿一-鿿豈-﫿]')
GOLD = '#c4964a'
STOP = {'않음', '없는', '않는', '속의', '속', '것', '사이', '위와', '아래', '마음', '두', '한'}

# 소장처 이름의 첫 지명 → 현재 시·도 (모르는 이름은 '기타')
REGION = {}
for prov, names in {
    '경북': '안동 경주 김천 상주 예천 고령 의성 구미 영덕 청도 성주 칠곡 봉화 영주 문경 영천 포항 군위 청송 영양 울진',
    '경남': '진주 밀양 거창 산청 고성 합천 함양 거제 김해 창원 통영 사천 하동 남해 의령 함안 창녕 양산',
    '전북': '고창 남원 진안 부안 익산 전주 정읍 김제 완주 무주 장수 임실 순창 군산',
    '전남': '구례 나주 영광 영암 순천 담양 곡성 보성 화순 장흥 강진 해남 무안 함평 장성 완도 진도 신안 여수 광양 목포',
    '충남': '서산 논산 예산 아산 공주 부여 보령 홍성 청양 당진 태안 금산 천안 서천',
    '충북': '제천 청주 충주 보은 옥천 영동 진천 괴산 음성 단양 증평',
    '경기': '안성 의정부 용인 군포 시흥 안산 김포 이천 양주 광주 여주 화성 평택 오산 수원 남양주 파주 포천 연천 가평 양평 고양 하남 강화',
    '강원': '강릉 원주 춘천 삼척 정선 평창 영월 횡성 홍천 양양 속초 인제 철원 화천',
    '제주': '제주 서귀포', '서울': '서울', '대전': '대전', '대구': '대구', '부산': '부산', '인천': '인천', '울산': '울산'}.items():
    for n in names.split(): REGION[n] = prov
INST = {'명성황후기념관': '경기', '국립고궁박물관': '서울', '국립청주박물관': '충북', '경기도박물관': '경기', '오죽헌': '강원'}


def region_of(coll):
    w = (coll or '').split()[0] if coll else ''
    if '·' in w:
        ps = {REGION.get(x) for x in w.split('·')}
        return '여러 지역' if len(ps) > 1 else (ps.pop() or '기타')
    for k, v in INST.items():
        if w.startswith(k): return v
    return REGION.get(w, '기타')


def lab(e):
    return e.get('label') or f"EP.{e['ep']:02d}"


def cent(y):
    return f'{(y - 1) // 100 + 1}세기'


def load_series(tsv):
    """series.tsv → 편 목록 (series.py 와 같은 규칙)"""
    rows = list(csv.DictReader(open(tsv, encoding='utf-8-sig'), delimiter='\t'))
    base = os.path.dirname(os.path.abspath(tsv)); eps = []
    for r in rows:
        work, theme = r['work'].strip(), r['theme'].strip()
        if not os.path.isdir(work) and os.path.isdir(os.path.join(base, work)): work = os.path.join(base, work)
        ed = os.path.join(work, 'edit', theme)
        if not os.path.exists(os.path.join(ed, 'selection.csv')): print(f'건너뜀: {ed}/selection.csv 없음'); continue
        th = json.load(open(os.path.join(ed, 'theme.json'), encoding='utf-8')) if os.path.exists(os.path.join(ed, 'theme.json')) else {}
        cj = os.path.join(work, 'collection.json')
        coll = json.load(open(cj, encoding='utf-8'))['name'] if os.path.exists(cj) else os.path.basename(os.path.abspath(work))
        ep = int(r['ep']) if r.get('ep') else len(eps) + 1
        md = os.path.join(work, 'mediate', theme)
        eps.append(episode(ep, th.get('title') or theme, coll, ed, kind=r.get('kind', ''), cards=len(glob.glob(os.path.join(md, 'cards', '*.*'))),
                           videos=glob.glob(os.path.join(md, 'video', '*_reel*.mp4')) + glob.glob(os.path.join(md, 'video', '*_wide*.mp4')),
                           link=f'eps/{ep:02d}-{theme}/index.html'))
    return eps


def episode(ep, title, coll, ed, kind='', cards=0, videos=(), dur=None, link=''):
    sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
    if dur is None:
        dur = 0
        for v in [x for x in videos if '_reel' in x][:1]:
            try:
                import subprocess
                dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', v]).decode())
            except Exception: pass
    return dict(ep=ep, title=title, coll=coll, kind=kind, sel=sel, cur=ST.read_curator(ed), dv=ST.read_delivery(ed), cards=cards, dur=dur or 0, link=link)


# ---------------------------------------------------------------- 그림 조각
def hbars(items, total=None, unit='건', top=None, link=None):
    items = items[:top] if top else items
    if not items: return '<p class="mute">자료 없음</p>'
    mx = max(v for _, v in items) or 1; total = total or sum(v for _, v in items)
    rows = []
    for k, v in items:
        pct = f' · {v / total * 100:.0f}%' if total else ''
        rows.append(f'<div class="hb" title="{h(str(k))}: {v}{unit}{pct}"><span class="hl">{h(str(k))}</span><span class="ht"><i style="width:{max(1.5, v / mx * 100):.1f}%"></i></span><span class="hv">{v}<small>{pct}</small></span></div>')
    return '<div class="hbs">' + ''.join(rows) + '</div>'


def table(head, rows, cls=''):
    return f'<div class="tw" tabindex="0" role="region" aria-label="표"><table class="{cls}"><thead><tr>' + ''.join(f'<th>{h(x)}</th>' for x in head) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table></div>'


def tv(items, head=('항목', '수')):
    return '<details class="tvw"><summary>표로 보기</summary>' + table(head, [(h(str(k)), v) for k, v in items]) + '</details>'


CSS = '''
.an{--gold:#c4964a;--dim:#b9ab90}
:focus-visible{outline:2px solid #c4964a;outline-offset:2px}
.an .tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin:14px 0}
.an .tile{background:#1f1a14;border:1px solid #3a3225;border-radius:14px;padding:12px 14px}.an .tile b{display:block;font:700 28px/1.2 'Noto Serif KR',serif;color:#f3ead8}.an .tile span{font-size:13px;color:var(--dim)}
.an .ins{background:#1f1a14;border:1px solid #4a3e2c;border-radius:16px;padding:14px 20px}.an .ins li{margin:6px 0;color:#e8dcc4}
.an .two{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}
.an .card{background:#1b1712;border:1px solid #3a3225;border-radius:16px;padding:16px 18px;min-width:0}.an .card h3{margin:0 0 4px;color:#f3ead8;font-size:17px}.an .card .q{margin:0 0 12px;font-size:13.5px;color:var(--dim)}
.an .hbs{display:flex;flex-direction:column;gap:6px}.an .hb{display:grid;grid-template-columns:minmax(70px,9em) 1fr 4.6em;gap:8px;align-items:center;font-size:13.5px;border-radius:6px;padding:1px 2px}
.an .hb:hover{background:#2a231a}.an .hl{color:#e8dcc4;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.an .ht{background:#2a231a;border-radius:4px;height:12px;overflow:hidden}.an .ht i{display:block;height:100%;background:var(--gold);border-radius:0 4px 4px 0}
.an .hv{text-align:right;color:#f3ead8;font-variant-numeric:tabular-nums}.an .hv small{color:var(--dim);font-size:11px}
.an .strip{position:relative;height:96px;border-bottom:1px solid #4a3e2c;margin:8px 0 26px}.an .strip i{position:absolute;bottom:0;width:8px;height:8px;margin-left:-4px;border-radius:50%;background:var(--gold);box-shadow:0 0 0 2px #1b1712}.an .strip i:hover{background:#f3ead8;transform:scale(1.5)}
.an .strip u{position:absolute;bottom:-22px;font-size:11.5px;color:var(--dim);text-decoration:none;transform:translateX(-50%)}.an .strip s{position:absolute;bottom:0;height:100%;border-left:1px dashed #3a3225}
.an .hm{border-collapse:separate;border-spacing:2px;font-size:12.5px;min-width:0;width:auto}.an .hm td,.an .hm th{border:0;padding:4px 6px;text-align:center;white-space:nowrap}.an .hm td{border-radius:4px;color:#16130f;font-weight:700;min-width:34px}.an .hm td.z{color:transparent}.an .hm th{color:var(--dim);font-weight:400}.an .hm th.r{text-align:right;color:#e8dcc4}
.an .chips{display:flex;flex-wrap:wrap;gap:6px}.an .chips span{background:#231d15;border:1px solid #4a3e2c;border-radius:20px;padding:3px 10px;font-size:13.5px;color:#e8dcc4}.an .chips span b{color:var(--gold);margin-left:4px}
.an .quotes{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}.an .quotes blockquote{margin:0;background:#1f1a14;border-left:3px solid var(--gold);border-radius:8px;padding:10px 14px;font-family:'Noto Serif KR',serif;color:#f3ead8;font-size:15.5px}.an .quotes blockquote small{display:block;font-family:'Noto Sans KR',sans-serif;color:var(--dim);font-size:12.5px;margin-top:6px}.an .quotes blockquote em{display:block;font-style:normal;color:var(--dim);font-size:13px}
.an .qs li{margin:5px 0;color:#e8dcc4}.an .qs li small{color:var(--dim)}
.an .mute{color:var(--dim);font-size:13.5px}.an details.tvw{margin-top:10px}.an details.tvw summary{cursor:pointer;color:var(--dim);font-size:13px}.an details.tvw table{min-width:0}
.an .toc{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.an .toc a{font-size:13px;border:1px solid #4a3e2c;border-radius:20px;padding:3px 10px;text-decoration:none;color:#d5cab4;background:#231d15}
.an table.ept td:nth-child(1){white-space:nowrap;color:var(--gold);font-weight:700}
@media (max-width:600px){.an .hb{grid-template-columns:6.5em 1fr 4em}}
.col .qq{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}.col .qq blockquote{margin:0;background:#1f1a14;border-left:3px solid var(--gold);border-radius:8px;padding:10px 14px;font-family:'Noto Serif KR',serif;color:#f3ead8;font-size:15.5px}
.col .qq blockquote em{display:block;font-style:normal;color:var(--dim);font-size:13px;margin-top:2px}.col .qq blockquote small{display:block;font-family:'Noto Sans KR',sans-serif;color:var(--dim);font-size:12.5px;margin-top:6px}.col .qq a{color:var(--gold)}
.col .tlv{border-left:2px solid #c4964a66;margin:6px 0 0 4px;padding-left:16px}.col .tlv h2{margin:18px 0 6px;color:var(--gold);font-size:18px}.col .tlv div{margin:0 0 8px;font-size:14.5px;color:#e8dcc4}.col .tlv b{color:#f3ead8;margin-right:6px;font-variant-numeric:tabular-nums}.col .tlv small{color:var(--dim)}.col .tlv a{color:var(--gold)}
.col details.rvf{border:1px solid #3a3225;border-radius:10px;padding:8px 12px;margin:6px 0;background:#1c1712}.col details.rvf summary{cursor:pointer;color:#f3ead8}.col details.rvf summary small{color:var(--gold);margin-left:6px}.col details.rvf ul{list-style:none;padding:0;margin:8px 0 2px}.col details.rvf li{margin:4px 0;font-size:14.5px;color:#e8dcc4}.col details.rvf li.done{color:var(--dim)}.col details.rvf a{color:var(--gold);font-size:13px}.col .tools button{font:inherit;background:#2a2219;color:#f3ead8;border:1px solid #4a3e2c;border-radius:8px;padding:6px 12px;cursor:pointer}.col .tools input[type=text]{font:inherit;background:#16130f;color:#efe6d4;border:1px solid #4a3e2c;border-radius:8px;padding:6px 10px}.col .jump{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.col .jump a{display:inline-block;min-width:2.2em;text-align:center;padding:4px 8px;border:1px solid #4a3e2c;border-radius:8px;color:var(--gold);text-decoration:none}.col .pp{border-left:2px solid #c4964a66;margin:0 0 12px 4px;padding-left:14px}.col .pp b{color:#f3ead8;font-size:16px}.col .pp b small{color:var(--gold);font-weight:400;font-size:12.5px;margin-left:6px}.col .pp ul{margin:4px 0 0;padding-left:18px}.col .pp li{font-size:14.5px;color:#e8dcc4;margin:2px 0}.col .pp li small{color:var(--dim)}.col .pp a.sq{font-size:12.5px;margin-left:8px}.col .pp li.mn{list-style:none;margin-left:-18px;margin-top:4px;color:#cfc3ab}.col .pp a{color:var(--gold)}.col .multi{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 16px}.col .multi a{background:#231d15;border:1px solid #4a3e2c;border-radius:16px;padding:4px 12px;color:#f3ead8;text-decoration:none;font-size:14px}.col .multi a small{color:var(--gold);margin-left:4px}
.col .qcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}.col .qcards div{background:#1f1a14;border:1px solid #4a3e2c;border-radius:14px;padding:14px 16px;break-inside:avoid}.col .qcards b{display:block;font-family:'Noto Serif KR',serif;font-size:17px;color:#f3ead8;line-height:1.55}.col .qcards span{display:block;margin-top:8px;color:var(--dim);font-size:12.8px}
.col .sr{padding-left:22px}.col .sr li{margin:0 0 12px;color:#e8dcc4}.col .sr li small{color:var(--dim)}.col .sr li p{margin:3px 0 0;font-size:14.5px;color:#d9cfbb}.col .sr mark{background:#c4964a;color:#16130f;border-radius:3px;padding:0 2px}.col .sr em{font-style:normal;color:var(--gold);font-size:12.5px;margin-right:4px}.col .sr a{color:var(--gold)}
.col .tcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}.col .tcard{background:#1f1a14;border:1px solid #3a3225;border-radius:14px;padding:12px 16px;break-inside:avoid}.col .tcard h2{margin:0 0 6px;color:#f3ead8;font-size:17px}.col .tcard h2 small{color:var(--gold);font-size:12.5px;font-weight:400;margin-left:6px}.col .tcard p{font-size:14px;margin:4px 0}.col .tcard ul{margin:6px 0 0;padding-left:18px;font-size:13.5px}.col .tcard a{color:var(--gold)}
.pbar{display:inline-block;width:90px;height:8px;background:#2a231a;border-radius:4px;overflow:hidden;vertical-align:middle}.pbar i{display:block;height:100%;background:var(--gold)}
.col .tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0 16px}.col input[type=search]{background:#1f1a14;border:1px solid #4a3e2c;color:#f3ead8;border-radius:20px;padding:6px 14px;min-width:260px;font:inherit}
.an input[type=search]{background:#1f1a14;border:1px solid #4a3e2c;color:#f3ead8;border-radius:20px;padding:6px 14px;min-width:260px;font:inherit}
@media print{body{background:#fff!important;color:#111!important}main{max-width:none!important;padding:0 8mm!important}nav,.toc,.tools,input,details.tvw summary,footer a{display:none!important}
 h1,h2,h3,p,li,td,th,span,b,em,small,blockquote,.hl,.hv{color:#111!important}a{color:#111!important;text-decoration:none}.card,.tile,.ins,.quotes blockquote,.qq blockquote,.qcards div,.box,.ep{background:#fff!important;border:1px solid #bbb!important;break-inside:avoid}
 .ht{background:#eee!important}.ht i{background:#8a6a33!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}.hm td{-webkit-print-color-adjust:exact;print-color-adjust:exact}.strip i{background:#8a6a33!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
 .qcards{grid-template-columns:1fr 1fr!important}.qcards div{border:1px dashed #888!important;min-height:38mm}}
'''


# 시·도 타일 지도(위치는 대략) — (열, 행)
TILES = {'경기': (1, 0), '강원': (2, 0), '인천': (0, 1), '서울': (1, 1), '충북': (2, 1), '경북': (3, 1), '충남': (0, 2), '세종': (1, 2), '대전': (2, 2), '대구': (3, 2), '울산': (4, 2),
         '전북': (1, 3), '경남': (3, 3), '부산': (4, 3), '광주': (0, 4), '전남': (1, 4), '제주': (1, 5)}


def tilemap(counts, unit='편'):
    """시·도 타일 지도 SVG — 진할수록 많음. 지도 밖(여러 지역 · 기타)은 아래 글로"""
    S, G = 70, 6; mx = max([counts.get(k, 0) for k in TILES] + [1])
    cells = []
    for name, (c, r) in TILES.items():
        n = counts.get(name, 0); x, y = c * (S + G), r * (S + G)
        fill = f'rgba(196,150,74,{0.15 + 0.85 * n / mx:.2f})' if n else '#231d15'
        ink = '#16130f' if n / mx > 0.45 else '#f3ead8'
        cells.append(f'<g><title>{name}: {n}{unit}</title><rect x="{x}" y="{y}" width="{S}" height="{S}" rx="8" fill="{fill}" stroke="#3a3225"/>'
                     f'<text x="{x + S / 2}" y="{y + 30}" text-anchor="middle" font-size="15" fill="{ink}">{name}</text>'
                     f'<text x="{x + S / 2}" y="{y + 52}" text-anchor="middle" font-size="17" font-weight="700" fill="{ink}">{n or "·"}</text></g>')
    W, H = 5 * (S + G), 6 * (S + G)
    label = ' · '.join(f'{k} {v}' for k, v in sorted(counts.items(), key=lambda x: -x[1]))
    other = ' · '.join(f'{k} {v}{unit}' for k, v in counts.items() if k not in TILES)
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="시·도별 {h(label)}" style="width:100%;max-width:{W}px;font-family:inherit"><title>시·도별 {h(label)}</title>{"".join(cells)}</svg>'
            + (f'<p class="mute">지도 밖: {h(other)}</p>' if other else ''))


def build(eps, title, kinds_label='소장처 종류'):
    """편 목록 → 분석 본문 HTML(<div class="an">…</div>)과 요약 dict"""
    docs = [(e, s) for e in eps for s in e['sel']]
    years = [(int(s['연도']), e, s) for e, s in docs if str(s.get('연도', '')).isdigit()]
    nodate = len(docs) - len(years)
    colls = {e['coll'] for e in eps}
    ys = [y for y, _, _ in years]
    han = sum(len(HAN.findall(s.get('판독') or '')) for _, s in docs)
    tr = sum(len(s.get('번역') or '') for _, s in docs)
    unk = sum((s.get('판독') or '').count('□') for _, s in docs); uns = sum((s.get('판독') or '').count('(?)') for _, s in docs)
    read_n = sum(1 for _, s in docs if (s.get('판독') or '').strip()); tr_n = sum(1 for _, s in docs if (s.get('번역') or '').strip())
    quotes = [(q[0], q[1], e) for e, s in docs for q in ST.find_quotes(s.get('이야기'))]
    dur = sum(e['dur'] for e in eps); cards = sum(e['cards'] for e in eps)
    C = collections.Counter(cent(y) for y in ys)
    centuries = sorted(C, key=lambda c: int(c[:-2]))
    T = collections.Counter((s.get('문서유형') or '기타').strip() or '기타' for _, s in docs)
    K = collections.Counter(e['kind'] for e in eps if e.get('kind'))
    R = collections.Counter(region_of(e['coll']) for e in eps)
    P = collections.Counter()
    for _, s in docs: P.update(persons_of(s))
    emos = [(e['dv'].get('emotion') or '').strip() for e in eps if (e['dv'].get('emotion') or '').strip()]
    EW = collections.Counter(re.sub(r'(?<=..)(의|에|을|를|이|가|은|는)$', '', w) for x in emos for w in re.split(r'\s*(?:와|과|에서|으로|로|,|·|→|그리고|\s)\s*', x) if len(w) >= 2 and w not in STOP)
    n_cur = sum(1 for e in eps if e['cur'].get('message')); n_dv = len(emos)

    # ---- 자동 요약(있는 수치만 문장으로)
    ins = []
    if C:
        c1, n1 = C.most_common(1)[0]; ins.append(f'연대가 적힌 문서 {len(ys)}건 가운데 <b>{c1}</b>가 {n1}건({n1 / len(ys) * 100:.0f}%)으로 가장 많습니다. 가장 이른 문서는 {min(ys)}년, 가장 늦은 문서는 {max(ys)}년 — {max(ys) - min(ys)}년에 걸칩니다.')
    if T:
        t3 = T.most_common(3); ins.append('문서 유형은 ' + ' · '.join(f'<b>{h(k)}</b> {v}건' for k, v in t3) + f' 순으로 많고, 모두 {len(T)}가지입니다.')
    if R and len(R) > 1:
        r1, rn = R.most_common(1)[0]; ins.append(f'소장처 {len(colls)}곳은 {len([k for k in R if k not in ("기타", "여러 지역")])}개 시·도에 걸쳐 있습니다. 가장 많은 곳은 <b>{h(r1)}</b>({rn}편)입니다.')
    if K and len(K) > 1:
        ins.append(f'{kinds_label}: ' + ' · '.join(f'{h(k)} {v}편' for k, v in K.most_common()) + '.')
    if read_n: ins.append(f'원문 판독 {read_n}건(한자 {han:,}자) · 번역 {tr_n}건(약 {tr:,}자). 못 읽은 글자 □ {unk}개, 불확실 (?) {uns}개를 그대로 표시했습니다.')
    if quotes: ins.append(f'이야기에 종이에 적힌 문장을 "현대어(原文)"로 인용한 곳이 {len(quotes)}곳 — 편마다 평균 {len(quotes) / max(1, len(eps)):.1f}곳입니다.')
    if EW: ins.append('전달 에디팅의 핵심 정서에 자주 나온 말: ' + ' · '.join(f'<b>{h(w)}</b>({n})' for w, n in EW.most_common(5)) + '.')
    if dur: ins.append(f'영상(릴스 기준) 총 {dur / 60:.0f}분, 편당 평균 {dur / max(1, sum(1 for e in eps if e["dur"])):.0f}초 · 카드 {cards:,}장.')

    tiles = [(len(eps), '편'), (len(docs), '문서'), (len(colls), '소장처'), (f'{min(ys)}–{max(ys)}' if ys else '—', '연대 범위'),
             (f'{han:,}', '판독한 한자'), (len(quotes), '원문 인용'), (f'{dur / 60:.0f}분' if dur else '—', '영상 길이'), (f'{cards:,}', '카드')]
    out = ['<div class="an">',
           '<nav class="toc">' + ''.join(f'<a href="#{i}">{t}</a>' for i, t in [('a-sum', '요약'), ('a-time', '시대'), ('a-type', '문서 유형'), ('a-where', '어디서'), ('a-feel', '정서'), ('a-read', '판독'), ('a-quote', '인용'), ('a-who', '인물'), ('a-q', '질문'), ('a-eps', '편별 표'), ('a-lim', '한계')]) + '</nav>',
           '<p class="mute">모아 보기: <a href="search.html">전체 검색</a> · <a href="types.html">문서 유형 사전</a> · <a href="quotes.html">종이에 적힌 문장 전체</a> · <a href="people.html">인물 찾아보기</a> · <a href="timeline.html">전체 연표</a> · <a href="questions.html">남겨 둔 질문 카드</a></p>',
           '<div class="tiles">' + ''.join(f'<div class="tile"><b>{v}</b><span>{h(l)}</span></div>' for v, l in tiles) + '</div>',
           '<h2 id="a-sum">한눈에 — 자동 요약</h2><ul class="ins">' + ''.join(f'<li>{x}</li>' for x in ins) + '</ul>']

    # ---- 시대
    strip = ''
    if ys:
        lo, hi = (min(ys) // 50) * 50, (max(ys) // 50 + 1) * 50; span = max(1, hi - lo)
        stack = collections.Counter(); dots = []
        for y, e, s in sorted(years, key=lambda x: x[0]):
            b = y // 5; stack[b] += 1
            dots.append(f'<i style="left:{(y - lo) / span * 100:.2f}%;bottom:{(stack[b] - 1) * 9}px" title="{y} · {lab(e)} {h(s.get("문서명") or "")}"></i>')
        ticks = ''.join(f'<s style="left:{(t - lo) / span * 100:.2f}%"></s><u style="left:{(t - lo) / span * 100:.2f}%">{t}</u>' for t in range(lo, hi + 1, 100 if span > 300 else 50))
        mxs = max(stack.values()); strip = f'<div class="strip" style="height:{max(60, mxs * 9 + 10)}px">{ticks}{"".join(dots)}</div>'
    out.append('<h2 id="a-time">언제의 기록인가</h2><div class="two">'
               f'<div class="card"><h3>세기별 문서 수</h3><p class="q">문서명·연호에서 읽은 연도 기준 · 연대 미상 {nodate}건 제외</p>{hbars([(c, C[c]) for c in centuries], len(ys))}{tv([(c, C[c]) for c in centuries], ("세기", "문서 수"))}</div>'
               f'<div class="card"><h3>연도별 분포</h3><p class="q">점 하나가 문서 한 건 — 점에 마우스를 올리면 문서명</p>{strip or "<p class=mute>연도가 적힌 문서가 없습니다</p>"}</div></div>')

    # ---- 유형 · 유형×세기
    tt = [k for k, _ in T.most_common(10)]
    hm = ''
    if centuries and tt:
        cell = collections.Counter((s.get('문서유형') or '기타', cent(int(s['연도']))) for _, s in docs if str(s.get('연도', '')).isdigit())
        mx = max(cell.values()) if cell else 1
        hm = '<div class="tw" style="border:0" tabindex="0" role="region" aria-label="유형 × 세기 표"><table class="hm"><tr><td></td>' + ''.join(f'<th>{c}</th>' for c in centuries) + '</tr>' + ''.join(
            f'<tr><th class="r">{h(t)}</th>' + ''.join(
                (f'<td style="background:rgba(196,150,74,{0.18 + 0.82 * cell[(t, c)] / mx:.2f});color:{"#16130f" if cell[(t, c)] / mx > 0.45 else "#f3ead8"}" title="{h(t)} · {c}: {cell[(t, c)]}건">{cell[(t, c)]}</td>' if cell[(t, c)] else f'<td class="z" style="background:#231d15" title="{h(t)} · {c}: 0건">0</td>') for c in centuries) + '</tr>' for t in tt) + '</table></div>'
    out.append('<h2 id="a-type">어떤 문서인가</h2><div class="two">'
               f'<div class="card"><h3>문서 유형 (상위 15)</h3><p class="q">전체 {len(T)}가지 · 막대에 마우스를 올리면 비율</p>{hbars(T.most_common(), len(docs), top=15)}{tv(T.most_common(), ("유형", "문서 수"))}</div>'
               f'<div class="card"><h3>유형 × 세기</h3><p class="q">많이 나온 유형 10가지가 어느 세기에 몰려 있는지 — 진할수록 많음</p>{hm or "<p class=mute>자료 없음</p>"}</div></div>')

    # ---- 어디서
    out.append('<h2 id="a-where">어디의 기록인가</h2><div class="two">' +
               (f'<div class="card"><h3>{h(kinds_label)}</h3><p class="q">편 수</p>{hbars(K.most_common(), unit="편")}</div>' if K else '') +
               f'<div class="card"><h3>지역 (현재 시·도)</h3><p class="q">소장처 이름의 첫 지명으로 나눈 편 수 · 모르는 이름은 「기타」</p>{hbars(R.most_common(), unit="편")}{tv(R.most_common(), ("시·도", "편 수"))}</div>'
               f'<div class="card"><h3>타일 지도</h3><p class="q">시·도 한 칸이 한 지역(위치는 대략) — 진할수록 편이 많음</p>{tilemap(dict(R))}</div></div>')

    # ---- 정서
    feel = ''
    if emos:
        feel = (f'<div class="card"><h3>핵심 정서에 자주 나온 말</h3><p class="q">전달 에디팅 「핵심 정서」 {n_dv}편에서</p>{hbars(EW.most_common(12), unit="번")}</div>'
                '<div class="card"><h3>편마다의 핵심 정서</h3><p class="q">같은 기록도 어떤 마음으로 전할지에 따라 달라집니다</p><div class="chips">' +
                ''.join(f'<span title="{lab(e)} {h(e["title"])}">{h(e["dv"]["emotion"])}</span>' for e in eps if (e['dv'].get('emotion') or '').strip()) + '</div></div>')
    out.append('<h2 id="a-feel">어떤 마음으로 전했나</h2><div class="two">' + (feel or '<p class="mute">delivery.md의 「핵심 정서」를 채우면 나옵니다.</p>') + '</div>')

    # ---- 판독 난도
    rd = sorted(((sum((s.get('판독') or '').count('□') for s in e['sel']), sum((s.get('판독') or '').count('(?)') for s in e['sel']), e) for e in eps), key=lambda x: -(x[0] + x[1]))
    rd = [x for x in rd if x[0] + x[1]][:10]
    hard_html = hbars([(lab(e) + ' ' + e['title'][:14], a + b) for a, b, e in rd], unit='자') if rd else '<p class=mute>□ · (?) 표시가 없습니다</p>'
    out.append('<h2 id="a-read">얼마나 읽었나</h2><div class="two">'
               f'<div class="card"><h3>읽기 진행</h3><p class="q">문서 {len(docs)}건 기준</p>{hbars([("원문 판독", read_n), ("번역", tr_n), ("해제", sum(1 for _, s in docs if (s.get("해제") or "").strip())), ("요약", sum(1 for _, s in docs if (s.get("요약") or "").strip())), ("원문 인용 이야기", sum(1 for _, s in docs if ST.find_quotes(s.get("이야기")))), ("검토 표시", sum(1 for _, s in docs if s.get("검토")))], len(docs))}</div>'
               f'<div class="card"><h3>읽기 어려웠던 편</h3><p class="q">못 읽은 글자 □ + 불확실 (?) 이 많은 순</p>{hard_html}</div></div>')

    # ---- 인용
    seen, pick = set(), []
    for q, src, e in quotes:
        if e['ep'] in seen: continue
        seen.add(e['ep']); pick.append((q, src, e))
    step = max(1, len(pick) // 12); pick = pick[::step][:12]
    out.append(f'<h2 id="a-quote">종이에 적힌 문장들</h2><p class="mute">이야기에 인용한 원문 {len(quotes)}곳 가운데 편마다 하나씩, 고르게 12개</p><div class="quotes">' +
               ''.join(f'<blockquote>"{h(q)}"<em>{h(src)}</em><small>{lab(e)} · {h(e["title"])}</small></blockquote>' for q, src, e in pick) + '</div>')

    # ---- 인물
    out.append('<h2 id="a-who">자주 나온 이름</h2><div class="two">' +
               f'<div class="card"><h3>인물 (상위 15)</h3><p class="q">문서명에서 뽑은 이름 · 같은 이름이 다른 사람일 수 있습니다</p>{hbars(P.most_common(15), unit="건") if P else "<p class=mute>자료 없음</p>"}<p class="q"><a href="people.html">{len(P)}명 모두 · 가나다순 인물 찾아보기 →</a></p></div>'
               f'<div class="card"><h3>노트 진행</h3><p class="q">편 {len(eps)}개 기준</p>{hbars([("큐레이터 노트", n_cur), ("전달 에디팅 정서", n_dv), ("남겨 둔 질문", sum(1 for e in eps if e["cur"].get("question")))], len(eps), unit="편")}</div></div>')

    # ---- 질문
    qs = [(e['cur']['question'], e) for e in eps if e['cur'].get('question')]
    step = max(1, len(qs) // 14)
    out.append('<h2 id="a-q">남겨 둔 질문</h2><p class="mute">문서만으로는 답할 수 없어 보는 사람과 나누려는 질문 — 수업 · 토론 · 창작의 출발점</p><ul class="qs">' +
               ''.join(f'<li>{h(q)} <small>— {lab(e)} {h(e["title"])}</small></li>' for q, e in qs[::step][:14]) + '</ul>')

    # ---- 편별 표
    rows = []
    for e in sorted(eps, key=lambda x: (x['ep'] or 0)):
        yy = sorted(int(s['연도']) for s in e['sel'] if str(s.get('연도', '')).isdigit())
        sp = (f'{yy[0]}–{yy[-1]}' if yy[0] != yy[-1] else str(yy[0])) if yy else '미상'
        t = f'<a href="{h(e["link"])}">{h(e["title"])}</a>' if e.get('link') else h(e['title'])
        rows.append((f'{lab(e)}', t, h(e['coll']), h(e.get('kind') or ''), sp, len(e['sel']), h(e['dv'].get('emotion') or ''), h(e['cur'].get('message') or '')))
    out.append(f'<h2 id="a-eps">편별 한 줄 — {len(eps)}편</h2><p><input id="aq" type="search" placeholder="찾기: 제목 · 소장처 · 정서 · 문장 (예: 편지, 안동, 그리움)" aria-label="편별 표에서 찾기"> <span id="an" class="mute"></span></p>'
               + table(['편', '제목', '소장처', '종류', '연대', '문서', '핵심 정서', '전하고 싶은 것'], rows, 'ept')
               + '<script>(function(){var q=document.getElementById("aq"),n=document.getElementById("an"),rs=[].slice.call(document.querySelectorAll("table.ept tbody tr"));'
               + 'q.addEventListener("input",function(){var v=q.value.trim().toLowerCase(),k=0;rs.forEach(function(r){var on=!v||r.textContent.toLowerCase().indexOf(v)>=0;r.style.display=on?"":"none";if(on)k++});n.textContent=v?k+"편":""})})()</script>'
               + '<p class="mute">데이터 내려받기: <a href="analysis-data.json" download>집계 JSON</a> · <a href="analysis-episodes.csv" download>편별 표 CSV</a> · <a href="data.zip" download>전체 데이터 묶음 ZIP</a>(편별 판독 · 번역 · 노트, 이미지 없음) — 수업 · 연구 · 다른 도구로 다시 그리기</p>')

    # ---- 날짜 맞춤(studio.date_issues): 연호 · 왕대 · 간지 · 서기가 서로 맞는지
    dm = sum(len(ST.date_mentions(s.get(k) or '')) for _, s in docs for k in ('원문', '판독', '번역', '해제', '요약', '캡션', '이야기'))
    dbad = [f'{lab(e)} {s.get("순서")}번' for e, s in docs if ST.date_issues(s)]
    # ---- 한계
    out.append('<h2 id="a-lim">이 분석을 읽을 때</h2><ul class="ins">'
               '<li>이 수치는 <b>이 시리즈가 고른 문서</b>의 분포입니다. 소장처 전체나 조선 시대 전체의 경향이 아닙니다(고른 기준: 사람의 목소리가 들리는 한 줄 · 다양성).</li>'
               '<li>연도 · 문서 유형 · 인물은 문서명과 연호에서 자동으로 뽑은 초안입니다. 같은 이름이 다른 사람일 수 있습니다.</li>'
               '<li>지역은 소장처 이름의 첫 지명을 지금의 시 · 도로 옮긴 것입니다. 문서가 만들어진 곳과 다를 수 있습니다.</li>'
               '<li>판독 · 번역은 이미지에 근거한 초안입니다. □ · (?)는 그대로 남겼습니다.</li>'
               f'<li>날짜 자동 확인: 판독 · 번역 · 해제 속 날짜 표현 {dm}곳(연호 · 왕대 · 간지 · 서기)을 서로 맞춰 보았습니다 — '
               + (f'어긋난 곳 {len(dbad)}건({h(", ".join(dbad[:3]))}{" …" if len(dbad) > 3 else ""}). 원문 자체가 어긋나 해제에 적어 둔 경우도 있으니 원본으로 확인하세요.' if dbad else '모두 맞습니다.')
               + '</li></ul></div>')
    plain = [re.sub(r'<[^>]+>', '', x) for x in ins]
    data = dict(centuries=[[c, C[c]] for c in centuries], undated=nodate, types=T.most_common(), kinds=K.most_common(), regions=R.most_common(),
                emotion_words=EW.most_common(), persons=P.most_common(50), reading=dict(read=read_n, translated=tr_n, hanja=han, translation_chars=tr, unknown=unk, unsure=uns, date_mentions=dm, date_issues=dbad),
                quotes=[dict(quote=q, source=src, episode=lab(e), title=e['title']) for q, src, e in quotes],
                episodes=[dict(episode=lab(e), title=e['title'], collection=e['coll'], kind=e.get('kind') or '', region=region_of(e['coll']), docs=len(e['sel']),
                               years=sorted(int(x['연도']) for x in e['sel'] if str(x.get('연도', '')).isdigit()), emotion=e['dv'].get('emotion') or '',
                               message=e['cur'].get('message') or '', question=e['cur'].get('question') or '') for e in sorted(eps, key=lambda x: (x['ep'] or 0))])
    summary = dict(eps=len(eps), docs=len(docs), colls=len(colls), span=(min(ys), max(ys)) if ys else None, han=han, quotes=len(quotes), insights=ins, summary_text=plain, data=data)
    return '\n'.join(out), summary


def save_data(folder, summary):
    """analysis-data.json(집계) · analysis-episodes.csv(편별 표)를 분석 페이지 옆에 저장"""
    d = summary['data']
    out = {k: v for k, v in summary.items() if k not in ('data', 'insights')}; out.update(d)
    json.dump(out, open(os.path.join(folder, 'analysis-data.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(folder, 'analysis-episodes.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['편', '제목', '소장처', '종류', '지역', '문서 수', '처음 연도', '끝 연도', '핵심 정서', '전하고 싶은 것', '남겨 둔 질문'])
        for e in d['episodes']:
            ys = e['years']; w.writerow([e['episode'], e['title'], e['collection'], e['kind'], e['region'], e['docs'], ys[0] if ys else '', ys[-1] if ys else '', e['emotion'], e['message'], e['question']])


SEARCH_JS = ('<script>(function(){var q=document.getElementById("cq"),n=document.getElementById("cn"),it=[].slice.call(document.querySelectorAll("[data-s]"));'
             'q.addEventListener("input",function(){var v=q.value.trim().toLowerCase(),k=0;it.forEach(function(e){var on=!v||e.getAttribute("data-s").indexOf(v)>=0;e.style.display=on?"":"none";if(on)k++});n.textContent=v?k+"개":""})})()</script>')


def dname(s):
    n, y = (s.get('문서명') or '').strip(), str(s.get('연도') or '').strip()
    return n if (not y or n.startswith(y)) else f'{y} {n}'


NOT_PERSON = re.compile(r'(?:현감|현령|부윤|부사|군수|목사|찰방|유사|동민|거민|동중|회원|생록|수료|감영|관찰사|향교|서원|사찰|문중|종가|관아|댁노|어사|판관|씨)$')
ROLES = {'정부인', '숙부인', '정경부인', '부인', '공인', '유인', '수령', '좌수', '별감', '생원', '진사', '유학', '유생', '학생', '선생', '대감', '영감', '상전',
         '노비', '사내종', '계집종', '아들', '딸', '아내', '남편', '사돈', '조부', '장자', '국왕', '장령', '혼서', '문통', '호노', '초동', '계조모', '경민장'}
OFFICES = {'예조', '이조', '호조', '병조', '형조', '공조', '의정부', '사헌부', '사간원', '한성부', '비변사', '선혜청', '승정원', '홍문관', '경상도', '전라도', '충청도',
           '경기도', '강원도', '황해도', '평안도', '함경도', '제주도'}


CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'


def persons_of(s):
    """문서 한 건의 「인물」 칸 → 사람 이름 목록(직함 · 관청 · 고을 · 성씨만 있는 것은 뺌 — 성 없는 노비 · 승려 이름은 남김)"""
    out = []
    for p in re.split(r'[;,·/]\s*', s.get('인물') or ''):
        p = re.sub(r'\(.*?\)', '', p).strip()
        if not 1 < len(p) < 12 or p in ROLES or p in OFFICES or NOT_PERSON.search(p): continue  # 직함 · 관청 · 무리 · 「이씨」 · 「청송심씨」
        if p[-1] in '군부현도목읍' and p[:-1] in REGION: continue  # 거제군 · 함양군처럼 고을 이름(광해군 · 이만부는 사람)
        hz = re.search(re.escape(p) + r'\(([^)]*)\)', s.get('문서명') or '')
        if hz and hz.group(1)[-1:] in '寺山庵院堂樓亭': continue  # 직지사(直指寺) · 황악산(黃岳山)처럼 절 · 산 · 건물 이름
        out.append(p)
    return list(dict.fromkeys(out))


def initial(name):
    """가나다 찾기용 첫소리(ㄲ → ㄱ …). 한글이 아니면 「기타」"""
    c = name[:1]
    if '가' <= c <= '힣':
        k = CHO[(ord(c) - 0xAC00) // 588]
        return {'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ'}.get(k, k)
    return '기타'


def review_form(eps):
    """검토 기록하기 — 원본과 대조를 마친 문서에 표시하고 reviews.csv로 내려받기(이 페이지는 아무 데도 보내지 않음)"""
    out = []
    for e in sorted(eps, key=lambda x: (x['ep'] or 0)):
        left = [x for x in e['sel'] if not (x.get('검토') or '').strip()]
        items = ''.join(
            (f'<li><label><input type="checkbox" class="rvk" data-id="{h(x.get("자료ID") or "")}" data-ep="{h(lab(e))}" data-n="{h(x.get("순서") or "")}" data-t="{h(x.get("문서명") or "")}"> '
             f'{h(x.get("순서") or "")}. {h(dname(x))}</label>' if not (x.get('검토') or '').strip() else f'<li class="done">✓ {h(x.get("순서") or "")}. {h(dname(x))} <small>{h(x["검토"])}</small>')
            + (f' <a href="{h(x["뷰어링크"])}" target="_blank" rel="noopener">원본 ↗</a>' if x.get('뷰어링크') else '') + '</li>' for x in e['sel'])
        pf = f'<p class="mute"><a href="{h(e["proof"])}">이 편의 검토지(인쇄용) →</a></p>' if e.get('proof') else ''
        out.append(f'<details class="rvf" data-s="{h((lab(e) + e["title"] + e["coll"]).lower())}"><summary>{h(lab(e))} {h(e["title"])} <small>남은 {len(left)}건</small></summary>{pf}<ul>{items}</ul></details>')
    return ('<h2 id="record">검토 기록하기</h2><p class="mute">원본 사진과 판독 · 번역을 <b>직접 대조한 문서에만</b> 표시하세요(자동 확인 · 읽어 본 느낌은 검토가 아닙니다). 표시는 이 브라우저에만 남고 어디에도 보내지지 않습니다. '
            '다 고르면 <b>reviews.csv</b>를 내려받아 저장소에서 <code>python3 studio.py review --from reviews.csv --in 폴더</code>로 반영합니다(자료ID로 맞춰 검토 칸에 「이름 날짜」).</p>'
            '<div class="tools"><input id="rvby" type="text" placeholder="검토한 사람 이름" aria-label="검토한 사람 이름"> <button type="button" id="rvdl">reviews.csv 내려받기</button> '
            '<button type="button" id="rvclr">표시 지우기</button> <span id="rvn" class="mute"></span></div>' + ''.join(out))


REVIEW_JS = ('<script>(function(){var K="aks-review:"+location.pathname,ks=[].slice.call(document.querySelectorAll(".rvk")),by=document.getElementById("rvby"),n=document.getElementById("rvn"),st={};'
             'try{st=JSON.parse(localStorage.getItem(K)||"{}")}catch(e){}'
             'function save(){try{localStorage.setItem(K,JSON.stringify(st))}catch(e){}var c=ks.filter(function(k){return k.checked}).length;n.textContent=c?c+"건 표시함":""}'
             'ks.forEach(function(k){var id=k.dataset.id+"|"+k.dataset.ep+"|"+k.dataset.n;if(st.d&&st.d[id]){k.checked=true}k.addEventListener("change",function(){st.d=st.d||{};if(k.checked)st.d[id]=new Date().toISOString().slice(0,10);else delete st.d[id];save()})});'
             'if(st.by)by.value=st.by;by.addEventListener("input",function(){st.by=by.value;save()});save();'
             'function q(v){v=String(v==null?"":v);return /[",\\n]/.test(v)?"\\""+v.replace(/"/g,"\\"\\"")+"\\"":v}'
             'document.getElementById("rvdl").addEventListener("click",function(){var who=by.value.trim();if(!who){by.focus();n.textContent="검토한 사람 이름을 적어 주세요";return}'
             'var rows=[["자료ID","편","순서","문서명","검토자","날짜"]];ks.forEach(function(k){if(k.checked){var id=k.dataset.id+"|"+k.dataset.ep+"|"+k.dataset.n;rows.push([k.dataset.id,k.dataset.ep,k.dataset.n,k.dataset.t,who,(st.d&&st.d[id])||new Date().toISOString().slice(0,10)])}});'
             'if(rows.length<2){n.textContent="표시한 문서가 없습니다";return}'
             'var b=new Blob(["\\ufeff"+rows.map(function(r){return r.map(q).join(",")}).join("\\r\\n")+"\\r\\n"],{type:"text/csv"}),a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="reviews.csv";document.body.appendChild(a);a.click();a.remove()});'
             'document.getElementById("rvclr").addEventListener("click",function(){if(!confirm("이 브라우저에 남긴 검토 표시를 모두 지울까요?"))return;st={by:by.value};ks.forEach(function(k){k.checked=false});save()})})()</script>')


def collections_pages(eps, title):
    """모아 보기 3종 — (파일, 제목, 머리말, 본문). 인용 · 연표 · 질문"""
    docs = [(e, s) for e in sorted(eps, key=lambda x: (x['ep'] or 0)) for s in e['sel']]
    link = lambda e: f'<a href="{h(e["link"])}">{h(lab(e))} {h(e["title"])}</a>' if e.get('link') else f'{h(lab(e))} {h(e["title"])}'
    # 1) 인용
    qs = [(q, s, e) for e, s in docs for q in ST.find_quotes(s.get('이야기'))]
    qb = ''.join(f'<blockquote data-s="{h((q[0] + q[1] + e["title"] + e["coll"] + (s.get("문서명") or "")).lower())}">"{h(q[0])}"<em>{h(q[1])}</em><small>{h(dname(s))} · {link(e)}</small></blockquote>' for q, s, e in qs)
    quotes = (f'<div class="col"><div class="tools"><input id="cq" type="search" placeholder="찾기: 낱말 · 한자 · 편 제목 · 소장처" aria-label="문장 찾기"><span id="cn" class="mute"></span></div><div class="qq">{qb}</div></div>' + SEARCH_JS)
    # 2) 연표
    dated = sorted(((int(s['연도']), e, s) for e, s in docs if str(s.get('연도', '')).isdigit()), key=lambda x: (x[0], x[1]['ep'] or 0))
    rows, cur = [], None
    for y, e, s in dated:
        c = cent(y)
        if c != cur: rows.append(f'<h2>{c}</h2>'); cur = c
        v = f' · <a href="{h(s["뷰어링크"])}" target="_blank" rel="noopener">원본 ↗</a>' if s.get('뷰어링크') else ''
        rows.append(f'<div data-s="{h((str(y) + (s.get("문서명") or "") + (s.get("문서유형") or "") + e["title"] + e["coll"]).lower())}"><b>{y}</b>{h(s.get("문서명") or "")} <small>· {h(s.get("문서유형") or "")} · {link(e)}{v}</small></div>')
    nod = sum(1 for _, s in docs if not str(s.get('연도', '')).isdigit())
    timeline = (f'<div class="col"><div class="tools"><input id="cq" type="search" placeholder="찾기: 연도 · 문서 유형 · 이름 · 소장처" aria-label="연표 찾기"><span id="cn" class="mute"></span></div>'
                f'<p class="mute">연대가 적힌 문서 {len(dated)}건(연대 미상 {nod}건 제외) · 연도는 문서명·연호에서 읽은 값</p><div class="tlv">{"".join(rows)}</div></div>' + SEARCH_JS)
    # 2b) 인물 찾아보기 — 「인물」 칸의 이름마다 나온 문서 · 편
    PP = collections.defaultdict(list)
    for e, s in docs:
        for p in persons_of(s): PP[p].append((e, s))
    # 다른 문서의 번역 · 해제 · 요약에 이름이 나오는 곳(세 글자 이상 — 두 글자는 우연히 겹치기 쉬움)
    MM = {p: [(e, s) for e, s in docs if all(s is not y for _, y in v) and any(p in (s.get(k) or '') for k in ('번역', '해제', '요약'))] for p, v in PP.items() if len(p) >= 3}
    eps_of = lambda p: {x["title"] for x, _ in PP[p] + MM.get(p, [])}
    multi = sorted(((p, len(eps_of(p))) for p in PP if len(eps_of(p)) > 1), key=lambda x: (-x[1], x[0]))
    groups = collections.defaultdict(list)
    for p in sorted(PP): groups[initial(p)].append(p)
    order = [k for k in 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ' if k in groups] + (['기타'] if '기타' in groups else [])
    pid = {p: f'p{i}' for i, p in enumerate(sorted(PP))}
    def pblock(p):
        v = sorted(PP[p], key=lambda x: (int(x[1]['연도']) if str(x[1].get('연도', '')).isdigit() else 9999, x[0]['ep'] or 0))
        li = ''.join(f'<li>{h(dname(s))} <small>· {h(s.get("문서유형") or "")} · {link(e)}' + (f' · <a href="{h(s["뷰어링크"])}" target="_blank" rel="noopener">원본 ↗</a>' if s.get('뷰어링크') else '') + '</small></li>' for e, s in v)
        mm = MM.get(p, [])
        li += (f'<li class="mn"><small>다른 문서에서 언급 {len(mm)}건:</small> ' + ' · '.join(f'{h(dname(s))} <small>({link(e)})</small>' for e, s in mm[:8]) + (' …' if len(mm) > 8 else '') + '</li>') if mm else ''
        eps_n = len(eps_of(p))
        return (f'<div class="pp" id="{pid[p]}" data-s="{h((p + " " + " ".join((s.get("문서명") or "") + e["title"] + e["coll"] for e, s in v + mm)).lower())}">'
                f'<b>{h(p)}<small>문서 {len(v)}건' + (f' · 언급 {len(mm)}건' if mm else '') + (f' · {eps_n}편' if eps_n > 1 else '') + f'</small></b> <a class="sq" href="search.html?q={quote(p)}">전문에서 찾기</a><ul>{li}</ul></div>')
    people = (f'<div class="col"><div class="tiles"><div class="tile"><b>{len(PP)}</b><span>인물</span></div><div class="tile"><b>{len(multi)}</b><span>여러 편에 나오는 인물</span></div>'
              f'<div class="tile"><b>{sum(len(v) for v in PP.values())}</b><span>인물이 적힌 문서(겹침 포함)</span></div></div>'
              + (('<h2>여러 편에 걸쳐 나오는 사람</h2><p class="mute">다른 소장처 · 다른 이야기의 문서명이나 번역 · 해제에 같은 이름이 나옵니다 — 같은 사람인지는 문서로 확인하세요.</p><div class="multi">'
                  + ''.join(f'<a href="#{pid[p]}">{h(p)}<small>{n}편</small></a>' for p, n in multi) + '</div>') if multi else '')
              + '<div class="tools"><input id="cq" type="search" placeholder="찾기: 이름 · 문서명 · 소장처" aria-label="인물 찾기"><span id="cn" class="mute"></span></div>'
              + '<nav class="jump" aria-label="가나다 바로가기">' + ''.join(f'<a href="#i-{k}">{k}</a>' for k in order) + '</nav>'
              + ''.join(f'<h2 id="i-{k}">{k}</h2>' + ''.join(pblock(p) for p in groups[k]) for k in order)
              + '<p class="mute">이름은 문서명에서 뽑은 초안입니다(「인물」 칸). 「언급」은 세 글자 이상 이름이 다른 문서의 번역 · 해제 · 요약에 그대로 나온 곳입니다. 동명이인이 섞일 수 있고, 직함 · 관청 · 고을 · 절 · 성씨만 있는 이름은 뺐습니다.</p></div>' + SEARCH_JS)
    # 3) 질문
    qq = [(e['cur']['question'], e) for e in sorted(eps, key=lambda x: (x['ep'] or 0)) if e['cur'].get('question')]
    questions = ('<div class="col"><p class="mute">인쇄하면 한 장에 두 줄씩 질문 카드가 됩니다 — 잘라서 모둠 토론 · 글쓰기 · 전시 참여 벽에.</p><div class="qcards">'
                 + ''.join(f'<div><b>{h(q)}</b><span>{h(lab(e))} {h(e["title"])} · {h(e["coll"])}</span></div>' for q, e in qq) + '</div></div>')
    # 4) 전체 검색 — 판독 · 원문 · 번역 · 해제 · 요약 · 이야기 전문
    F = [('판독', '판독'), ('원문', '원문'), ('번역', '번역'), ('해제', '해제'), ('요약', '요약'), ('이야기', '이야기')]
    idx = [{'n': dname(s), 't': s.get('문서유형') or '', 'y': s.get('연도') or '', 'e': lab(e) + ' ' + e['title'], 'c': e['coll'], 'l': e.get('link') or '', 'v': s.get('뷰어링크') or '',
            **{k: (s.get(k) or '').strip() for k, _ in F if (s.get(k) or '').strip()}} for e, s in docs]
    data = json.dumps(idx, ensure_ascii=False).replace('</', '<\\/')
    search = ('<div class="col"><div class="tools"><input id="sq" type="search" placeholder="낱말 · 한자 · 이름 (예: 乘馹, 역마, 노비, 편지)" aria-label="전체 검색" autofocus>'
              '<span id="sn" class="mute"></span></div><p class="mute" id="sf">찾을 곳: ' + ''.join(f'<label style="margin-right:10px"><input type="checkbox" value="{k}" checked> {l}</label>' for k, l in F) + '</p>'
              f'<p class="mute">문서 {len(idx)}건의 판독 · 번역 · 해제 · 요약 · 이야기 전문에서 찾습니다. 판독은 이미지에 근거한 초안입니다.</p><ol id="sr" class="sr"></ol></div>'
              '<script type="application/json" id="sd">' + data + '</script>'
              '<script>(function(){var D=JSON.parse(document.getElementById("sd").textContent),q=document.getElementById("sq"),o=document.getElementById("sr"),n=document.getElementById("sn"),cb=[].slice.call(document.querySelectorAll("#sf input"));'
              'function E(t){return String(t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",\'"\':"&quot;"}[c]})}'
              'function go(){var v=q.value.trim();o.innerHTML="";if(v.length<1){n.textContent="";return}var lv=v.toLowerCase(),fs=cb.filter(function(c){return c.checked}).map(function(c){return c.value}),k=0,h="";'
              'D.forEach(function(d){var hit=null;fs.some(function(f){var t=d[f];if(!t)return false;var i=t.toLowerCase().indexOf(lv);if(i<0)return false;hit=[f,t,i];return true});if(!hit&&(d.n+d.e+d.c).toLowerCase().indexOf(lv)>=0)hit=["문서명",d.n,d.n.toLowerCase().indexOf(lv)];if(!hit)return;k++;if(k>300)return;'
              'var t=hit[1],i=Math.max(0,hit[2]),a=Math.max(0,i-40),sn=(a?"…":"")+E(t.slice(a,i))+"<mark>"+E(t.slice(i,i+v.length))+"</mark>"+E(t.slice(i+v.length,i+v.length+60))+"…";'
              'h+="<li><b>"+E(d.n)+"</b> <small>"+E(d.t)+(d.l?" · <a href=\\""+E(d.l)+"\\">"+E(d.e)+"</a>":" · "+E(d.e))+(d.v?" · <a href=\\""+E(d.v)+"\\" target=_blank rel=noopener>원본 ↗</a>":"")+"</small><p><em>"+hit[0]+"</em> "+sn+"</p></li>"});'
              'o.innerHTML=h;n.textContent=k+"건"+(k>300?" (앞 300건만)":"")}var tm;q.addEventListener("input",function(){clearTimeout(tm);tm=setTimeout(go,120)});cb.forEach(function(c){c.addEventListener("change",go)});'
              'var u=new URLSearchParams(location.search).get("q");if(u){q.value=u;go()}})()</script>')
    # 5) 문서 유형 사전 — 읽는 법 · 몇 건 · 어느 세기 · 예
    T = collections.defaultdict(list)
    for e, s in docs: T[(s.get('문서유형') or '기타').strip() or '기타'].append((e, s))
    cards = []
    for t, items in sorted(T.items(), key=lambda kv: -len(kv[1])):
        guide = ST.read_guide(t) or ST.glossary(t)
        cs = collections.Counter(cent(int(s['연도'])) for _, s in items if str(s.get('연도', '')).isdigit())
        seen, first, rest = set(), [], []
        for e, s in items: (rest if e['title'] in seen else first).append((e, s)); seen.add(e['title'])
        ex = ''.join(f'<li>{link(e)} — {h(dname(s))}</li>' for e, s in (first + rest)[:4])  # 되도록 다른 편에서
        cards.append(f'<div class="tcard" data-s="{h((t + guide).lower())}"><h2 id="t-{h(t)}">{h(t)} <small>{len(items)}건' + (' · ' + ', '.join(f'{c} {v}' for c, v in sorted(cs.items(), key=lambda x: int(x[0][:-2]))) if cs else '') + '</small></h2>'
                     + (f'<p>{h(guide)}</p>' if guide else '<p class="mute">읽는 법 설명이 아직 없습니다.</p>') + f'<ul>{ex}</ul>' + (f'<p class="mute">외 {len(items) - 4}건 — <a href="search.html?q={h(t)}">모두 찾기</a></p>' if len(items) > 4 else '') + '</div>')
    types = (f'<div class="col"><div class="tools"><input id="cq" type="search" placeholder="찾기: 홍패 · 교지 · 편지 · 노비 …" aria-label="유형 찾기"><span id="cn" class="mute"></span></div>'
             f'<p class="mute">이 시리즈에 나온 문서 유형 {len(T)}가지 — 많이 나온 순. 유형은 문서명에서 뽑은 초안입니다.</p><div class="tcards">' + ''.join(cards).replace('class="tcard" data-s', 'class="tcard" data-s') + '</div></div>' + SEARCH_JS)
    # 6) 검토 현황 — 사람이 원본과 대조한 문서(검토 칸)
    rows, tot, done = [], 0, 0
    for e in sorted(eps, key=lambda x: (x['ep'] or 0)):
        n = len(e['sel']); k = sum(1 for x in e['sel'] if (x.get('검토') or '').strip()); tot += n; done += k
        bad = sum((x.get('판독') or '').count('□') + (x.get('판독') or '').count('(?)') for x in e['sel'])
        tlink = f'<a href="{h(e["link"])}">{h(e["title"])}</a>' if e.get('link') else h(e['title'])
        pf = e.get('proof'); pfl = f'<a href="{h(pf)}">검토지</a>' if pf else ''
        rows.append(f'<tr data-s="{h((lab(e) + e["title"] + e["coll"]).lower())}"><td>{h(lab(e))}</td><td>{tlink}</td><td>{n}</td><td>{k}</td><td>{n - k}</td><td>{bad or ""}</td>'
                    f'<td><span class="pbar"><i style="width:{(k / n * 100) if n else 0:.0f}%"></i></span></td><td>{pfl}</td></tr>')
    review = (f'<div class="col"><div class="tiles"><div class="tile"><b>{done}</b><span>검토 마친 문서</span></div><div class="tile"><b>{tot - done}</b><span>남은 문서</span></div><div class="tile"><b>{(done / tot * 100) if tot else 0:.0f}%</b><span>진행</span></div></div>'
              '<p class="mute">검토 = 사람이 원본 사진과 판독 · 번역을 대조하고 검토 칸에 이름 · 날짜를 남긴 것(<code>studio.py proof</code> → <code>review</code>). 검토 전 문서에는 「초안」 딱지가 붙습니다. □ · (?)가 많은 편부터 보시면 좋습니다.</p>'
              '<div class="tools"><input id="cq" type="search" placeholder="찾기: 편 · 제목 · 소장처" aria-label="검토 현황 찾기"><span id="cn" class="mute"></span></div>'
              + table(['편', '제목', '문서', '검토', '남음', '□·(?)', '진행', '검토지'], [], 'rvt').replace('<tbody></tbody>', '<tbody>' + ''.join(rows) + '</tbody>') + review_form(eps) + '</div>' + SEARCH_JS + REVIEW_JS)
    return [('search.html', '전체 검색', f'문서 {len(idx)}건의 판독 · 번역 · 해제 · 이야기 전문을 한 곳에서 찾습니다 — 한자 한 글자, 이름 하나로.', search),
            ('types.html', '문서 유형 사전', f'고신 · 홍패 · 준호구 · 명문 … 이 시리즈에 나온 {len(T)}가지 문서를 읽는 법과 예.', types),
            ('quotes.html', '종이에 적힌 문장들', f'이야기에 "현대어(原文)"로 인용한 원문 {len(qs)}곳 전체 — 찾아보고, 수업 · 글쓰기 · SNS에 씁니다.', quotes),
            ('timeline.html', '전체 연표', f'{len(dated)}건의 문서를 한 줄로 — 세기별로 나누고, 편과 원본으로 바로 갑니다.', timeline),
            ('people.html', '인물 찾아보기', f'문서에 이름이 나온 {len(PP)}명을 가나다순으로 — 사람마다 나온 문서 · 편 · 원본, 여러 편에 걸친 인물 {len(multi)}명.', people),
            ('questions.html', '남겨 둔 질문 카드', f'문서만으로는 답할 수 없어 보는 사람과 나누려는 질문 {len(qq)}개.', questions),
            ('review.html', '검토 현황', f'문서 {tot}건 가운데 사람이 원본과 대조를 마친 문서 {done}건 — 편마다 남은 문서와 검토지.', review)]


def page_html(title, kicker, h1, lead, body, nav='', foot='', base_css=''):
    return (f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)}</title>'
            f'<style>{base_css}{CSS}</style></head><body><main>{nav}<p class="k">{h(kicker)}</p><h1>{h(h1)}</h1><p class="lead">{h(lead)}</p><div class="an">{body}</div>{foot}</main></body></html>')


def write_collections(folder, eps, title, nav='', foot='', base_css='', meta_fn=None, oh_url=None):
    out = []
    for fn, t, lead, body in collections_pages(eps, title):
        page = page_html(f'{title} — {t}', 'COLLECTION', f'{title} — {t}', lead, body, nav, foot, base_css)
        if meta_fn: page = ST.put_share(page, meta_fn(fn, f'{title} — {t}', lead))
        page = ST.put_oldhangul(page, ST.oldhangul_css(body, url=oh_url))
        open(os.path.join(folder, fn), 'w', encoding='utf-8').write(page); out.append(fn)
    return out


DATA_README = """{title} — 데이터 묶음

들어 있는 것
- 편별 폴더/selection.csv : 문서마다 문서명 · 연도 · 유형 · 인물 · 판독 · 원문 · 번역 · 해제 · 요약 · 이야기 · 원본 뷰어 링크
- 편별 폴더/curator.md · delivery.md : 큐레이터 노트 · 전달 에디팅 (있으면)
- 편별 폴더/corrections.csv : 함께 고친 곳(날짜 · 이전 · 이후 · 근거) (있으면)
- analysis-data.json : 통합 분석 집계(세기 · 유형 · 지역 · 정서 · 인물 · 인용 · 편별)
- analysis-episodes.csv : 편별 한 줄 표
- datapackage.json : 표의 구조 · 출처 · 이용 조건(Frictionless Data — R · Python · OpenRefine 등에서 바로 읽기)

읽을 때
- 판독 · 번역 · 해제는 이미지에 근거한 초안입니다. □는 못 읽은 글자, (?)는 불확실한 글자입니다.
- 연도 · 문서유형 · 인물은 문서명에서 자동으로 뽑은 값입니다.
- 엑셀에서 열 때 CSV는 UTF-8(BOM)이라 한글이 바로 보입니다.

출처와 이용
- 문서와 이미지: 한국학중앙연구원 한국고문서자료관 소장·제공 · 각 소장처. 원본은 selection.csv의 '뷰어링크'에서 보세요.
- 이 묶음에는 이미지가 없습니다. 이미지 재사용은 소장처 동의가 필요합니다(한국고문서자료관 031-730-8873, 8876).
- 판독 · 번역 텍스트를 인용할 때는 "초안"임과 출처를 밝혀 주세요. 고칠 곳은 「판독 고침 제보」로 알려 주세요.{license}
만든 날: {date}
"""


LICENSES = {'CC BY 4.0': ('CC-BY-4.0', 'https://creativecommons.org/licenses/by/4.0/'), 'CC BY-SA 4.0': ('CC-BY-SA-4.0', 'https://creativecommons.org/licenses/by-sa/4.0/'),
            'CC BY-NC 4.0': ('CC-BY-NC-4.0', 'https://creativecommons.org/licenses/by-nc/4.0/'), 'CC0': ('CC0-1.0', 'https://creativecommons.org/publicdomain/zero/1.0/')}
SEL_FIELDS = ['순서', '자료ID', '문서명', '연도', '문서유형', '인물', '유형설명', '대표장', '이미지', '원본경로', '캡션', '이야기', '판독', '원문', '번역', '해제', '요약', '검토', '뷰어링크', '공유이미지']


def datapackage(names, title, license=''):
    """Frictionless Data 묶음 설명(datapackage.json) — 다른 도구(Excel 밖의 R · Python · Open Refine 등)가 표의 구조를 알게"""
    lic = next(((n, u) for k, (n, u) in LICENSES.items() if license.startswith(k)), None)
    res = []
    for n in names:
        if n.endswith('selection.csv'):
            res.append({'name': f'{len(res) + 1:03d}-' + re.sub(r'[^a-z0-9._-]+', '-', n.lower().replace('/selection.csv', '')).strip('-') + '-selection', 'path': n, 'format': 'csv', 'encoding': 'utf-8-sig',
                        'schema': {'fields': [{'name': f, 'type': 'integer' if f == '순서' else 'string'} for f in SEL_FIELDS]}})
        elif n == 'analysis-episodes.csv':
            res.append({'name': 'episodes', 'path': n, 'format': 'csv', 'encoding': 'utf-8-sig', 'schema': {'fields': [{'name': f, 'type': 'integer' if f in ('문서 수', '처음 연도', '끝 연도') else 'string'} for f in ['편', '제목', '소장처', '종류', '지역', '문서 수', '처음 연도', '끝 연도', '핵심 정서', '전하고 싶은 것', '남겨 둔 질문']]}})
        elif n == 'analysis-data.json':
            res.append({'name': 'analysis', 'path': n, 'format': 'json'})
    dp = {'name': 'gomunseo-data', 'title': title + ' — 데이터 묶음', 'description': '판독 · 번역 · 해제 · 요약 · 이야기와 큐레이터 노트, 통합 분석 집계. 판독 · 번역은 이미지에 근거한 초안. 이미지는 포함하지 않음(소장처 동의 필요).',
          'sources': [{'title': '한국학중앙연구원 한국고문서자료관', 'path': 'https://archive.aks.ac.kr'}], 'resources': res}
    if lic: dp['licenses'] = [{'name': lic[0], 'path': lic[1], 'title': license.split(' —')[0]}]
    elif license: dp['licenses'] = [{'title': license}]
    return dp


SOURCE_FILES = ('selection.csv', 'curator.md', 'delivery.md', 'corrections.csv')


def source_date(eps_dirs):
    """편별 원자료가 마지막으로 바뀐 날(YYYY-MM-DD) — 다시 만들어도 내용이 같으면 같은 날짜"""
    import datetime
    ts = [os.path.getmtime(os.path.join(d, f)) for _, d in eps_dirs for f in SOURCE_FILES if os.path.exists(os.path.join(d, f))]
    return datetime.date.fromtimestamp(max(ts)).isoformat() if ts else datetime.date.today().isoformat()


def data_bundle(path, eps_dirs, folder, title, license=''):
    """데이터 묶음 ZIP — eps_dirs: [(폴더 이름, 원본 폴더)] (selection.csv · curator.md · delivery.md · corrections.csv), folder: analysis-*.json/csv가 있는 곳.
    내용이 같으면 같은 바이트(파일 순서 · 묶음 안 날짜 고정, '만든 날'은 편별 원자료가 마지막으로 바뀐 날)."""
    import zipfile
    items = [(os.path.join(d, f), f'{name}/{f}') for name, d in eps_dirs for f in SOURCE_FILES if os.path.exists(os.path.join(d, f))]
    date = source_date(eps_dirs)  # 원자료(편별 파일)가 마지막으로 바뀐 날 — 분석 파일은 만들 때마다 새로 써지므로 뺌
    for f in ('analysis-data.json', 'analysis-episodes.csv'):
        if os.path.exists(os.path.join(folder, f)): items.append((os.path.join(folder, f), f))
    def put(z, arc, data):
        zi = zipfile.ZipInfo(arc, date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; zi.flag_bits |= 0x800; zi.external_attr = 0o644 << 16
        z.writestr(zi, data)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        put(z, '읽어보기.txt', DATA_README.format(title=title, date=date, license=('\n- 텍스트 이용 조건: ' + license) if license else '').encode('utf-8'))
        for p, arc in items: put(z, arc, open(p, 'rb').read())
        put(z, 'datapackage.json', json.dumps(datapackage([arc for _, arc in items], title, license), ensure_ascii=False, indent=1).encode('utf-8'))
    return path

def write(path, title, body, nav='', foot='', base_css='', meta='', oh_url=None):
    page = (
        f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)} — 통합 분석</title>'
        f'<style>{base_css}{CSS}</style></head><body><main>{nav}<p class="k">ANALYSIS</p><h1>{h(title)} — 통합 분석</h1>'
        f'<p class="lead">편마다 따로 보던 문서 · 노트 · 결과물을 한데 모아, 전체가 무엇을 담고 있는지 한 장에서 읽습니다.</p>{body}{foot}</main></body></html>')
    page = ST.put_oldhangul(page, ST.oldhangul_css(body, url=oh_url))
    open(path, 'w', encoding='utf-8').write(ST.put_share(page, meta) if meta else page)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', required=True, help='series.tsv (ep · work · theme [· kind])'); ap.add_argument('--out', required=True); ap.add_argument('--title', default='고문서 시리즈')
    a = ap.parse_args()
    eps = load_series(a.list)
    if not eps: sys.exit('분석할 편이 없습니다.')
    body, s = build(eps, a.title)
    folder = os.path.dirname(os.path.abspath(a.out)); os.makedirs(folder, exist_ok=True)
    write(a.out, a.title, body); save_data(folder, s); write_collections(folder, eps, a.title)
    print(f'→ {a.out}  편 {s["eps"]} · 문서 {s["docs"]} · 소장처 {s["colls"]}')


if __name__ == '__main__':
    main()
