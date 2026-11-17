#!/usr/bin/env python3
"""시리즈 — 여러 편(테마)을 묶어 한 사이트로: 갤러리 · 기획 노트 · 홍보 가이드 · 활용 가이드 · 시리즈 카드.

  python3 series.py --list series.tsv --note series.md --out site [--title "고문서 한 장"]

series.tsv (탭 구분, 첫 줄 머리글):  ep  work  theme  [url]  [kind(소장처 종류: 문중·서원…)]
   각 편은 먼저 studio.py edit · mediate (· video.py) 를 마친 상태여야 합니다.
series.md (기획 노트):  # 시리즈 제목  다음에 ## 제목별 문단. 아래 제목을 쓰면 알맞은 자리에 들어갑니다.
   ## 왜 만들었나 / ## 전하고 싶은 것 / ## 고른 기준 / ## 이렇게 보이길 바랐다 / ## 이렇게 써 주세요 /
   ## 지킨 원칙 / ## 부탁 / ## 히스토리   (히스토리는 "- 날짜 · 무엇" 줄)
결과: site/index.html(갤러리) · about.html · promote.html · use.html · analysis.html(통합 분석) · cards/(시리즈 카드) · eps/NN-테마/(각 편 결과물 복사)
"""
import argparse, collections, csv, glob, html, json, os, re, shutil, sys

for _s in (sys.stdout, sys.stderr):  # Windows에서 출력을 파일·파이프로 보낼 때(cp949) 기호 때문에 멈추지 않게
    try: _s.reconfigure(errors='replace')
    except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio as ST
import analysis as AN

h = html.escape
CSS = '''body{margin:0;background:#16130f;color:#efe6d4;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;line-height:1.8}main{max-width:1100px;margin:0 auto;padding:6vh 5vw}
a{color:#c4964a}h1{font-family:'Noto Serif KR',serif;font-size:clamp(30px,5vw,52px);line-height:1.25;margin:.2em 0}.k{color:#c4964a;letter-spacing:.18em;font-size:13px}
h2{font-family:'Noto Serif KR',serif;font-size:25px;margin:2em 0 .5em;color:#f3ead8}h3{margin:0 0 6px;color:#c4964a;font-size:16px}p{color:#d9cfbb}.lead{font-size:18px;color:#e8dcc4}
nav.top{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}nav.top a{background:#231d15;border:1px solid #4a3e2c;border-radius:30px;padding:5px 13px;text-decoration:none;font-size:14px;color:#efe6d4}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}.box{background:#1f1a14;border:1px solid #3a3225;border-radius:14px;padding:16px 18px}.box p{margin:.3em 0;font-size:15px}
.ep{background:#1f1a14;border:1px solid #3a3225;border-radius:14px;overflow:hidden;display:flex;flex-direction:column}.ep img{width:100%;aspect-ratio:4/5;object-fit:cover;object-position:50% 0;display:block;background:#0d0c0a}
.ep .tx{padding:12px 14px}.ep .tx small{color:#c4964a;font-weight:700}.ep .tx b{display:block;font-size:16.5px;line-height:1.4;margin:2px 0}.ep .tx span{font-size:13px;color:#b9ab90}
.ql{display:flex;flex-wrap:wrap;gap:5px;padding:0 14px 14px}.ql a{font-size:12.5px;color:#d5cab4;text-decoration:none;border:1px solid #4a3e2c;border-radius:20px;padding:2px 9px;background:#231d15}.ql a:hover{border-color:#c4964a}
.stats{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}.stats div{background:#1f1a14;border:1px solid #3a3225;border-radius:12px;padding:10px 16px}.stats b{display:block;font:700 26px 'Noto Serif KR',serif;color:#c4964a}.stats span{font-size:13px;color:#b9ab90}
.tw{overflow-x:auto;border:1px solid #3a3225;border-radius:12px}table{border-collapse:collapse;width:100%;min-width:720px;font-size:14.5px}th,td{padding:8px 10px;border-bottom:1px solid #2c251b;text-align:left;vertical-align:top}th{background:#1f1a14;color:#c4964a}
.cards{display:flex;gap:12px;overflow-x:auto}.cards img{height:340px;border-radius:10px;border:1px solid #3a3225}
.tl{border-left:2px solid #c4964a66;margin:10px 0 0 6px;padding-left:20px}.tl div{margin:0 0 12px}
*:focus-visible{outline:2px solid #c4964a;outline-offset:2px}
@media print{body{background:#fff;color:#111}main{max-width:none;padding:0 8mm}nav.top,.ql,video{display:none}h1,h2,h3,p,li,td,th,span,b,small{color:#111!important}a{color:#111}.box,.ep,.stats div{background:#fff;border:1px solid #bbb;break-inside:avoid}.ep img{max-height:60mm;object-fit:contain}}
footer{margin-top:6vh;border-top:1px solid #3a3225;padding-top:14px;font-size:13.5px;color:#9d917c}'''
USE = [('교사', '활동지(끝의 「선생님께」)로 1–2차시 수업 — 원문 한 줄 찾기 → 번역 읽기 → 「남겨 둔 질문」 토론'),
       ('학예사 · 전시기획자', '원본 묶음으로 패널, 전달 에디팅(연출 노트)대로 공간 설계, 비하인드 카드로 기획 의도 벽, 영상 루프'),
       ('연구자', 'selection.csv의 판독·번역을 출발점으로 다시 읽고 고치기, 원본 면으로 검증'),
       ('기록관리자', '"증거로서의 기록", 출처 표기·메타데이터 실습 사례'),
       ('문중 · 지자체 · 서원향교', '우리 집안·고장 문서를 이야기로 — 종가 행사·축제 전시, 답사 해설'),
       ('크리에이터', '편마다 준비된 릴스·카드·채널별 문구로 시리즈 운영'),
       ('작가(소설·웹툰·시나리오)', '「남겨 둔 질문」에서 시작, 원본 사진으로 고증, 원문 한 줄을 대사로'),
       ('개발자 · 데이터', '판독 텍스트로 검색·연표·지도(권리 확인 후)')]
CHECK = ['이미지 재사용·상업 이용은 소장처 동의(한국고문서자료관 031-730-8873, 8876). 공개 전이면 mediate --placeholder 결과물로',
         '출처 표기: "이미지: 한국학중앙연구원 한국고문서자료관 소장·제공 · 소장처"', '판독·번역은 초안 — 인용할 때 밝히기', '각색은 사실과 허구를 구분해 밝히기',
         '민감한 기록(기근·노비·자매·형벌)은 존엄을 먼저', '근대 명부의 실명 등 개인정보 배려']


def read_note(p):
    t = open(p, encoding='utf-8').read() if p and os.path.exists(p) else ''
    title = (re.search(r'^#\s+(.+)$', t, re.M) or [None, ''])[1].strip()
    secs = [(m.group(1).strip(), m.group(2).strip()) for m in re.finditer(r'^##\s*(.+?)\s*\n(.*?)(?=^##\s|\Z)', t, re.S | re.M)]
    return title, secs


HOME = None
TEXT_LICENSE = ''  # 판독 · 번역 등 텍스트의 이용 조건(--text-license)
SITE = ''      # 공개 주소(…/site/) — 링크 미리 보기용
SDESC = ''


def page(path, title, body, back=True, desc=''):
    home = f'<a href="{h(HOME[0])}">{h(HOME[1])}</a>' if HOME else ''
    nav = f'<nav class="top">{home}<a href="index.html">갤러리</a><a href="about.html">기획 노트</a><a href="promote.html">홍보 가이드</a><a href="use.html">활용 가이드</a><a href="analysis.html">통합 분석</a><a href="search.html">검색</a><a href="types.html">유형 사전</a><a href="quotes.html">문장</a><a href="timeline.html">연표</a><a href="questions.html">질문 카드</a><a href="review.html">검토 현황</a></nav>'
    html_ = (f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)}</title><style>{CSS}</style></head><body><main>{nav}{body}<footer>이미지: 한국학중앙연구원 한국고문서자료관 소장·제공 · 각 소장처(재사용은 소장처 동의 필요) · 판독·번역은 이미지에 근거한 초안{(" · 텍스트 " + h(TEXT_LICENSE)) if TEXT_LICENSE else ""} · 만든 도구: aks-archive-harvester (github.com/changgi/archive-tools)</footer></main></body></html>')
    name = os.path.basename(path)
    html_ = ST.put_oldhangul(html_, ST.oldhangul_css(body))
    open(path, 'w', encoding='utf-8').write(ST.put_share(html_, ST.share_meta(title, desc or SDESC, (SITE + 'share.jpg') if SITE else '', (SITE + name) if SITE else '')))


def bars(data, color='#c4964a'):
    if not data: return ''
    mx = max(v for _, v in data) or 1; w = 340; out = [f'<svg viewBox="0 0 {w} {30*len(data)+10}" style="width:100%;max-width:{w}px">']
    for i, (k, v) in enumerate(data):
        y = 8 + i * 30; bw = (w - 150) * v / mx
        out.append(f'<text x="96" y="{y+15}" text-anchor="end" fill="#d5cab4" font-size="13">{h(str(k))}</text><rect x="104" y="{y+2}" width="{bw:.0f}" height="18" rx="3" fill="{color}"/><text x="{110+bw:.0f}" y="{y+15}" fill="#f3ead8" font-size="13">{v}</text>')
    return ''.join(out) + '</svg>'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', required=True); ap.add_argument('--note'); ap.add_argument('--out', required=True); ap.add_argument('--title')
    ap.add_argument('--text-license', help='판독 · 번역 · 해제 등 텍스트의 이용 조건(예: "CC BY 4.0") — 사이트 아래 · 데이터 묶음에 표시'); ap.add_argument('--site-url', help='사이트를 올릴 주소(예: https://아이디.github.io/저장소/site/) — 카카오톡·SNS 링크 미리 보기 그림에 필요'); ap.add_argument('--home', help='상단 메뉴 첫 칸에 둘 바깥 주소(예: 전체 갤러리)'); ap.add_argument('--home-label', default='← 처음으로')
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.list, encoding='utf-8-sig'), delimiter='\t'))
    if not rows or not {'work', 'theme'} <= set(rows[0]): sys.exit('series.tsv 첫 줄은 머리글이어야 합니다: ep<TAB>work<TAB>theme[<TAB>url]')
    base = os.path.dirname(os.path.abspath(a.list))
    global HOME, SITE, SDESC, TEXT_LICENSE; TEXT_LICENSE = a.text_license or ''; HOME = (a.home, a.home_label) if a.home else None; SITE = ST.base_url(a.site_url) if a.site_url else ''
    ntitle, secs = read_note(a.note); stitle = a.title or ntitle or '고문서 시리즈'
    out = a.out; os.makedirs(out, exist_ok=True); os.makedirs(os.path.join(out, 'eps'), exist_ok=True)
    EPS = []; docs = []; AE = []; FIRSTIMG = []
    for r in rows:
        work, theme = r['work'].strip(), r['theme'].strip()
        if not os.path.isdir(work) and os.path.isdir(os.path.join(base, work)): work = os.path.join(base, work)  # series.tsv 기준 상대 경로
        ep = int(r['ep']) if r.get('ep') else len(EPS) + 1
        md = os.path.join(work, 'mediate', theme); ed = os.path.join(work, 'edit', theme)
        if not os.path.exists(os.path.join(md, 'exhibit.html')): print(f'건너뜀: {work}/mediate/{theme}/exhibit.html 이 없습니다 (작업 폴더·테마 확인, 또는 먼저 studio.py mediate)'); continue
        slug = f'{ep:02d}-{theme}'; dst = os.path.join(out, 'eps', slug)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(md, dst, ignore=shutil.ignore_patterns('.*'))
        for full in glob.glob(os.path.join(dst, 'video', '*_reel.mp4')) + glob.glob(os.path.join(dst, 'video', '*_wide.mp4')):
            if os.path.exists(full[:-4] + '_web.mp4'): os.remove(full)  # 웹 압축본이 있으면 원본 크기 영상은 빼기
        shutil.copy(os.path.join(ed, 'selection.csv'), dst)
        for f in ('curator.md', 'delivery.md', 'corrections.csv'):
            if os.path.exists(os.path.join(ed, f)): shutil.copy(os.path.join(ed, f), dst)
        sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig'))); docs += sel
        if sel and not FIRSTIMG and os.path.exists(os.path.join(ed, sel[0].get('이미지') or '-')): FIRSTIMG.append(os.path.join(ed, sel[0]['이미지']))
        th = json.load(open(os.path.join(ed, 'theme.json'), encoding='utf-8')) if os.path.exists(os.path.join(ed, 'theme.json')) else {}
        cj = os.path.join(work, 'collection.json'); coll = json.load(open(cj, encoding='utf-8'))['name'] if os.path.exists(cj) else os.path.basename(work)
        cards = sorted(glob.glob(os.path.join(dst, 'cards', '*.png')) + glob.glob(os.path.join(dst, 'cards', '*.jpg')))
        cover = next((c for c in cards if re.fullmatch(r'0?1\.(png|jpg)', os.path.basename(c))), cards[0] if cards else '')
        vids = sorted(glob.glob(os.path.join(dst, 'video', '*_web.mp4')))
        if not vids:
            vids = sorted(glob.glob(os.path.join(dst, 'video', '*.mp4')))
            if vids: print(f'  EP.{ep:02d}: 웹용 영상(_web.mp4)이 없어 원본 크기 영상을 복사했습니다(용량 큼) → video.py ... --web 권장')
        AE.append(AN.episode(ep, th.get('title') or theme, coll, ed, kind=(r.get('kind') or '').strip(), cards=len(cards),
                             videos=glob.glob(os.path.join(md, 'video', '*_reel*.mp4')), link=f'eps/{slug}/index.html'))
        EPS.append(dict(ep=ep, slug=slug, title=th.get('title') or theme, coll=coll, cover=os.path.relpath(cover, out).replace(os.sep, '/') if cover else '', cur=ST.read_curator(ed), dv=ST.read_delivery(ed),
                        vids=[os.path.relpath(v, out).replace(os.sep, '/') for v in vids], has={f: os.path.exists(os.path.join(dst, f)) for f in ('index.html', 'exhibit.html', 'handout.html', 'channels.md', 'curator.md', 'delivery.md', 'promo.md')}))
    if not EPS: sys.exit('묶을 편이 없습니다. series.tsv의 work·theme 경로와 mediate 결과를 확인하세요.')
    EPS.sort(key=lambda e: e['ep'])
    # ---- 시리즈 카드
    cd = os.path.join(out, 'cards'); shutil.rmtree(cd, ignore_errors=True); os.makedirs(cd)
    foot = f'{stitle} · 이미지: 한국학중앙연구원 한국고문서자료관 소장·제공'
    ST.note_card('시리즈 기획 노트', stitle, [('담은 것', f'{len(EPS)}편 · 문서 {len(docs)}건')], os.path.join(cd, '00_표지.png'), foot=foot, big_size=70)
    for i, (t, body) in enumerate([s for s in secs if s[0] != '히스토리'][:8], 1):
        first = re.split(r'\n\s*\n', body)[0].replace('\n', ' ')
        ST.note_card(t, first[:90], [], os.path.join(cd, f'{i:02d}_{re.sub(r"[^가-힣A-Za-z0-9]", "", t)[:10]}.png'), foot=foot, big_size=54 if len(first) > 40 else 64)
    scards = sorted(os.listdir(cd))
    # ---- 갤러리
    cent = collections.Counter(f"{(int(s['연도'])-1)//100+1}세기" if str(s.get('연도', '')).isdigit() else '연도 미상' for s in docs)
    CENT = sorted(cent.items(), key=lambda x: (x[0] == '연도 미상', x[0]))
    sec = dict(secs)
    def links(e):
        b = f"eps/{e['slug']}/"; L = [('첫 페이지', 'index.html'), ('전시', 'exhibit.html'), ('활동지', 'handout.html'), ('채널', 'channels.md'), ('노트', 'curator.md'), ('전달', 'delivery.md'), ('홍보 글', 'promo.md')]
        return ''.join(f'<a href="{b}{f}">{n}</a>' for n, f in L if e['has'].get(f)) + ''.join(f'<a href="{v}">{"릴스" if "reel" in v else "가로"}</a>' for v in e['vids']) + f'<a href="{b}selection.csv">CSV</a>'
    grid = ''.join(f'<div class="ep"><a href="eps/{e["slug"]}/index.html"><img src="{h(e["cover"])}" alt="EP.{e["ep"]:02d} {h(e["title"])} — 표지" loading="lazy"></a><div class="tx"><small>EP.{e["ep"]:02d}</small><b>{h(e["title"])}</b><span>{h(e["coll"])}</span>{("<p style=font-size:14px>" + h(e["cur"]["message"]) + "</p>") if e["cur"].get("message") else ""}</div><div class="ql">{links(e)}</div></div>' for e in EPS)
    why = sec.get('왜 만들었나') or sec.get('왜') or ''
    global SDESC
    SDESC = re.split(r'\n\s*\n', why)[0] if why else (sec.get('전하고 싶은 것') or f'{len(EPS)}편 · 문서 {len(docs)}건을 원문으로 읽은 시리즈')
    ST.share_image(FIRSTIMG[0] if FIRSTIMG else None, stitle, f'{len(EPS)}편 · 문서 {len(docs)}건 · 전시 · 영상 · 활동지 · 통합 분석', os.path.join(out, 'share.jpg'), tag='SERIES')
    an_body, an_sum = AN.build(sorted(AE, key=lambda e: e['ep']), stitle); AN.save_data(out, an_sum)
    AN.data_bundle(os.path.join(out, 'data.zip'), [(f"{e['slug']}", os.path.join(out, 'eps', e['slug'])) for e in EPS], out, stitle, license=TEXT_LICENSE)
    smap = ('<h2>이 사이트에 있는 것</h2><div class="g">' + ''.join(f'<div class="box"><h3><a href="{u}">{t}</a></h3><p>{d}</p></div>' for u, t, d in [
        ('#eps', f'에피소드 {len(EPS)}편', '편마다 첫 페이지 · 전시 · 활동지 · 카드 · 영상 · 노트 · CSV'),
        ('analysis.html', '통합 분석', '시대 · 문서 유형 · 지역 · 정서 · 판독 · 원문 인용 · 질문을 한 장에'),
        ('about.html', '기획 노트', '왜 만들었나 · 고른 기준 · 히스토리 · 편별 메시지'),
        ('promote.html', '홍보 가이드', '채널별 형식과 문구 · 4주 계획'),
        ('use.html', '활용 가이드', '누가 무엇을 할 수 있나 · 지킬 것'),
        ('search.html', '전체 검색', '판독 · 번역 · 해제 · 이야기 전문에서 낱말 · 한자로'),
        ('types.html', '문서 유형 사전', '문서 종류마다 읽는 법 · 건수 · 시대 · 예'),
        ('quotes.html', '종이에 적힌 문장들', '이야기에 인용한 원문 전체 · 찾기'),
        ('timeline.html', '전체 연표', '모든 문서를 연도순으로 · 편과 원본으로 바로'),
        ('questions.html', '남겨 둔 질문 카드', '인쇄해 잘라 쓰는 토론 · 글쓰기 카드'),
        ('review.html', '검토 현황', '사람이 원본과 대조를 마친 문서 · 남은 문서 · □·(?)'),
        ('data.zip', '데이터 묶음 ZIP', '편별 판독 · 번역 · 해제 · 노트 · 분석 집계 — 이미지 없이 가볍게'),
        ('#cards', f'시리즈 카드 {len(scards)}장', 'SNS에 바로 쓰는 기획 노트 카드')]) + '</div>')
    smap += '<h2>한눈에 — 자동 요약</h2><ul>' + ''.join(f'<li>{x}</li>' for x in an_sum['insights'][:4]) + '</ul><p><a href="analysis.html">통합 분석 전체 보기 →</a></p>'
    lead_ = ('<p class="lead">' + h(re.split(r"\n\s*\n", why)[0]) + '</p>') if why else ''  # 파이썬 3.10 · 3.11: f-string 안에 \ 를 쓸 수 없음
    body = f'''<p class="k">SERIES</p><h1>{h(stitle)}</h1>{lead_}
<div class="stats"><div><b>{len(EPS)}</b><span>편</span></div><div><b>{len(docs)}</b><span>문서</span></div><div><b>{sum(1 for e in EPS if e["vids"])}</b><span>영상 있는 편</span></div><div><b>{len(scards)}</b><span>시리즈 카드</span></div></div>
<h2>결과물 바로 가기</h2><p>편마다: <b>첫 페이지</b>(모든 결과물) · <b>전시</b> 웹페이지 · <b>활동지</b>(선생님께) · <b>채널</b>별 홍보안 · 큐레이터 <b>노트</b> · <b>전달</b> 에디팅 · <b>홍보 글</b> · 릴스·가로 영상 · 원문·번역 <b>CSV</b></p>
{smap}
<h2 id="eps">에피소드</h2><div class="g">{grid}</div>
<h2 id="cards">시리즈 카드</h2><div class="cards" tabindex="0" role="region" aria-label="시리즈 카드 — 옆으로 넘겨 보기">{''.join(f'<img src="cards/{c}" alt="시리즈 카드 {k + 1}" loading="lazy">' for k, c in enumerate(scards))}</div>'''
    page(os.path.join(out, 'index.html'), stitle, body)
    # ---- 기획 노트
    hist = sec.get('히스토리', '')
    body = f'<p class="k">SERIES NOTE</p><h1>기획 노트 — {h(stitle)}</h1>' + ''.join(f'<h2>{h(t)}</h2>' + ''.join(f'<p>{h(p)}</p>' for p in re.split(r"\n\s*\n", b)) for t, b in secs if t != '히스토리')
    per_ep_bars = bars([('EP.%02d' % e['ep'], sum(1 for _ in open(os.path.join(out, 'eps', e['slug'], 'selection.csv'), encoding='utf-8-sig')) - 1) for e in EPS][:12], '#8fae8b')
    body += f'<h2>숫자로 본 시리즈</h2><div class="g"><div class="box"><h3>문서의 시대 ({len(docs)}건)</h3>{bars(CENT)}</div><div class="box"><h3>편별 문서 수</h3>{per_ep_bars}</div></div>'
    if hist: body += '<h2>히스토리</h2><div class="tl">' + ''.join(f'<div>{h(l.lstrip("- ").strip())}</div>' for l in hist.splitlines() if l.strip()) + '</div>'
    body += '<h2>편별 큐레이터 노트 · 전달 에디팅</h2><div class="tw" tabindex="0" role="region" aria-label="표"><table><tr><th>편</th><th>전하고 싶은 것</th><th>핵심 정서</th><th>남겨 둔 질문</th></tr>' + ''.join(f'<tr><td><a href="eps/{e["slug"]}/index.html">EP.{e["ep"]:02d} {h(e["title"])}</a></td><td>{h(e["cur"].get("message", ""))}</td><td>{h(e["dv"].get("emotion", ""))}</td><td>{h(e["cur"].get("question", ""))}</td></tr>' for e in EPS) + '</table></div>'
    page(os.path.join(out, 'about.html'), '기획 노트 — ' + stitle, body)
    # ---- 홍보 가이드
    body = '<p class="k">PROMOTION</p><h1>채널별 홍보 가이드</h1><p class="lead">한 게시물에 문서 한 장·원문 한 줄, 질문으로 열고 「남겨 둔 질문」으로 닫기, 출처는 언제나, 판독은 초안이라고.</p>'
    body += '<div class="tw" tabindex="0" role="region" aria-label="표"><table><tr><th>채널</th><th>형식</th><th>쓰는 파일</th><th>요령</th></tr>' + ''.join(f'<tr><td><b>{h(a_)}</b></td><td>{h(b)}</td><td>{h(c)}</td><td>{h(d)}</td></tr>' for a_, b, c, d in ST.CHANNELS) + '</table></div>'
    body += '<h2>4주 계획</h2><div class="tw" tabindex="0" role="region" aria-label="표"><table><tr><th>주</th><th>무엇을</th></tr><tr><td>1주</td><td>1차 공개 — 릴스 · 카드뉴스 · 전시 링크</td></tr><tr><td>2주</td><td>2차 — 편별 비하인드 카드 ①②③, 「남겨 둔 질문」으로 댓글</td></tr><tr><td>3주</td><td>시리즈 — 기획 노트 카드 · 시리즈 영상 · 유튜브 묶음</td></tr><tr><td>4주</td><td>확장 — 장문 · 지역 커뮤니티 · 수업 · 전시 제안</td></tr></table></div>'
    body += '<h2>편별 채널 홍보안</h2><ul>' + ''.join(f'<li><a href="eps/{e["slug"]}/channels.md">EP.{e["ep"]:02d} {h(e["title"])}</a></li>' for e in EPS if e['has'].get('channels.md')) + '</ul>'
    page(os.path.join(out, 'promote.html'), '홍보 가이드 — ' + stitle, body)
    # ---- 활용 가이드
    body = '<p class="k">USE</p><h1>패키지 활용 가이드</h1><p class="lead">원본 사진(원재료) · 판독과 번역(손질된 재료) · 이야기와 큐레이터 노트(레시피) · 카드·영상·전시(차림 예시) — 받는 사람이 자기 자리(수업·전시·책·창작)에 맞게 바로 쓰는 묶음입니다.</p>'
    body += '<div class="g">' + ''.join(f'<div class="box"><h3>{h(a_)}</h3><p>{h(b)}</p></div>' for a_, b in USE) + '</div><h2>지킬 것</h2><div class="box"><ul>' + ''.join(f'<li>{h(x)}</li>' for x in CHECK) + '</ul></div>'
    page(os.path.join(out, 'use.html'), '활용 가이드 — ' + stitle, body)
    for fn, t, lead, body_ in AN.collections_pages(sorted(AE, key=lambda e: e['ep']), stitle):
        page(os.path.join(out, fn), f'{t} — {stitle}', f'<p class="k">COLLECTION</p><h1>{h(stitle)} — {h(t)}</h1><p class="lead">{h(lead)}</p><style>{AN.CSS}</style><div class="an">{body_}</div>', desc=lead)
    page(os.path.join(out, 'analysis.html'), '통합 분석 — ' + stitle, f'<p class="k">ANALYSIS</p><h1>{h(stitle)} — 통합 분석</h1><p class="lead">편마다 따로 보던 문서 · 노트 · 결과물을 한데 모아, 전체가 무엇을 담고 있는지 한 장에서 읽습니다.</p><style>{AN.CSS}</style>' + an_body)
    if SITE:  # 검색 엔진용 사이트 지도
        import datetime
        today = datetime.date.today().isoformat()
        urls = [SITE + f for f in ('', 'analysis.html', 'search.html', 'types.html', 'quotes.html', 'timeline.html', 'questions.html', 'review.html', 'about.html', 'promote.html', 'use.html')] + [SITE + f'eps/{e["slug"]}/{f}' for e in EPS for f in ('index.html', 'exhibit.html', 'handout.html') if e['has'].get(f)]
        open(os.path.join(out, 'sitemap.xml'), 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{h(u)}</loc><lastmod>{today}</lastmod></url>\n' for u in urls) + '</urlset>\n')
    print(f'→ {out}  편 {len(EPS)} · 문서 {len(docs)} · 시리즈 카드 {len(scards)}장\n  index.html(갤러리) · about.html(기획 노트) · promote.html · use.html · analysis.html(통합 분석) · search · types · quotes · timeline · questions.html(모아 보기) · eps/' + (' · sitemap.xml' if SITE else ''))


if __name__ == '__main__':
    main()
