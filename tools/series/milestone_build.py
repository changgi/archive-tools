# 「고문서 한 장」 200편 기념 페이지 — examples/200.html
#   analysis-data.json(숫자 · 분포) + viewer-data.json(편 · 문서 · 썸네일)을 읽어 만든다. 다시 돌려도 같은 결과.
import _paths as P
import json, html, re, os

R = P.REPO + '/examples/'
A = json.load(open(R + 'analysis-data.json', encoding='utf-8'))
V = json.load(open(R + 'viewer-data.json', encoding='utf-8'))
BASE = V['base']
EPS = [e for e in V['eps']]
esc = html.escape

def yrs(e):
    out = []
    for d in e['d']:
        m = re.match(r'(\d{4})', str(d.get('y') or ''))
        if m: out.append(int(m.group(1)))
    return out

def short(t): return t.split(' — ')[0].strip()
def epl(e): return f"EP.{e['ep']}" if e.get('ep') is not None else '기획 예시'

# ---- 주제별로 다시 보기 (제목 · 문서 유형으로 묶음, 한 편이 여러 주제에 들어갈 수 있음) ----
THEMES = [
    ('부르고 맡기다', '유지 · 고신 · 교첩 · 차첩 · 망기 · 녹패 — 나라와 고을이 사람을 쓰는 종이', r'유지|고신|교첩|차첩|망기|녹패|임명|부름|부른'),
    ('시험을 치르다', '백패 · 홍패 · 시권 — 흰 종이와 붉은 종이', r'백패|홍패|시권|과거|급제|생원|진사|문과|무과'),
    ('가족이 되다', '혼서 · 분재기 · 호적 · 계후입안 · 부인의 교지', r'혼서|혼인|분재|별급|호적|준호구|호구|계후|입후|부인|아내|정부인|숙부인|양씨|윤씨|강씨'),
    ('땅을 지키다', '소지 · 산송 · 명문 · 산림 서류', r'소지|산송|산도|명문|토지|산림|임야|선산|무덤|등장|의송'),
    ('마을과 서원', '완문 · 완의 · 절목 · 향약 · 서원과 향교의 문서', r'완문|완의|절목|향약|서원|향교|마을|동중|계안|제수'),
    ('편지와 글', '간찰 · 한글 편지 · 문집', r'편지|간찰|언간|문집|유고|글씨'),
    ('근대의 종이', '1895년 이후 — 인쇄 서식 · 청원서 · 영수증', None),
]

def theme_eps(rx):
    out = []
    for e in EPS:
        hay = e['t'] + ' ' + ' '.join((d.get('t') or '') + ' ' + (d.get('ty') or '') for d in e['d'])
        if rx is None:
            ys = yrs(e)
            if ys and max(ys) >= 1895: out.append(e)
        elif re.search(rx, hay): out.append(e)
    return out

def bars(rows, unit='건', color='#c4964a'):
    mx = max(v for _, v in rows) or 1
    return '<div class="bars">' + ''.join(
        f'<div class="bar"><span class="bl">{esc(k)}</span><span class="bt"><i style="width:{v / mx * 100:.1f}%;background:{color}"></i></span><b>{v:,}{unit}</b></div>'
        for k, v in rows) + '</div>'

S = A['reading']
span = A['span']
nums = [(A['eps'], '편'), (A['docs'], '건의 문서'), (A['colls'], '곳의 소장처'), (span[1] - span[0], f"년 ({span[0]}–{span[1]})"),
        (S['hanja'], '자 판독 한자'), (S.get('quotes_checked', 0), '곳 원문 인용')]

mosaic = []
for e in EPS:
    d0 = e['d'][0]
    ys = yrs(e)
    yr = (f"{min(ys)}" if min(ys) == max(ys) else f"{min(ys)}–{max(ys)}") if ys else ''
    mosaic.append(f'<a class="tile" href="{esc(e["f"])}/exhibit.html" title="{esc(epl(e))} {esc(e["t"])}">'
                  f'<img loading="lazy" src="{BASE}{esc(e["f"])}/thumb/01.jpg" width="{d0.get("tw", 270)}" height="{d0.get("th", 360)}" alt="">'
                  f'<span><b>{esc(epl(e))}</b>{esc(short(e["t"]))}<em>{esc(yr)}</em></span></a>')

themes = []
for name, sub, rx in THEMES:
    es = theme_eps(rx)
    links = ' '.join(f'<a href="{esc(e["f"])}/exhibit.html" title="{esc(short(e["t"]))}">{esc(epl(e))}</a>' for e in es)
    themes.append(f'<details><summary><b>{esc(name)}</b> <em>{len(es)}편</em><span>{esc(sub)}</span></summary><p class="eplist">{links}</p></details>')

ex = A.get('episodes', [])
msgs = [x for x in ex if x.get('message')]
pick = [msgs[i] for i in range(0, len(msgs), max(1, len(msgs) // 12))][:12]
voices = ''.join(f'<li><small>{esc(x["episode"])} · {esc(x["collection"])}</small>{esc(x["message"])}</li>' for x in pick)

page = f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>고문서 한 장 — 200편</title>
<meta name="description" content="「고문서 한 장」 200편 — 문서 {A['docs']}건 · 소장처 {A['colls']}곳 · {span[0]}–{span[1]}년. 한 장씩 원문으로 읽은 옛 문서 이야기를 한 페이지에 모았습니다.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%2316130f'/%3E%3Crect x='14' y='10' width='36' height='44' rx='3' fill='%23efe3c8'/%3E%3Cpath d='M21 20h22M21 28h22M21 36h16' stroke='%23c4964a' stroke-width='4' stroke-linecap='round'/%3E%3C/svg%3E">
<style>
:root{{--bg:#16130f;--pan:#1f1a14;--line:#3a3225;--gold:#c4964a;--paper:#efe6d4;--dim:#b9ad96}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--paper);font-family:'Noto Sans KR','Malgun Gothic',sans-serif;line-height:1.75}}
a{{color:var(--gold)}}main{{max-width:1180px;margin:0 auto;padding:6vh 5vw 12vh}}
.k{{color:var(--gold);letter-spacing:.18em;font-size:13px}}h1{{font-family:'Noto Serif KR',serif;font-size:clamp(34px,6vw,64px);line-height:1.2;margin:.15em 0 .3em}}
h2{{font-family:'Noto Serif KR',serif;font-size:clamp(22px,3vw,30px);margin:2.4em 0 .6em;border-top:1px solid var(--line);padding-top:1em}}
.lead{{font-size:clamp(16px,2vw,19px);color:#e8dcc4;max-width:46em}}
nav.top{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0}}nav.top a{{background:#231d15;border:1px solid #4a3e2c;border-radius:30px;padding:5px 14px;text-decoration:none;font-size:14px;color:var(--paper)}}nav.top a:hover{{border-color:var(--gold)}}
.nums{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:28px 0}}
.num{{background:var(--pan);border:1px solid var(--line);border-radius:14px;padding:16px 18px}}.num b{{display:block;font-family:'Noto Serif KR',serif;font-size:clamp(26px,3.4vw,38px);color:var(--gold);line-height:1.2}}.num span{{font-size:14px;color:var(--dim)}}
.two{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:22px}}
.card{{background:var(--pan);border:1px solid var(--line);border-radius:14px;padding:18px 20px}}.card h3{{margin:0 0 10px;font-size:16px;color:var(--gold)}}
.bars{{display:flex;flex-direction:column;gap:7px}}.bar{{display:grid;grid-template-columns:5.5em 1fr 4.8em;gap:10px;align-items:center;font-size:14px}}
.bl{{color:var(--dim);text-align:right}}.bt{{background:#2a231a;border-radius:6px;height:14px;overflow:hidden}}.bt i{{display:block;height:100%;border-radius:6px}}.bar b{{font-weight:500;font-size:13px}}
.mosaic{{display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:6px}}
.tile{{position:relative;display:block;aspect-ratio:3/4;overflow:hidden;border-radius:6px;background:#0d0c0a;text-decoration:none}}
.tile img{{width:100%;height:100%;object-fit:cover;object-position:50% 25%;display:block;opacity:.88;transition:opacity .2s,transform .3s}}
.tile span{{position:absolute;inset:auto 0 0 0;padding:16px 6px 5px;background:linear-gradient(transparent,rgba(10,9,7,.92));font-size:11px;line-height:1.35;color:var(--paper)}}
.tile span b{{display:block;color:var(--gold);font-size:11px}}.tile span em{{display:block;font-style:normal;color:var(--dim);font-size:10.5px}}
.tile:hover img{{opacity:1;transform:scale(1.04)}}
details{{background:var(--pan);border:1px solid var(--line);border-radius:12px;margin:8px 0;padding:10px 16px}}summary{{cursor:pointer;display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline}}
summary b{{font-family:'Noto Serif KR',serif;font-size:18px}}summary em{{font-style:normal;color:var(--gold);font-size:14px}}summary span{{color:var(--dim);font-size:14px}}
.eplist{{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}}.eplist a{{font-size:13px;background:#231d15;border:1px solid #4a3e2c;border-radius:20px;padding:1px 10px;text-decoration:none}}
ul.voices{{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}ul.voices li{{background:var(--pan);border-left:3px solid var(--gold);border-radius:8px;padding:12px 14px;font-size:15px;color:#e8dcc4}}ul.voices small{{display:block;color:var(--gold);font-size:12px;margin-bottom:4px}}
.note p{{color:#d9cfbb;max-width:50em}}footer{{border-top:1px solid var(--line);margin-top:4em;padding-top:1.2em;font-size:13px;color:var(--dim)}}
</style></head><body><main>
<div class="k">ARCHIVE TOOLS · 고문서 한 장</div>
<h1>200편</h1>
<p class="lead">한 편에 문서 네 장 남짓. 한국학중앙연구원 한국고문서자료관에 공개된 각 소장처의 문서를 한 장씩 원문으로 읽고, 번역하고, 해제하고, 그 종이에 적힌 문장으로 이야기를 만들었습니다. 그렇게 쌓인 200편을 이 한 페이지에 모았습니다.</p>
<nav class="top"><a href="index.html">갤러리</a><a href="viewer.html">연속 보기 · IIIF</a><a href="search.html">전체 검색</a><a href="timeline.html">전체 연표</a><a href="analysis.html">통합 분석</a><a href="types.html">문서 유형 사전</a><a href="about.html">기획 노트</a></nav>
<div class="nums">{''.join(f'<div class="num"><b>{v:,}</b><span>{esc(u)}</span></div>' for v, u in nums)}</div>
<h2>200편, 한눈에</h2>
<p class="note" style="color:var(--dim);font-size:14px">썸네일을 누르면 그 편의 전시 웹페이지가 열립니다. 이미지는 각 전시 웹페이지에 실린 것과 같습니다.</p>
<div class="mosaic">{''.join(mosaic)}</div>
<h2>무엇을 읽었나</h2>
<div class="two">
<div class="card"><h3>세기별 문서 (연대 적힌 {sum(v for _, v in A['centuries']):,}건)</h3>{bars(A['centuries'])}</div>
<div class="card"><h3>많이 읽은 문서 유형 (모두 {len(A['types'])}가지)</h3>{bars(A['types'][:10])}</div>
<div class="card"><h3>지역별 편 수</h3>{bars(A['regions'][:10], '편', '#8a9a7a')}</div>
<div class="card"><h3>소장처 종류</h3>{bars(A['kinds'], '편', '#8a9a7a')}</div>
</div>
<h2>주제별로 다시 보기</h2>
{''.join(themes)}
<h2>편마다 전하려 한 말</h2>
<ul class="voices">{voices}</ul>
<h2>만든 방법과 남겨 둔 것</h2>
<div class="note">
<p>문서 고르기 · 판독 · 번역 · 해제 · 이야기 초안은 Claude(Anthropic)가 aks-archive-harvester 도구로 만들고, 기획과 책임 편집은 Song Chang-gi가 맡았습니다. 못 읽은 글자는 □로({S.get('unknown', 0)}개), 확신하지 못한 글자는 (?)로({S.get('unsure', 0)}개) 남겼고, 문서에 없는 사실은 '확인하지 않았다'고 적었습니다.</p>
<p>판독 · 번역은 초안입니다. 원본과 대조한 사람만 검토 칸을 채우며, 지금 검토 표시는 0건입니다. 고쳐야 할 곳을 찾으시면 <a href="https://github.com/changgi/archive-tools/issues">GitHub</a> 또는 아래 연락처로 알려 주세요.</p>
<p>고문서 이미지는 한국학중앙연구원 한국고문서자료관 소장 · 제공(각 소장처 기탁)입니다. 다시 쓰려면 자료관(031-730-8873 · 8876)을 통해 소장처의 동의를 받아야 하며, 문제가 있으면 내립니다. 이 시리즈가 새로 만든 텍스트는 CC BY 4.0, 코드는 MIT입니다.</p>
</div>
<footer>엮은이 Song Chang-gi · <a href="mailto:chgsong@naver.com">chgsong@naver.com</a> · <a href="https://github.com/changgi">github.com/changgi</a> · <a href="index.html">갤러리로 돌아가기</a></footer>
</main></body></html>
'''
old = open(R + '200.html', encoding='utf-8').read() if os.path.exists(R + '200.html') else ''
if old != page: open(R + '200.html', 'w', encoding='utf-8').write(page)
print(f'■ 200편 페이지: 편 {len(EPS)}개 · 주제 {len(THEMES)}개 · {"바뀜" if old != page else "그대로"} → examples/200.html')
