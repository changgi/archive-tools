#!/usr/bin/env python3
"""통합 분석 — 여러 편(테마)의 문서 · 노트 · 결과물을 모아 한 장에서 전체를 읽는 분석 페이지.

  python3 analysis.py --list series.tsv --out site/analysis.html [--title "시리즈 제목"]

  (series.py 가 사이트를 만들 때 analysis.html 도 함께 만듭니다.)

보여 주는 것: 핵심 수치 · 자동 요약 · 세기 · 연도 분포 · 문서 유형 · 유형×세기 · 소장처 종류 · 지역 ·
            핵심 정서 · 판독 난도 · 원문 인용 모음 · 자주 나온 인물 · 남겨 둔 질문 · 편별 표 · 데이터의 한계.
모든 수치는 selection.csv(문서명에서 뽑은 연도·유형·인물 포함)와 curator.md · delivery.md에서 셉니다.
"""
import argparse, collections, csv, glob, html, json, os, re, statistics, sys

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(errors='replace')
    except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio as ST

h = html.escape
QRX = r'"([^"(]{2,80})\(([^)]+)\)[.,]?"'
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
    return f'<div class="tw"><table class="{cls}"><thead><tr>' + ''.join(f'<th>{h(x)}</th>' for x in head) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table></div>'


def tv(items, head=('항목', '수')):
    return '<details class="tvw"><summary>표로 보기</summary>' + table(head, [(h(str(k)), v) for k, v in items]) + '</details>'


CSS = '''
.an{--gold:#c4964a;--dim:#b9ab90}
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
'''


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
    quotes = [(m.group(1), m.group(2), e) for e, s in docs for m in re.finditer(QRX, s.get('이야기') or '')]
    dur = sum(e['dur'] for e in eps); cards = sum(e['cards'] for e in eps)
    C = collections.Counter(cent(y) for y in ys)
    centuries = sorted(C, key=lambda c: int(c[:-2]))
    T = collections.Counter((s.get('문서유형') or '기타').strip() or '기타' for _, s in docs)
    K = collections.Counter(e['kind'] for e in eps if e.get('kind'))
    R = collections.Counter(region_of(e['coll']) for e in eps)
    P = collections.Counter()
    for _, s in docs:
        for p in re.split(r'[;,·/]\s*', s.get('인물') or ''):
            p = p.strip()
            if 1 < len(p) < 12: P[p] += 1
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
        r1, rn = R.most_common(1)[0]; ins.append(f'소장처 {len(colls)}곳은 {len([k for k in R if k != "기타"])}개 시·도에 걸쳐 있습니다. 가장 많은 곳은 <b>{h(r1)}</b>({rn}편)입니다.')
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
        hm = '<div class="tw" style="border:0"><table class="hm"><tr><th></th>' + ''.join(f'<th>{c}</th>' for c in centuries) + '</tr>' + ''.join(
            f'<tr><th class="r">{h(t)}</th>' + ''.join(
                (f'<td style="background:rgba(196,150,74,{0.18 + 0.82 * cell[(t, c)] / mx:.2f});color:{"#16130f" if cell[(t, c)] / mx > 0.45 else "#f3ead8"}" title="{h(t)} · {c}: {cell[(t, c)]}건">{cell[(t, c)]}</td>' if cell[(t, c)] else f'<td class="z" style="background:#231d15" title="{h(t)} · {c}: 0건">0</td>') for c in centuries) + '</tr>' for t in tt) + '</table></div>'
    out.append('<h2 id="a-type">어떤 문서인가</h2><div class="two">'
               f'<div class="card"><h3>문서 유형 (상위 15)</h3><p class="q">전체 {len(T)}가지 · 막대에 마우스를 올리면 비율</p>{hbars(T.most_common(), len(docs), top=15)}{tv(T.most_common(), ("유형", "문서 수"))}</div>'
               f'<div class="card"><h3>유형 × 세기</h3><p class="q">많이 나온 유형 10가지가 어느 세기에 몰려 있는지 — 진할수록 많음</p>{hm or "<p class=mute>자료 없음</p>"}</div></div>')

    # ---- 어디서
    out.append('<h2 id="a-where">어디의 기록인가</h2><div class="two">' +
               (f'<div class="card"><h3>{h(kinds_label)}</h3><p class="q">편 수</p>{hbars(K.most_common(), unit="편")}</div>' if K else '') +
               f'<div class="card"><h3>지역 (현재 시·도)</h3><p class="q">소장처 이름의 첫 지명으로 나눈 편 수 · 모르는 이름은 「기타」</p>{hbars(R.most_common(), unit="편")}{tv(R.most_common(), ("시·도", "편 수"))}</div></div>')

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
    out.append('<h2 id="a-read">얼마나 읽었나</h2><div class="two">'
               f'<div class="card"><h3>읽기 진행</h3><p class="q">문서 {len(docs)}건 기준</p>{hbars([("원문 판독", read_n), ("번역", tr_n), ("해제", sum(1 for _, s in docs if (s.get("해제") or "").strip())), ("요약", sum(1 for _, s in docs if (s.get("요약") or "").strip())), ("원문 인용 이야기", sum(1 for _, s in docs if re.search(QRX, s.get("이야기") or ""))), ("검토 표시", sum(1 for _, s in docs if s.get("검토")))], len(docs))}</div>'
               f'<div class="card"><h3>읽기 어려웠던 편</h3><p class="q">못 읽은 글자 □ + 불확실 (?) 이 많은 순</p>{hbars([(f"{lab(e)} {e['title'][:14]}", a + b) for a, b, e in rd], unit="자") if rd else "<p class=mute>□ · (?) 표시가 없습니다</p>"}</div></div>')

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
               f'<div class="card"><h3>인물 (상위 15)</h3><p class="q">문서명에서 뽑은 이름 · 같은 이름이 다른 사람일 수 있습니다</p>{hbars(P.most_common(15), unit="건") if P else "<p class=mute>자료 없음</p>"}</div>'
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
    out.append(f'<h2 id="a-eps">편별 한 줄 — {len(eps)}편</h2>' + table(['편', '제목', '소장처', '종류', '연대', '문서', '핵심 정서', '전하고 싶은 것'], rows, 'ept'))

    # ---- 한계
    out.append('<h2 id="a-lim">이 분석을 읽을 때</h2><ul class="ins">'
               '<li>이 수치는 <b>이 시리즈가 고른 문서</b>의 분포입니다. 소장처 전체나 조선 시대 전체의 경향이 아닙니다(고른 기준: 사람의 목소리가 들리는 한 줄 · 다양성).</li>'
               '<li>연도 · 문서 유형 · 인물은 문서명과 연호에서 자동으로 뽑은 초안입니다. 같은 이름이 다른 사람일 수 있습니다.</li>'
               '<li>지역은 소장처 이름의 첫 지명을 지금의 시 · 도로 옮긴 것입니다. 문서가 만들어진 곳과 다를 수 있습니다.</li>'
               '<li>판독 · 번역은 이미지에 근거한 초안입니다. □ · (?)는 그대로 남겼습니다.</li></ul></div>')
    summary = dict(eps=len(eps), docs=len(docs), colls=len(colls), span=(min(ys), max(ys)) if ys else None, han=han, quotes=len(quotes), insights=ins)
    return '\n'.join(out), summary


def write(path, title, body, nav='', foot='', base_css=''):
    open(path, 'w', encoding='utf-8').write(
        f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)} — 통합 분석</title>'
        f'<style>{base_css}{CSS}</style></head><body><main>{nav}<p class="k">ANALYSIS</p><h1>{h(title)} — 통합 분석</h1>'
        f'<p class="lead">편마다 따로 보던 문서 · 노트 · 결과물을 한데 모아, 전체가 무엇을 담고 있는지 한 장에서 읽습니다.</p>{body}{foot}</main></body></html>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', required=True, help='series.tsv (ep · work · theme [· kind])'); ap.add_argument('--out', required=True); ap.add_argument('--title', default='고문서 시리즈')
    a = ap.parse_args()
    eps = load_series(a.list)
    if not eps: sys.exit('분석할 편이 없습니다.')
    body, s = build(eps, a.title)
    write(a.out, a.title, body)
    print(f'→ {a.out}  편 {s["eps"]} · 문서 {s["docs"]} · 소장처 {s["colls"]}')


if __name__ == '__main__':
    main()
