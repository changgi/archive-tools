# examples/index.html 을 캐러셀 갤러리로 다시 만든다 (기존 카드 내용·뒷부분 섹션은 그대로 재사용)
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import re, json, os, html, glob, csv
R = (P.REPO + '/examples/')
src = open(R + 'index.html', encoding='utf-8').read()
if 'id="vcar"' in src or 'id="epd"' in src:                       # 재실행 대비: 원본 백업 사용
    src = open((P.DATA + '/index_before_carousel.html'), encoding='utf-8').read()
else:
    open((P.DATA + '/index_before_carousel.html'), 'w', encoding='utf-8').write(src)

head = src[:src.index('</style>')]
top = src[src.index('<header>'):src.index('<h2>홍보 영상</h2>')]
tail = src[src.index('  <h2>여러 소장처 비교'):]
caps = json.load(open((P.DATA + '/captions.json'), encoding='utf-8'))

# ---- 기존 예시 카드 파싱 ----
arts = re.findall(r'<article class="ex">(.*?)</article>', src, re.S)
EX = []
for a in arts:
    tag = re.search(r'<span class="tag">(.*?)</span>', a).group(1)
    h3 = re.search(r'<h3>(.*?)</h3>', a).group(1)
    who = re.search(r'<div class="who">(.*?)</div>', a).group(1)
    desc = re.search(r'</div>\s*<div>(.*?)</div>', a, re.S).group(1).strip()
    links = re.search(r'<div class="links">(.*?)</div>', a, re.S).group(1)
    folder = re.search(r'href="([^"/]+)/exhibit\.html"', a).group(1)
    ep = re.search(r'EP\.(\d+)', tag)
    EX.append(dict(tag=tag, h3=h3, who=who, desc=desc, links=re.sub(r'\s+', ' ', links).strip(), folder=folder, ep=int(ep.group(1)) if ep else None))
KIND = {'royal-letters': '박물관', 'unjoru': '문중', 'jeongon': '문중', 'gujora': '마을', 'hagari': '마을', 'yongmunsa': '사찰',
        'deokcheon': '서원', 'yunjeung': '문중', 'byeongsan': '서원', 'anjeongbok': '문중', 'jikjisa-temple': '사찰',
        'susanri-village': '마을', 'namgye-seowon': '서원', 'myeongseong-letters': '박물관'}
for e in EX:
    e['kind'] = KIND.get(e['folder'], '문중')
assert len(EX) == 17, len(EX)
GHT = 'https://github.com/changgi/archive-tools/tree/main/examples/'
for jp in sorted(glob.glob((P.DATA + '/new/*.json'))) + sorted(glob.glob((P.DATA + '/new2/*.json'))) + sorted(glob.glob((P.DATA + '/new3/*.json'))) + sorted(glob.glob((P.DATA + '/new4/*.json'))):
    if not os.path.exists(R + json.load(open(jp, encoding='utf-8'))['meta']['folder'] + '/selection.csv'): continue
    J = json.load(open(jp, encoding='utf-8')); M = J['meta']; f = M['folder']
    sel = list(csv.DictReader(open(R + f + '/selection.csv', encoding='utf-8-sig')))
    ys = [int(r['연도'][:4]) for r in sel if r['연도'][:4].isdigit()] or [0]
    EX.append(dict(tag=f"EP.{M['ep']} · {M['kind']} · 원문 읽기", h3=M['title'], who=f"{M['coll']} · " + ((f"{min(ys)}–{max(ys)} · " if min(ys) != max(ys) else f"{min(ys)} · ") if ys[0] else '') + f"{len(sel)}점", desc=M['lead'],
                   links=f'<a href="{f}/exhibit.html">전시 웹페이지</a><a href="{f}/handout.html">수업 활동지</a><a href="{GHT}{f}/cards">카드뉴스</a><a href="{f}/sns.txt">SNS 글</a><a href="{f}/selection.csv">원문·번역 표</a>',
                   folder=f, ep=M['ep'], kind=M['kind']))

def dur(p):
    import subprocess
    return round(float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', P.media_file(os.path.basename(p)) if p.endswith('.mp4') else R + p])))

# ---- 영상 슬라이드 ----
V = [dict(ep=1, id='promo-reel', title='흩어진 기록을, 다시 이야기로', sub='임명장 한 장에서 시작해 ① 수집부터 ⑤ 패키징까지', group='intro',
          reel='media/promo-reel.mp4', rposter='media/promo-reel-poster.jpg', vtt='media/promo-reel.ko.vtt', srt='media/promo-reel.ko.srt'),
     dict(ep=2, id='promo-reel-ep2', title='만든 것 보기', sub='말 한마디로 만든 전시·카드뉴스·활동지, 에디팅 전후, 두 집안 비교', group='intro',
          reel='media/promo-reel-ep2.mp4', rposter='media/promo-reel-ep2-poster.jpg', vtt='media/promo-reel-ep2.ko.vtt', srt='media/promo-reel-ep2.ko.srt')]
for k, c in sorted(caps.items(), key=lambda x: x[1]['n']):
    ex = next((e for e in EX if e['folder'] == c['folder']), None)
    if not ex: continue
    if not os.path.exists(P.media_file(f'{k}_reel.mp4')): continue
    V.append(dict(ep=c['n'], id=k, title=c['title'], sub=f"{ex['who']}", group='set' if c['n'] <= 6 else ('story' if c['n'] <= 16 else ('read' if c['n'] <= 26 else ('read2' if c['n'] <= 50 else ('read3' if c['n'] <= 100 else 'read4')))), kind=ex['kind'],
                  folder=c['folder'], reel=f'media/{k}_reel.mp4', rposter=f'media/{k}_reel-poster.jpg',
                  wide=f'media/{k}_wide.mp4', wposter=f'media/{k}_wide-poster.jpg', vtt=f'media/{k}.ko.vtt', srt=f'media/{k}.ko.srt', caption=c['caption']))
for v in V:
    for f in ('reel', 'rposter', 'vtt', 'wide', 'wposter'):
        if f in v: assert os.path.exists(R + v[f]) or os.path.exists(P.media_file(os.path.basename(v[f]))), v[f]  # 영상은 archive-tools-next에 있을 수 있음
    v['dr'] = dur(v['reel']); v['dw'] = dur(v['wide']) if 'wide' in v else None

# 카드뉴스 데이터
import csv
EDITS = []
for e in sorted([e for e in EX if not e['ep']], key=lambda e: e['folder']) + sorted([e for e in EX if e['ep']], key=lambda e: e['ep']):
    rows = list(csv.DictReader(open(R + e['folder'] + '/selection.csv', encoding='utf-8-sig')))
    out = []
    for r in rows:
        who = ', '.join(x.strip() for x in r['인물'].split(';')[:2] if x.strip())
        before = (f"{r['연도']}년 " if r['연도'] else '') + (who + '의 ' if who else '') + r['문서유형'] + (f" — {r['유형설명']}." if r['유형설명'] else '.')
        out.append(dict(n=r['순서'], d=r['문서명'], b=before, a=r['이야기'] or r['캡션'], h=r.get('해제', ''), y=r.get('요약', '')))
    EDITS.append(dict(f=e['folder'], t=(f"EP.{e['ep']} " if e['ep'] else '') + re.sub('<.*?>', '', e['h3']), r=out))
CARDS = []
order = [e for e in EX if not e['ep']] + sorted([e for e in EX if e['ep']], key=lambda e: e['ep'])
for e in order:
    fs = sorted(f for f in os.listdir(R + e['folder'] + '/cards') if f.endswith('.jpg'))
    fs = [f for f in fs if f.startswith('00')] + [f for f in fs if not f.startswith(('00', '99'))] + [f for f in fs if f.startswith('99')]
    CARDS.append(dict(f=e['folder'], t=(f"EP.{e['ep']} " if e['ep'] else '') + re.sub('<.*?>', '', e['h3']), c=fs))


# ---------------------------------------------------------------- 인터랙티브 갤러리 (에피소드 격자 + 상세 보기 창)
GHB = 'https://github.com/changgi/archive-tools/blob/main/examples/'
GROUPS = [('intro', '소개'), ('set', '예시 EP.03–06'), ('story', '이야기 EP.07–16'), ('read', '원문으로 읽기 EP.17–26'), ('read2', '원문으로 읽기 EP.27–50'), ('read3', '원문으로 읽기 EP.51–100'), ('read4', '원문으로 읽기 EP.101–')]
EDIT_BY = {e['f']: e['r'] for e in EDITS}
CARD_BY = {c['f']: c['c'] for c in CARDS}
VBY = {v['ep']: v for v in V}
ITEMS = []
for v in V:
    if v['group'] == 'intro':
        ITEMS.append(dict(key=f"ep{v['ep']}", ep=v['ep'], t=v['title'], k='소개', who=v['sub'], d=v['sub'], g='intro', cover=v['rposter'], v=v))
for e in order:
    v = VBY.get(e['ep']) if e['ep'] else None
    g = v['group'] if v else ('read4' if (e['ep'] or 0) > 100 else 'read3' if (e['ep'] or 0) > 50 else 'read2' if (e['ep'] or 0) > 26 else ('read' if (e['ep'] or 0) > 16 else 'set'))
    ITEMS.append(dict(key=f"ep{e['ep']}" if e['ep'] else e['folder'], ep=e['ep'], t=re.sub('<.*?>', '', e['h3']), k=e['kind'], who=re.sub('<.*?>', '', e['who']),
                      d=re.sub('<.*?>', '', e['desc']), g=g if e['ep'] else 'base', f=e['folder'], cover=f"{e['folder']}/cards/" + next((c for c in CARD_BY.get(e['folder'], []) if not c.startswith(('00', '99'))), '00_표지.jpg'), v=v,
                      links=e['links'], cards=CARD_BY.get(e['folder'], []), edits=EDIT_BY.get(e['folder'], [])))
def slim(it):
    v = it.pop('v')
    if v:
        it.update(reel=v['reel'], rp=v['rposter'], vtt=v['vtt'], srt=v['srt'], dr=v['dr'])
        if 'wide' in v: it.update(wide=v['wide'], wp=v['wposter'], dw=v['dw'])
        if 'caption' in v: it['cap'] = v['caption']
        it['promo'] = f"{GHB}{it['f']}/promo.md" if it.get('f') else ''
    return it
ITEMS = [slim(i) for i in ITEMS]
CNJ = json.load(open((P.DATA + '/curator.json'), encoding='utf-8')) if os.path.exists((P.DATA + '/curator.json')) else {}
for i in ITEMS:
    if i.get('f') in CNJ: i['cn'] = CNJ[i['f']]
DVJ = json.load(open((P.DATA + '/delivery.json'), encoding='utf-8')) if os.path.exists((P.DATA + '/delivery.json')) else {}
for i in ITEMS:
    if i.get('f') in DVJ: i['dv'] = DVJ[i['f']]
NV = sum(1 for i in ITEMS if i.get('reel'))
NCOLL = len({i['who'].split(' · ')[0] for i in ITEMS if i.get('f') and not i['who'].startswith('같은')})
KINDS = ['문중', '사찰', '마을', '서원', '향교', '박물관', '소개']
kcount = {k: sum(1 for i in ITEMS if i['k'] == k) for k in KINDS}
gcount = {g: sum(1 for i in ITEMS if i['g'] == g) for g, _ in GROUPS}

CSS = '''
html{scroll-behavior:smooth}
.topnav{position:sticky;top:0;z-index:20;background:rgba(22,19,15,.94);backdrop-filter:blur(8px);border-bottom:1px solid #3a3225;padding:10px 7vw;display:flex;gap:6px 18px;align-items:center;flex-wrap:wrap}
.topnav b{color:var(--gold);font-size:14px;letter-spacing:.08em;margin-right:6px}
.topnav a{color:#d5cab4;text-decoration:none;font-size:15px;padding:4px 2px;border-bottom:2px solid transparent}.topnav a:hover,.topnav a.on{color:var(--paper);border-color:var(--gold)}
.stats{display:flex;flex-wrap:wrap;gap:12px;margin:26px 0 6px}
.stat{background:#1f1a14;border:1px solid #3a3225;border-radius:14px;padding:12px 18px;min-width:120px}.stat b{display:block;font-size:28px;color:var(--gold);font-family:'Noto Serif KR',serif;line-height:1.2}.stat span{font-size:13.5px;color:var(--dim)}
.feat{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:26px;align-items:center;background:#1f1a14;border:1px solid #3a3225;border-radius:18px;padding:22px;margin-top:10px}
.feat video{width:100%;aspect-ratio:16/9;background:#000;border-radius:12px;display:block}
.feat h3{font-family:'Noto Serif KR',serif;font-size:26px;margin:.2em 0}.feat p{color:#d5cab4;margin:.4em 0 1em}
@media (max-width:820px){.feat{grid-template-columns:1fr}}
.tools{position:sticky;top:49px;z-index:15;background:rgba(22,19,15,.96);backdrop-filter:blur(8px);padding:12px 0 10px;border-bottom:1px solid #2c251b;display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center}
.tools input[type=search]{flex:1 1 240px;min-width:200px;background:#1f1a14;border:1px solid #4a3e2c;border-radius:30px;color:var(--paper);font:inherit;font-size:15px;padding:9px 18px}
.tools input[type=search]:focus{outline:none;border-color:var(--gold)}
.tools select{background:#1f1a14;border:1px solid #4a3e2c;border-radius:30px;color:var(--paper);font:inherit;font-size:14px;padding:8px 14px}
.chips{display:flex;gap:7px;flex-wrap:wrap}
.chip{background:#231d15;border:1px solid #4a3e2c;color:var(--paper);border-radius:30px;padding:6px 14px;font:inherit;font-size:14px;cursor:pointer;white-space:nowrap}
.chip small{opacity:.8;margin-left:4px}.chip[aria-pressed=true] small{opacity:1}.chip[aria-pressed=true]{background:var(--gold);border-color:var(--gold);color:var(--ink);font-weight:700}
.chip:disabled{opacity:.35;cursor:default}
.count{font-size:14px;color:var(--dim)}
.eps{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:20px;margin-top:18px}
.ep{background:#1f1a14;border:1px solid #3a3225;border-radius:14px;overflow:hidden;cursor:pointer;display:flex;flex-direction:column;text-align:left;font:inherit;color:inherit;padding:0;transition:transform .15s,border-color .15s}
.ep:hover,.ep:focus-visible{transform:translateY(-3px);border-color:var(--gold);outline:none}
.ep .im{position:relative;aspect-ratio:4/3;background:#0d0c0a;overflow:hidden}.ep img{width:100%;height:100%;object-fit:cover;object-position:50% 0%;display:block;transition:transform .4s}.ep:hover img{transform:scale(1.04)}
.ep .badge{position:absolute;left:10px;top:10px;background:var(--gold);color:var(--ink);font-weight:800;font-size:12.5px;border-radius:20px;padding:2px 10px}
.ep .kind{position:absolute;right:10px;top:10px;background:rgba(14,12,9,.8);color:#e8dcc4;font-size:12px;border-radius:20px;padding:2px 9px;border:1px solid #4a3e2c}
.ep .pl{position:absolute;right:10px;bottom:10px;width:40px;height:40px;border-radius:50%;background:rgba(196,150,74,.95);color:var(--ink);display:grid;place-items:center;font-size:16px}
.ep .tx{padding:12px 14px 16px;display:flex;flex-direction:column;gap:4px}.ep .tx b{font-size:16.5px;line-height:1.4}.ep .tx span{font-size:13px;color:var(--dim);line-height:1.5}
.empty{color:var(--dim);padding:40px 0;text-align:center}
/* 전달 에디팅 */
.dvh{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;margin:6px 0 14px}.dve{background:var(--gold);color:var(--ink);font-weight:800;border-radius:30px;padding:3px 14px}.dvh span:last-child{font-family:'Noto Serif KR',serif;font-size:18px}
.dvba{display:grid;grid-template-columns:1fr 1fr;gap:12px}.dvba>div{border-radius:12px;padding:12px 14px;border:1px solid #3a3225}.dvba .b0{background:#1a1712;color:var(--dim)}.dvba .b1{background:#2a2117;border-color:var(--gold)}.dvba b{font-size:13.5px;color:var(--gold)}.dvba p{margin:4px 0 0;font-size:15px;line-height:1.75}
.dvt{color:var(--gold);margin:18px 0 8px;font-size:14px}.dvf{display:flex;gap:8px;align-items:stretch;overflow-x:auto;padding-bottom:6px}.dvf i{align-self:center;color:var(--gold);font-style:normal}
.dvs{flex:1 1 0;min-width:190px;background:#1f1a14;border:1px solid #3a3225;border-top:3px solid var(--gold);border-radius:12px;padding:10px 12px}.dvs small{color:var(--gold);font-weight:800}.dvs b{display:block}.dvs p{margin:4px 0 0;font-size:14px;color:#e2d7c1;line-height:1.65}
.dvg{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-top:12px}
@media (max-width:760px){.dvba{grid-template-columns:1fr}}
/* 큐레이터 노트 */
.cnq{font-family:'Noto Serif KR',serif;font-size:clamp(18px,2.2vw,22px);line-height:1.7;border-left:4px solid var(--gold);margin:0 0 18px;padding:4px 0 4px 16px;color:var(--paper)}
.cng{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.cnb{background:#1f1a14;border:1px solid #3a3225;border-radius:12px;padding:12px 14px}.cnb b{color:var(--gold);font-size:13.5px}.cnb p{margin:4px 0 0;color:#e2d7c1;font-size:15px;line-height:1.7}
.bcs{display:flex;gap:12px;overflow-x:auto;margin:0 0 16px}.bcs img{height:min(46vh,420px);border-radius:10px;border:1px solid #3a3225;cursor:zoom-in}
.cnf{margin-top:14px;color:var(--dim);font-size:13.5px}.cnf b{color:var(--gold);margin-right:6px}
.sbh{display:flex;gap:16px;overflow-x:auto}.sbh figure{margin:0;flex:none;width:min(260px,70vw)}.sbh video{width:100%;aspect-ratio:9/16;background:#000;border-radius:12px}.sbh figcaption{font-size:14px;color:#d5cab4;margin-top:6px}
.why{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:22px;background:#1f1a14;border:1px solid #3a3225;border-radius:18px;padding:22px 24px;margin-top:10px}.why p{color:#d5cab4;margin:.3em 0 .8em}.why ul{margin:0;padding-left:18px;color:#d5cab4}.why li{margin:4px 0}
@media (max-width:820px){.why{grid-template-columns:1fr}}
/* 결과물 한눈에 보기 */
.outs{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;margin-top:14px}
.out{background:#1f1a14;border:1px solid #3a3225;border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.out .ic{font-size:24px;line-height:1}.out b{font-size:16px}.out p{margin:0;font-size:13.5px;color:var(--dim);line-height:1.55;flex:1}
.out .row{margin-top:4px}.out .btn{font-size:13px;padding:5px 10px}
.epw{display:flex;flex-direction:column;background:#1f1a14;border:1px solid #3a3225;border-radius:14px;overflow:hidden;transition:transform .15s,border-color .15s}
.epw:hover,.epw:focus-within{transform:translateY(-3px);border-color:var(--gold)}
.epw .ep{border:0;border-radius:0;background:none}.epw .ep:hover,.epw .ep:focus-visible{transform:none}
.ql{display:flex;flex-wrap:wrap;gap:5px;padding:0 12px 12px;margin-top:-6px}
.ql a{font-size:12px;color:#d5cab4;text-decoration:none;border:1px solid #4a3e2c;border-radius:20px;padding:2px 9px;background:#231d15}.ql a:hover{border-color:var(--gold);color:var(--paper)}
details.all{margin-top:18px;border:1px solid #3a3225;border-radius:14px;background:#1b1712}
details.all>summary{cursor:pointer;padding:12px 16px;font-weight:700;color:var(--gold)}
.allwrap{overflow-x:auto;padding:0 12px 14px}.allwrap input{width:100%;max-width:420px;margin:0 0 10px;background:#1f1a14;border:1px solid #4a3e2c;border-radius:30px;color:var(--paper);font:inherit;font-size:14px;padding:7px 14px}
table.all{min-width:760px;font-size:13.5px;border-collapse:collapse;width:100%}table.all td,table.all th{padding:6px 8px;border-bottom:1px solid #2c251b;text-align:left;vertical-align:top}table.all a{color:#e8dcc4;margin-right:8px;white-space:nowrap}
mark{background:rgba(196,150,74,.35);color:inherit;border-radius:3px}
/* 상세 보기 창 */
dialog#epd{width:min(1180px,96vw);height:min(92vh,980px);max-height:none;padding:0;border:1px solid #4a3e2c;border-radius:18px;background:#16130f;color:var(--paper)}
dialog#epd::backdrop{background:rgba(5,4,3,.78)}
.dh{display:flex;gap:12px;align-items:flex-start;padding:16px 20px 10px;border-bottom:1px solid #2c251b}
.dh .tt{flex:1;min-width:0}.dh .tt small{color:var(--gold);font-weight:700;font-size:13px}.dh h3{margin:2px 0;font-family:'Noto Serif KR',serif;font-size:clamp(19px,2.4vw,26px);line-height:1.35}.dh .tt div{color:var(--dim);font-size:13.5px}
.ib{background:#231d15;border:1px solid #4a3e2c;color:var(--paper);border-radius:10px;min-width:40px;height:40px;font-size:18px;cursor:pointer;font-family:inherit}.ib:hover{border-color:var(--gold)}.ib:disabled{opacity:.3}
.dlg{display:flex;flex-direction:column;height:100%}
.tabs{display:flex;gap:4px;padding:8px 20px 0;overflow-x:auto;border-bottom:1px solid #2c251b;scrollbar-width:none}
.tabs button{background:none;border:0;border-bottom:3px solid transparent;color:#d5cab4;font:inherit;font-size:15px;padding:8px 12px;cursor:pointer;white-space:nowrap}
.tabs button[aria-selected=true]{color:var(--paper);border-color:var(--gold);font-weight:700}.tabs button:disabled{opacity:.3;cursor:default}
.pane{flex:1;overflow:auto;padding:18px 20px 24px}
.vwrap{display:flex;gap:22px;align-items:flex-start;flex-wrap:wrap}
.vbox{background:#000;border-radius:12px;overflow:hidden;flex:none}
.vbox video{display:block;width:100%;height:100%;background:#000}
.vbox.reel{width:min(360px,100%);aspect-ratio:9/16;max-height:72vh}.vbox.wide{width:min(760px,100%);aspect-ratio:16/9}
.vside{flex:1;min-width:240px;display:flex;flex-direction:column;gap:12px}
.vside .lead{color:#d5cab4}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.btn{background:#2c251b;border:1px solid #4a3e2c;border-radius:8px;padding:6px 12px;text-decoration:none;font-size:14px;color:var(--paper);font-family:inherit;cursor:pointer}
.btn:hover{border-color:var(--gold)}.btn.pri{background:var(--gold);color:var(--ink);border-color:var(--gold);font-weight:700}.btn.done{background:var(--gold);color:var(--ink)}
label.ck{font-size:14px;color:#d5cab4;display:flex;gap:6px;align-items:center;cursor:pointer}
.capbox{white-space:pre-wrap;background:#0d0c0a;border:1px solid #3a3225;border-radius:10px;padding:12px 14px;font-size:14px;color:#e8dcc4;max-height:240px;overflow:auto}
.docs{display:flex;flex-direction:column;gap:12px}
.doc{border:1px solid #3a3225;border-radius:12px;background:#1b1712}
.doc>summary{cursor:pointer;padding:12px 16px;display:flex;gap:12px;align-items:baseline;list-style:none}.doc>summary::-webkit-details-marker{display:none}
.doc>summary .n{color:var(--gold);font-weight:800}.doc>summary .y{color:var(--gold);font-size:13px;white-space:nowrap}.doc>summary b{flex:1;font-weight:600}
.doc>summary::after{content:'＋';color:var(--gold)}.doc[open]>summary::after{content:'－'}
.dbody{display:grid;grid-template-columns:minmax(0,300px) minmax(0,1fr);gap:18px;padding:0 16px 16px}
.dbody img{width:100%;border-radius:8px;border:1px solid #3a3225;cursor:zoom-in;background:#0d0c0a}
.dbody .story{font-family:'Noto Serif KR',serif;font-size:17px;line-height:1.8;color:var(--paper);border-left:3px solid var(--gold);padding-left:12px;margin:0 0 12px}
.dbody h4{margin:14px 0 4px;color:var(--gold);font-size:14px}.dbody p{margin:0;color:#d5cab4;font-size:15px}
.dbody pre{white-space:pre-wrap;font-family:'Noto Serif KR',serif;font-size:16px;line-height:1.9;margin:0}
.seg{display:inline-flex;border:1px solid #4a3e2c;border-radius:30px;overflow:hidden}.seg button{background:#1f1a14;border:0;color:#d5cab4;font:inherit;font-size:13.5px;padding:5px 12px;cursor:pointer}.seg button[aria-pressed=true]{background:var(--gold);color:var(--ink);font-weight:700}
@media (max-width:760px){.dbody{grid-template-columns:1fr}dialog#epd{width:100vw;height:100dvh;border-radius:0;max-width:100vw}}
.cdv{position:relative}
.cdtrack{display:flex;gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:10px;scroll-behavior:smooth}
.cdtrack img{flex:none;width:min(480px,88%,calc(62vh * .8));height:auto;aspect-ratio:4/5;object-fit:cover;border-radius:10px;border:1px solid #3a3225;scroll-snap-align:start;background:#1f1a14}
.cdv .ib{position:absolute;top:45%}.cdv .ib.l{left:6px}.cdv .ib.r{right:6px}
table.ed{min-width:820px;font-size:14px}table.ed td{line-height:1.6}table.ed th{width:auto;background:#1f1a14}
.edwrap{overflow-x:auto;border:1px solid #3a3225;border-radius:12px}
.zoom{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;z-index:99;cursor:zoom-out;align-items:center;justify-content:center}.zoom.on{display:flex}.zoom img{max-width:96vw;max-height:94vh}
.kbd{font-size:12.5px;color:var(--dim)}
.trs{margin-top:12px}.trs summary{cursor:pointer;color:var(--gold);font-size:14px}.trx{max-height:260px;overflow:auto;background:#16130f;border:1px solid #3a3225;border-radius:10px;padding:8px 12px;margin-top:6px}.trx p{margin:4px 0;font-size:14px;color:#e8dcc4}
.map{margin-top:18px;background:#1b1712;border:1px solid #3a3225;border-radius:18px;padding:20px 22px}
.map h2{margin-top:0}.map .lead{color:#d5cab4;margin:0 0 14px}
.who{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:18px}
.who div{background:#231d16;border:1px solid #4a3f2e;border-radius:14px;padding:12px 14px}.who b{display:block;color:var(--gold);margin-bottom:6px}
.who a{display:inline-block;margin:2px 8px 2px 0;color:var(--paper);font-size:14px;text-decoration:none;border-bottom:1px solid #6b5a3e}.who a:hover{border-color:var(--gold)}
.nums{background:#231d16;border:1px solid #6b5a3e;border-radius:14px;padding:12px 16px;margin-bottom:14px}.nums .nh{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}.nums .nh b{color:var(--gold)}.nums ul{margin:8px 0 0;padding-left:20px}.nums li{color:#e8dcc4;font-size:14.5px;margin:3px 0}
.mg{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
.mg section{background:#1f1a14;border:1px solid #3a3225;border-radius:14px;padding:12px 14px}.mg h3{margin:0 0 8px;font-size:15.5px;color:var(--paper)}
.mg ul{list-style:none;margin:0;padding:0}.mg li{padding:5px 0;border-top:1px dashed #3a3225;font-size:14px;line-height:1.45}.mg li:first-child{border-top:0}
.lk{background:none;border:0;padding:0;margin:2px 8px 2px 0;font:inherit;font-size:14px;font-weight:700;color:var(--paper);cursor:pointer;text-align:left;border-bottom:1px solid #6b5a3e}.lk:hover{color:var(--gold);border-color:var(--gold)}.who .lk{font-weight:400}
.mg li a{color:var(--paper);font-weight:700;text-decoration:none}.mg li a:hover{color:var(--gold)}.mg li em{font-style:normal;color:var(--gold);font-weight:700;margin-left:4px}.mg li span{display:block;color:var(--dim);font-size:12.8px}
@media (max-width:760px){.topnav{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;gap:16px}.topnav b{display:none}.topnav a{white-space:nowrap}.tools{position:static}.stat{min-width:0;flex:1 1 40%}}
@media (prefers-reduced-motion:reduce){html,.cdtrack{scroll-behavior:auto}.ep,.ep img{transition:none}}
'''
head2 = head.replace('.grid{', '.grid0{').rstrip() + CSS
latest = max((i for i in ITEMS if i.get('wide')), key=lambda i: i['ep'])
e_ = html.escape
nav = '''<nav class="topnav" aria-label="바로 가기"><b>ARCHIVE TOOLS</b><a href="#map">한눈에 보기</a><a href="search.html">전체 검색</a><a href="analysis.html">통합 분석</a><a href="#why">만든 이유</a><a href="#series">비하인드</a><a href="#outputs">결과물 바로가기</a><a href="#browse">에피소드</a><a href="#compare">소장처 비교</a><a href="#try">직접 해 보기</a><a href="tutorial/site/index.html">따라하기 예제</a><a href="about.html">기획 노트</a><a href="promote.html">홍보 가이드</a><a href="use.html">활용 가이드</a><a href="https://github.com/changgi/archive-tools">GitHub</a><a href="en.html" lang="en" hreflang="en">English</a></nav>'''
NEP = len([i for i in ITEMS if i.get('f')]); NDOC = sum(len(i.get('edits', [])) for i in ITEMS); NCARD = sum(len(i.get('cards', [])) for i in ITEMS)
NBH = len(glob.glob(R + '*/behind/*.jpg'))
NREV = sum(1 for f in glob.glob(R + '*/selection.csv') for r in csv.DictReader(open(f, encoding='utf-8-sig')) if (r.get('검토') or '').strip())
import sys as _s; _s.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts')); import analysis as _AN
NPEOPLE = len({p for f in glob.glob(R + '*/selection.csv') for r in csv.DictReader(open(f, encoding='utf-8-sig')) for p in _AN.persons_of(r)})
NDATED = sum(n for _, n in json.load(open(R + 'analysis-data.json', encoding='utf-8')).get('centuries', [])) if os.path.exists(R + 'analysis-data.json') else ''
ANS = json.load(open((P.DATA + '/analysis_summary.json'), encoding='utf-8')) if os.path.exists((P.DATA + '/analysis_summary.json')) else {'insights': [], 'docs': ''}
body = f'''{nav}
{top}
  <div class="stats">
    <div class="stat"><b>{len([i for i in ITEMS if i.get('f')])}</b><span>예시</span></div>
    <div class="stat"><b>{NV}</b><span>영상(세로·가로)</span></div>
    <div class="stat"><b>{sum(len(i.get('edits', [])) for i in ITEMS)}</b><span>읽은 문서</span></div>
    <div class="stat"><b>{sum(len(i.get('cards', [])) for i in ITEMS)}</b><span>카드뉴스</span></div>
    <div class="stat"><b>{NCOLL}</b><span>소장처</span></div>
  </div>


  <section class="map" id="map" aria-labelledby="map-h">
  <h2 id="map-h">처음 오셨나요? — 여기 있는 것 전부, 한눈에</h2>
  <p class="lead">한국고문서자료관의 고문서를 한 장씩 원문으로 읽고, 영상 · 전시 · 활동지 · 카드뉴스 · 데이터로 만든 시리즈와, 그것을 누구나 만들 수 있게 한 도구(Claude 플러그인)가 있습니다. 하려는 일에 맞는 곳부터 여세요.</p>
  <div class="who">
    <div><b>👀 그냥 구경하러 왔어요</b><a href="#new">새로 나온 편</a><a href="#browse">{NEP}편 둘러보기</a><a href="#series">1분 소개 릴스</a></div>
    <div><b>🧑‍🏫 수업에 쓰고 싶어요</b><a href="{latest['f']}/handout.html" target="_blank" rel="noopener">활동지 예시</a><button class="lk" type="button" data-open="{latest['key']}" data-tab="r">원문 · 번역 읽기</button><a href="questions.html">질문 카드(인쇄용)</a><a href="use.html">활용 가이드</a></div>
    <div><b>🏛️ 전시 · 홍보를 맡았어요</b><a href="{latest['f']}/exhibit.html" target="_blank" rel="noopener">전시 웹페이지</a><a href="promote.html">채널별 홍보 가이드</a><button class="lk" type="button" data-open="{latest['key']}" data-tab="d">전달 에디팅</button></div>
    <div><b>🛠️ 직접 만들고 싶어요</b><a href="tutorial/site/index.html">따라하기 예제</a><a href="https://github.com/changgi/archive-tools/blob/main/examples/tutorial/README.md" target="_blank" rel="noopener">단계별 안내</a><a href="#try">플러그인 설치</a></div>
  </div>
  <div class="nums"><div class="nh"><b>📊 숫자로 본 전체</b><a class="btn pri" href="analysis.html">통합 분석 보기 — 시대 · 유형 · 지역 · 정서 · 판독 · 인용 · 질문</a></div><ul>{''.join(f'<li>{x}</li>' for x in ANS['insights'][:4])}</ul></div>
  <div class="mg">
    <section><h3>🎬 보기</h3><ul>
      <li><a href="#browse">에피소드 「고문서 한 장」</a><em>{NEP}편</em><span>소장처 {NCOLL}곳 · 문중 · 서원 · 향교 · 사찰 · 마을 · 제주</span></li>
      <li><a href="#browse">릴스 · 가로 영상</a><em>{NV}개</em><span>한국어 자막 포함 · 편마다 세로 9:16과 가로 16:9</span></li>
      <li><a href="#series">시리즈 비하인드 릴스</a><em>3편</em><span>왜 만들었나 · 걸어온 길 · 만들며 있었던 일</span></li>
    </ul></section>
    <section><h3>📜 읽기</h3><ul>
      <li><button class="lk" type="button" data-open="{latest['key']}" data-tab="r">원문 전문 판독 · 번역 · 해제 · 요약</button><em>{NDOC}건</em><span>한자 위 한글 독음, □ 못 읽은 글자 · (?) 불확실 표시</span></li>
      <li><a href="search.html">전체 검색</a><em>{ANS['docs']}건</em><span>판독 · 번역 · 해제 · 이야기 전문에서 낱말 · 한자 하나로 (예: 乘馹 · 노비 · 편지)</span></li>
      <li><a href="types.html">문서 유형 사전</a><span>고신 · 홍패 · 준호구 · 명문 … 문서마다 읽는 법 · 건수 · 시대 · 예</span></li>
      <li><a href="quotes.html">종이에 적힌 문장들</a><em>{ANS.get('quotes', '')}곳</em><span>이야기에 인용한 "현대어(原文)" 전체 — 낱말 · 한자로 찾기</span></li>
      <li><a href="timeline.html">전체 연표</a><em>{NDATED}건</em><span>{ANS['span'][0] if ANS.get('span') else ''}–{ANS['span'][1] if ANS.get('span') else ''}년의 문서를 연도순으로 · 편과 원본으로 바로</span></li>
      <li><a href="people.html">인물 찾아보기</a><em>{NPEOPLE}명</em><span>문서에 나온 이름을 가나다순으로 — 사람마다 나온 문서 · 편 · 원본, 여러 편에 걸친 인물</span></li>
      <li><button class="lk" type="button" data-open="{latest['key']}" data-tab="e">문구 에디팅 전후</button><span>자동 초안 → 원문을 읽고 다듬은 "현대어(原文)" 이야기</span></li>
      <li><button class="lk" type="button" data-open="{latest['key']}" data-tab="d">전달 에디팅</button><span>정서 · 열기→절정→여운 · 물질 · 통로 — 같은 기록이 마음에 남게</span></li>
    </ul></section>
    <section><h3>📦 받아 쓰기</h3><ul>
      <li><a href="#alltable" class="opent">전체 결과물 표</a><em>{NEP}편</em><span>편마다 영상 · 전시 · 활동지 · 카드 · CSV · 홍보 글 바로 가기</span></li>
      <li><a href="{latest['f']}/exhibit.html" target="_blank" rel="noopener">전시 웹페이지</a> · <a href="{latest['f']}/handout.html" target="_blank" rel="noopener">수업 활동지</a><span>인쇄하면 전시 패널 · A4 활동지</span></li>
      <li><button class="lk" type="button" data-open="{latest['key']}" data-tab="c">카드뉴스</button><em>{NCARD}장</em><span>1080×1350 · SNS에 바로</span></li>
      <li><a href="data.zip" download>전체 데이터 묶음 (ZIP)</a><span>{NEP}편의 판독 · 번역 · 해제 · 노트 · 분석 집계 — 이미지 없이 0.6MB · 텍스트 <a href="https://github.com/changgi/archive-tools/blob/main/LICENSE-CONTENT.md">CC BY 4.0</a></span></li>
      <li><a href="records.jsonl" download>기록 꾸러미 목록 (JSONL)</a><em>{NEP}편</em><span>편마다 맥락 · 출처 · 파생물 · SHA-256 고정값 · 검증 · 검토 · 작업 이력 — <a href="records-dc.csv" download>Dublin Core CSV</a> · 편 폴더의 record.json · <a href="https://github.com/changgi/archive-tools/blob/main/plugins/aks-archive-harvester/skills/aks-archive-harvester/references/records.md" target="_blank" rel="noopener">설명</a></span></li>
      <li><a href="{latest['f']}/selection.csv" download>원문 · 번역 표 (CSV)</a><span>문서명 · 연도 · 판독 · 번역 · 해제 · 원본 뷰어 링크 — 연구 · 데이터 수업용</span></li>
    </ul></section>
    <section><h3>✍️ 알기 — 기획과 비하인드</h3><ul>
      <li><a href="review.html">검토 현황</a><em>{NREV}/{ANS['docs']}</em><span>사람이 원본과 대조를 마친 문서 · 남은 문서 · 편마다 인쇄용 검토지</span></li>
      <li><a href="analysis.html">통합 분석</a><em>{ANS['docs']}건</em><span>{NEP}편 전체를 한 장에 — 세기 · 문서 유형 · 지역 · 정서 · 판독 난도 · 원문 인용 · 남겨 둔 질문</span></li>
      <li><a href="about.html">기획 노트</a><span>만든 이유 · 고른 기준 · 숫자로 본 100편 · 버전별 히스토리 · 지킨 원칙</span></li>
      <li><button class="lk" type="button" data-open="{latest['key']}" data-tab="b">편별 큐레이터 노트</button><em>{NEP}편</em><span>왜 골랐나 · 전하고 싶은 것 · 만들며 있었던 일 · 남겨 둔 질문</span></li>
      <li><button class="lk" type="button" data-open="{latest['key']}" data-tab="b">비하인드 카드</button><em>{NBH}장</em><span>편마다 3장 — 2차 홍보용</span></li>
    </ul></section>
    <section><h3>📢 퍼뜨리기</h3><ul>
      <li><a href="promote.html">채널별 홍보 가이드</a><span>인스타 · 유튜브 · 틱톡 · 페이스북 · 스레드 · X · 전시 · 책 · 웹툰 · 영상 · 광고, 4주 계획</span></li>
      <li><a href="{latest['f']}/channels.md" target="_blank" rel="noopener">편별 채널 홍보안</a><span>편마다 바로 쓰는 문구 · 형식 · 지표</span></li>
      <li><a href="series/promo.md" target="_blank" rel="noopener">시리즈 게시 문구</a> · <a href="#series">시리즈 카드</a><span>"📜 고문서 한 장 EP.NN" 형식</span></li>
      <li><a href="use.html">패키지 활용 가이드</a><span>누가 무엇을 할 수 있나 · 부가가치 · 권리 · 윤리 체크리스트</span></li>
    </ul></section>
    <section><h3>🛠️ 만들기 · 연구하기</h3><ul>
      <li><a href="#try">플러그인 설치 · 말로 시키기</a><span>Claude에게 "OO 종가 문서로 전시랑 영상 만들어줘"</span></li>
      <li><a href="tutorial/site/index.html">처음부터 끝까지 따라하기</a><em>10단계</em><span>찾기 → 받기 → 문구·전달 에디팅 → 점검 → 전시·영상 → 원본 묶음 → 시리즈 사이트</span></li>
      <li><a href="#compare">여러 소장처 비교</a><span>문서 유형 · 세기 분포 비교표와 그래프, 연구 패키지</span></li>
      <li><a href="https://github.com/changgi/archive-tools" target="_blank" rel="noopener">GitHub 저장소</a> · <a href="https://github.com/changgi/archive-tools/blob/main/CHANGELOG.md" target="_blank" rel="noopener">변경 기록</a><span>코드 · 문서 · 오류 제보(문제가 있는 이미지는 바로 내립니다)</span></li>
    </ul></section>
  </div>
  </section>

  <h2 id="why">이 시리즈를 만든 이유</h2>
  <div class="why"><div><p><b>볼 수는 있지만 읽을 수는 없는 기록</b> — 흘림 한자와 이두, 옛 한글로 쓰인 고문서에 다리를 놓고 싶었습니다. 한 번에 한 장씩, 원문을 끝까지 읽고, 오늘의 말로 옮기고, 종이에 실제로 적힌 문장으로 이야기를 들려줍니다.</p>
  <p>합격증을 받은 아버지, 굶주린 어머니를 위해 자신을 판 여인, 임금의 부름에 대신 답한 종, 바다 건너와 조선 사람이 된 장수 — 고문서는 누군가의 기쁨과 걱정이 적힌 종이입니다.</p>
  <div class="row"><a class="btn pri" href="about.html">기획 노트 읽기 — 의도 · 고른 기준 · 히스토리</a><button class="btn" type="button" data-open="{latest['key']}" data-tab="b">편별 비하인드 보기</button></div></div>
  <div><ul><li><b>고른 기준</b> 사람의 목소리가 들리는 한 줄 · 소장처·시대·신분의 다양성 · 공개된 이미지만</li><li><b>보이길 바란 모습</b> 가볍게는 1분 릴스, 깊게는 원문 전문 · 번역 · 해제</li><li><b>두 가지 에디팅</b> 문구 에디팅(무엇을 말할지) + 전달 에디팅(어떻게 · 무엇으로 · 어디로 전할지)</li><li><b>이렇게 써 주세요</b> 수업(활동지 「선생님께」) · 전시 · 연구(CSV · 원본 묶음) · SNS</li><li><b>지킨 원칙</b> 판독은 초안, □ 못 읽은 글자 · (?) 불확실, 이미지 재사용은 소장처 동의</li></ul></div></div>

  <h2 id="series">시리즈 비하인드 — 2차 홍보</h2>
  <div class="sbh">{''.join(f'<figure><video controls playsinline preload="none" poster="media/{r}_reel-poster.jpg"><source src="media/{r}_reel.mp4" type="video/mp4"><track kind="captions" srclang="ko" label="한국어" src="media/{r}.ko.vtt"></video><figcaption>{t}</figcaption></figure>' for r, t in [('series-why', '① 왜 「고문서 한 장」인가'), ('series-history', '② 100편이 걸어온 길'), ('series-behind', '③ 만들며 있었던 일')])}</div>
  <div class="bcs" style="margin-top:14px" tabindex="0" role="region" aria-label="시리즈 카드 — 옆으로 넘겨 보기">{''.join(f'<img src="series/cards/{f}" alt="시리즈 카드" loading="lazy">' for f in sorted(os.listdir(R + 'series/cards')))}</div>
  <div class="row" style="margin-top:8px"><a class="btn" href="series/promo.md" target="_blank" rel="noopener">게시 문구</a><a class="btn" href="promote.html">채널별 홍보 가이드</a><a class="btn" href="use.html">패키지 활용 가이드</a></div>

  <h2 id="outputs">결과물 한눈에 보기 — 바로 가기</h2>
  <p>고문서 한 장마다 아래 결과물이 함께 만들어집니다. 버튼을 누르면 <b>가장 최근 편(EP.{latest['ep']})</b>의 실제 결과물이 바로 열립니다. 모든 편의 결과물은 맨 아래 <a href="#alltable">전체 결과물 표</a>에서 한 번에 찾을 수 있어요.</p>
  <div class="outs">
    <div class="out"><span class="ic">🎬</span><b>릴스 · 가로 영상</b><p>세로 9:16 릴스와 가로 16:9 영상, 한국어 자막(srt·vtt)까지.</p><div class="row"><a class="btn pri" href="{latest['reel']}" target="_blank" rel="noopener">릴스 ↗</a><a class="btn" href="{latest['wide']}" target="_blank" rel="noopener">가로 ↗</a></div></div>
    <div class="out"><span class="ic">📜</span><b>원문 읽기</b><p>판독 전문 · 번역 · 해제 · 요약 · "현대어(原文)" 이야기.</p><div class="row"><button class="btn pri" type="button" data-open="{latest['key']}" data-tab="r">열기</button></div></div>
    <div class="out"><span class="ic">🖼️</span><b>전시 웹페이지</b><p>문서 이미지와 이야기를 한 장씩 넘겨 보는 온라인 전시.</p><div class="row"><a class="btn pri" href="{latest['f']}/exhibit.html" target="_blank" rel="noopener">전시 ↗</a></div></div>
    <div class="out"><span class="ic">✏️</span><b>수업 활동지</b><p>인쇄해서 바로 쓰는 학생용 활동지(읽기 · 찾기 · 생각하기).</p><div class="row"><a class="btn pri" href="{latest['f']}/handout.html" target="_blank" rel="noopener">활동지 ↗</a></div></div>
    <div class="out"><span class="ic">🗂️</span><b>카드뉴스</b><p>SNS에 올리는 4:5 카드 묶음(표지 · 문서별 · 마무리).</p><div class="row"><button class="btn pri" type="button" data-open="{latest['key']}" data-tab="c">보기</button></div></div>
    <div class="out"><span class="ic">📊</span><b>원문·번역 표 (CSV)</b><p>문서명 · 연도 · 판독 · 번역 · 해제 · 원본 링크를 담은 데이터.</p><div class="row"><a class="btn pri" href="{latest['f']}/selection.csv" download>CSV 받기</a></div></div>
    <div class="out"><span class="ic">📣</span><b>홍보 글 · 릴스 문구</b><p>"📜 고문서 한 장" 형식의 게시 문구와 해시태그.</p><div class="row"><a class="btn pri" href="{latest.get('promo','')}" target="_blank" rel="noopener">홍보 글 ↗</a><button class="btn" type="button" data-open="{latest['key']}" data-tab="s">문구 복사</button></div></div>
    <div class="out"><span class="ic">✍️</span><b>큐레이터 노트 · 비하인드</b><p>왜 골랐는지, 무엇을 전하려 했는지, 어떻게 쓰이길 바라는지, 만들며 있었던 일.</p><div class="row"><button class="btn pri" type="button" data-open="{latest['key']}" data-tab="b">이 편의 노트</button><a class="btn" href="about.html">기획 노트</a></div></div>
    <div class="out"><span class="ic">🃏</span><b>비하인드 카드 (2차 홍보)</b><p>편마다 3장 — 전하고 싶은 것 · 만들며 있었던 일 · 남겨 둔 질문.</p><div class="row"><button class="btn pri" type="button" data-open="{latest['key']}" data-tab="b">보기</button></div></div>
    <div class="out"><span class="ic">📢</span><b>채널별 홍보안</b><p>인스타 · 유튜브 · 틱톡 · 페이스북 · 스레드 · X · 전시 · 책 · 웹툰 · 영상 · 광고.</p><div class="row"><a class="btn pri" href="promote.html">홍보 가이드</a><a class="btn" href="{latest['f']}/channels.md" target="_blank" rel="noopener">이 편의 홍보안</a></div></div>
    <div class="out"><span class="ic">🧰</span><b>패키지 활용 가이드</b><p>누가 무엇을 할 수 있나, 부가가치를 만드는 길, 지킬 것.</p><div class="row"><a class="btn pri" href="use.html">활용 가이드</a></div></div>
    <div class="out"><span class="ic">🎭</span><b>전달 에디팅</b><p>고른 기록을 어떤 정서·장면·물질·통로·매개로 전할지 — 같은 기록이 마음에 남게.</p><div class="row"><button class="btn pri" type="button" data-open="{latest['key']}" data-tab="d">이 편의 설계</button><a class="btn" href="about.html#delivery">왜 필요한가</a></div></div>
    <div class="out"><span class="ic">📊</span><b>통합 분석</b><p>전체 {NEP}편 · 문서 {ANS['docs']}건을 한 장에 — 시대 · 유형 · 지역 · 정서 · 판독 · 인용 · 질문.</p><div class="row"><a class="btn pri" href="analysis.html">분석 보기</a></div></div>
    <div class="out"><span class="ic">🧭</span><b>처음부터 끝까지 따라하기</b><p>실제 예제 「임금이 보낸 종이 세 장」 — 찾기부터 영상·시리즈 사이트까지, 단계마다 자동 초안과 다듬은 결과.</p><div class="row"><a class="btn pri" href="tutorial/site/index.html">완성된 사이트</a><a class="btn" href="https://github.com/changgi/archive-tools/blob/main/examples/tutorial/README.md" target="_blank" rel="noopener">단계별 안내 ↗</a></div></div>
    <div class="out"><span class="ic">🔍</span><b>문구 에디팅 전후</b><p>자동 초안과, 원문을 읽고 다듬은 이야기를 나란히 비교.</p><div class="row"><button class="btn pri" type="button" data-open="{latest['key']}" data-tab="e">비교 보기</button></div></div>
  </div>

  <h2 id="new">새로 나온 편</h2>
  <div class="feat"><video controls playsinline preload="metadata" poster="{latest['wp']}"><source src="{latest['wide']}" type="video/mp4"><track kind="captions" srclang="ko" label="한국어" src="{latest['vtt']}"></video>
    <div><small style="color:var(--gold);font-weight:700">EP.{latest['ep']:02d} · {latest['k']}</small><h3>{e_(latest['t'])}</h3><p>{e_(latest['d'])}</p>
    <div class="row"><button class="btn pri" type="button" data-open="{latest['key']}">자세히 보기 — 원문 · 카드뉴스</button><a class="btn" href="#browse">전체 에피소드</a></div></div></div>

  <h2 id="browse">에피소드 — 「고문서 한 장」</h2>
  <p>카드를 누르면 영상, <b>원문 읽기</b>(판독 전문 · 번역 · 해제 · 요약), 카드뉴스, <b>문구 에디팅 전후</b>, <b>전달 에디팅</b>(표현 · 물질 · 통로 · 매개), 비하인드, 홍보 글을 한 창에서 볼 수 있습니다. 검색창에 인물·문서·지역(예: <i>유지</i>, <i>안동</i>, <i>언간</i>)을 넣어 보세요. <span class="kbd">창 안에서 ← → 로 이전·다음 편, Esc로 닫기.</span></p>
  <div class="tools">
    <input type="search" id="q" placeholder="검색 — 제목 · 소장처 · 인물 · 문서 · 원문 이야기" aria-label="에피소드 검색"><a class="btn" id="fts" href="search.html">원문 전문에서 찾기 →</a>
    <div class="chips" id="kinds" role="group" aria-label="소장처 유형"><button class="chip" type="button" data-k="" aria-pressed="true">전체<small>{len(ITEMS)}</small></button>{"".join(f'<button class="chip" type="button" data-k="{k}" aria-pressed="false">{k}<small>{kcount[k]}</small></button>' for k in KINDS if kcount[k])}</div>
    <select id="grp" aria-label="묶음"><option value="">모든 묶음</option>{"".join(f'<option value="{g}">{t} ({gcount[g]})</option>' for g, t in GROUPS if gcount[g])}<option value="base">기본 예시 (영상 없음)</option></select>
    <select id="sort" aria-label="정렬"><option value="new">최신 편부터</option><option value="old">첫 편부터</option></select>
    <label class="ck"><input type="checkbox" id="onlyv"> 영상 있는 것만</label>
    <span class="count" id="cnt"></span>
  </div>
  <div class="eps" id="eps"></div>
  <p class="empty" id="empty" hidden>맞는 에피소드가 없습니다. 검색어를 줄이거나 <a href="search.html" id="fts2">판독 · 번역 · 해제 전문에서 찾아보세요</a>.</p>
  <details class="all" id="alltable"><summary>전체 결과물 표 — {len([i for i in ITEMS if i.get('f')])}편의 영상 · 전시 · 활동지 · 카드 · CSV · 홍보 글 바로 가기</summary><div class="allwrap"><input type="search" id="aq" placeholder="표에서 찾기 — 제목 · 소장처" aria-label="결과물 표 검색"><table class="all"><thead><tr><th>편</th><th>제목</th><th>소장처</th><th>바로 가기</th></tr></thead><tbody id="allb"></tbody></table></div></details>

  <dialog id="epd" aria-labelledby="dt"><div class="dlg">
    <div class="dh"><button class="ib" id="dprev" type="button" aria-label="이전 편">‹</button><div class="tt"><small id="dtag"></small><h3 id="dt"></h3><div id="dwho"></div></div><button class="ib" id="dnext" type="button" aria-label="다음 편">›</button><button class="ib" id="dx" type="button" aria-label="닫기">✕</button></div>
    <div class="tabs" role="tablist"><button role="tab" data-p="v">영상</button><button role="tab" data-p="r">원문 읽기</button><button role="tab" data-p="c">카드뉴스</button><button role="tab" data-p="e">문구 에디팅 전후</button><button role="tab" data-p="d">전달 에디팅</button><button role="tab" data-p="b">비하인드</button><button role="tab" data-p="s">자료 · 공유</button></div>
    <div class="pane" id="pane"></div></div></dialog>
  <div class="zoom" id="zoom"><img alt=""></div>

'''
tail2 = tail.replace('<h2>여러 소장처 비교', '<h2 id="compare">여러 소장처 비교').replace('<h2>직접 해 보기', '<h2 id="try">직접 해 보기')

JS = r'''<script>
const IT=__ITEMS__;
const $=s=>document.querySelector(s),esc=t=>String(t??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const st={q:'',k:'',g:'',sort:'new',v:false};let LIST=[],cur=-1,tab='v',fmt='wide',auto=true;const CSV={};
IT.forEach(i=>i.hay=[i.t,i.who,i.d,i.k,'EP.'+i.ep,...(i.edits||[]).map(r=>r.d+' '+r.a+' '+r.y)].join(' ').toLowerCase());
const hl=(t,q)=>{t=esc(t);if(!q)return t;const r=q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');return t.replace(new RegExp(r,'gi'),m=>`<mark>${m}</mark>`)};
function render(){const q=st.q.trim().toLowerCase();
  LIST=IT.filter(i=>(!st.k||i.k===st.k)&&(!st.g||i.g===st.g)&&(!st.v||i.reel)&&(!q||q.split(/\s+/).every(w=>i.hay.includes(w))));
  LIST.sort((a,b)=>st.sort==='new'?((b.ep||0)-(a.ep||0)):((a.ep||99)-(b.ep||99)));
  const QL=i=>i.f?`<div class="ql">${i.reel?`<a href="${i.reel}" target="_blank" rel="noopener">릴스</a>`:''}${i.wide?`<a href="${i.wide}" target="_blank" rel="noopener">가로</a>`:''}<a href="${i.f}/exhibit.html" target="_blank" rel="noopener">전시</a><a href="${i.f}/handout.html" target="_blank" rel="noopener">활동지</a><a href="${i.f}/selection.csv" download>CSV</a>${i.promo?`<a href="${i.promo}" target="_blank" rel="noopener">홍보 글</a>`:''}</div>`:'';
  $('#eps').innerHTML=LIST.map((i,j)=>`<div class="epw"><button class="ep" type="button" data-j="${j}"><div class="im"><img src="${encodeURI(i.cover)}" alt="" loading="lazy" decoding="async">${i.ep?`<span class="badge">EP.${String(i.ep).padStart(2,'0')}</span>`:'<span class="badge">예시</span>'}<span class="kind">${esc(i.k)}</span>${i.reel?'<span class="pl" aria-hidden="true">▶</span>':''}</div><div class="tx"><b>${hl(i.t,st.q.trim())}</b><span>${hl(i.who,st.q.trim())}</span></div></button>${QL(i)}</div>`).join('');
  $('#empty').hidden=LIST.length>0;$('#cnt').textContent=`${LIST.length}편`;
  document.querySelectorAll('#eps .ep').forEach(b=>b.onclick=()=>openAt(+b.dataset.j))}
let tq;$('#q').oninput=e=>{clearTimeout(tq);tq=setTimeout(()=>{st.q=e.target.value;render()},120)};
document.querySelectorAll('#kinds .chip').forEach(c=>c.onclick=()=>{st.k=c.dataset.k;document.querySelectorAll('#kinds .chip').forEach(x=>x.setAttribute('aria-pressed',x===c));render()});
$('#grp').onchange=e=>{st.g=e.target.value;render()};$('#sort').onchange=e=>{st.sort=e.target.value;render()};$('#onlyv').onchange=e=>{st.v=e.target.checked;render()};
// CSV (따옴표 안 줄바꿈 지원)
function parseCSV(t){t=t.replace(/^﻿/,'');const rows=[];let r=[],f='',q=false;for(let i=0;i<t.length;i++){const c=t[i];if(q){if(c==='"'){if(t[i+1]==='"'){f+='"';i++}else q=false}else f+=c}else if(c==='"')q=true;else if(c===','){r.push(f);f=''}else if(c==='\n'){r.push(f);rows.push(r);r=[];f=''}else if(c!=='\r')f+=c}if(f||r.length){r.push(f);rows.push(r)}const h=rows.shift();return rows.filter(x=>x.length>1).map(x=>Object.fromEntries(h.map((k,j)=>[k,x[j]||''])))}
async function sel(f){if(!CSV[f]){try{CSV[f]=parseCSV(await (await fetch(f+'/selection.csv')).text())}catch(e){CSV[f]=[]}}return CSV[f]}
const dlg=$('#epd'),pane=$('#pane');
function openAt(j,t){cur=j;const i=LIST[j];if(!i)return;if(!dlg.open)dlg.showModal();
  $('#dtag').textContent=(i.ep?`EP.${String(i.ep).padStart(2,'0')} · `:'')+i.k+(LIST.length>1?`  (${j+1}/${LIST.length})`:'');$('#dt').textContent=i.t;$('#dwho').textContent=i.who;
  $('#dprev').disabled=j<=0;$('#dnext').disabled=j>=LIST.length-1;
  const has={v:!!i.reel,r:!!i.f,c:!!(i.cards&&i.cards.length),e:!!(i.edits&&i.edits.length),d:!!i.dv,b:!!i.cn,s:true};
  document.querySelectorAll('.tabs button').forEach(b=>{b.disabled=!has[b.dataset.p]});
  t=t||tab;if(!has[t])t=['v','r','c','e','d','b','s'].find(k=>has[k]);show(t);history.replaceState(null,'','#'+i.key)}
function show(t){tab=t;document.querySelectorAll('.tabs button').forEach(b=>b.setAttribute('aria-selected',b.dataset.p===t));const i=LIST[cur];pane.scrollTop=0;
  ({v:pV,r:pR,c:pC,e:pE,d:pD,b:pB,s:pS})[t](i)}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>!b.disabled&&show(b.dataset.p));
function pV(i){const w=fmt==='wide'&&i.wide;pane.innerHTML=`<div class="vwrap"><div class="vbox ${w?'wide':'reel'}"><video controls playsinline autoplay poster="${w?i.wp:i.rp}"><source src="${w?i.wide:i.reel}" type="video/mp4"><track kind="captions" srclang="ko" label="한국어" src="${i.vtt}"></video></div>
  <div class="vside"><div class="row">${i.wide?`<div class="seg" role="group" aria-label="화면 비율"><button type="button" data-f="wide" aria-pressed="${!!w}">가로 16:9</button><button type="button" data-f="reel" aria-pressed="${!w}">세로 9:16</button></div>`:''}<label class="ck"><input type="checkbox" id="auto" ${auto?'checked':''}> 끝나면 다음 편</label></div>
  <p class="lead">${esc(i.d)}</p><div class="row"><span class="kbd">${i.dr}초${i.dw?` · 가로 ${i.dw}초`:''} · 자막 포함</span></div>
  <div class="row">${i.f?'<button class="btn pri" type="button" data-t="r">원문 읽기 →</button>':''}<a class="btn" href="${i.reel}" download>릴스 받기</a>${i.wide?`<a class="btn" href="${i.wide}" download>가로 영상 받기</a>`:''}<a class="btn" href="${i.srt}">자막(srt)</a></div>
  <details class="trs"><summary>자막 전문 읽기 — 소리 없이 · 화면 읽기 프로그램으로</summary><div class="trx" tabindex="0" role="region" aria-label="자막 전문">불러오는 중…</div></details></div></div>`;
  const v=pane.querySelector('video');v.play().catch(()=>{});
  const tr=pane.querySelector('.trs');if(tr)tr.addEventListener('toggle',()=>{const box=tr.querySelector('.trx');if(!tr.open||box.dataset.ok)return;fetch(i.vtt).then(r=>r.text()).then(t=>{const L=t.replace(/\r/g,'').split('\n\n').map(b=>b.split('\n').filter(l=>l&&!/^WEBVTT/.test(l)&&!/-->/.test(l)&&!/^\d+$/.test(l)).join(' ')).filter(Boolean);box.innerHTML=L.map(l=>'<p>'+esc(l)+'</p>').join('');box.dataset.ok=1}).catch(()=>{box.textContent='자막을 불러오지 못했습니다 — 자막(srt) 파일을 받아 보세요.'})});
  v.onended=()=>{if(auto&&cur<LIST.length-1){let n=cur+1;while(n<LIST.length&&!LIST[n].reel)n++;if(n<LIST.length)openAt(n,'v')}};
  pane.querySelectorAll('.seg button').forEach(b=>b.onclick=()=>{fmt=b.dataset.f;pV(i)});$('#auto').onchange=e=>auto=e.target.checked;
  pane.querySelectorAll('[data-t]').forEach(b=>b.onclick=()=>show(b.dataset.t))}
function fixUrl(r,i){const b=`문서: ${r['문서명']||''}\n자료 ID: ${r['자료ID']||''}\n원본 뷰어: ${r['뷰어링크']||''}\n편: ${i.ep?'EP.'+String(i.ep).padStart(2,'0')+' ':''}${i.t}\n\n고칠 곳(판독 · 번역 · 해제 · 연도 가운데):\n\n바르게 고친 내용:\n\n근거(원본 사진의 줄 · 다른 자료):\n`;return 'https://github.com/changgi/archive-tools/issues/new?title='+encodeURIComponent('[판독 고침] '+(r['문서명']||''))+'&body='+encodeURIComponent(b)+'&labels='+encodeURIComponent('판독 고침')}
async function pR(i){pane.innerHTML='<p class="kbd">원문을 불러오는 중…</p>';const rows=await sel(i.f);if(LIST[cur]!==i||tab!=='r')return;
  const vw=localStorage.getItem('rv')||'all';
  pane.innerHTML=`<div class="row" style="margin-bottom:12px"><div class="seg" role="group" aria-label="보기"><button type="button" data-m="all" aria-pressed="${vw==='all'}">전부</button><button type="button" data-m="src" aria-pressed="${vw==='src'}">원문 + 번역</button><button type="button" data-m="easy" aria-pressed="${vw==='easy'}">쉬운 설명만</button></div><button class="btn" type="button" id="xall">모두 펼치기</button><a class="btn" href="${i.f}/exhibit.html" target="_blank" rel="noopener">전시 웹페이지에서 보기 ↗</a><a class="btn" href="${i.f}/handout.html" target="_blank" rel="noopener">수업 활동지 ↗</a></div>
  <div class="docs">${rows.map((r,j)=>`<details class="doc" ${j===0?'open':''}><summary><span class="n">${esc(r['순서'])}</span><b>${esc(r['문서명'])}</b><span class="y">${esc(r['연도'])}${r['문서유형']?' · '+esc(r['문서유형']):''}</span></summary>
   <div class="dbody"><div><img src="${i.f}/cards/${String(r['순서']).padStart(2,'0')}.jpg" alt="${esc(r['문서명'])}" loading="lazy" onerror="this.remove()">${r['뷰어링크']?`<p style="margin-top:6px"><a href="${esc(r['뷰어링크'])}" target="_blank" rel="noopener">자료관 원본 보기 ↗</a></p>`:''}<p style="margin-top:4px"><a href="${esc(fixUrl(r,i))}" target="_blank" rel="noopener">판독 고침 제보 ↗</a></p></div>
   <div>${r['이야기']?`<p class="story">${esc(r['이야기'])}</p>`:''}
    <div data-s="easy">${r['해제']?`<h4>해제 — 어떤 문서?</h4><p>${esc(r['해제'])}</p>`:''}${r['요약']?`<h4>내용 요약</h4><p>${esc(r['요약'])}</p>`:''}</div>
    <div data-s="src">${r['원문']?`<h4>원문 판독 전문</h4><pre>${esc(r['원문'])}</pre>`:(r['판독']?`<h4>판독</h4><pre>${esc(r['판독'])}</pre>`:'')}${r['번역']?`<h4>원문 해석</h4><p>${esc(r['번역'])}</p>`:''}</div></div></div></details>`).join('')}</div>`;
  const apply=m=>{localStorage.setItem('rv',m);pane.querySelectorAll('[data-m]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.m===m));pane.querySelectorAll('[data-s]').forEach(d=>d.hidden=!(m==='all'||d.dataset.s===m))};
  pane.querySelectorAll('[data-m]').forEach(b=>b.onclick=()=>apply(b.dataset.m));apply(vw);
  $('#xall').onclick=e=>{const ds=pane.querySelectorAll('details.doc'),o=![...ds].every(d=>d.open);ds.forEach(d=>d.open=o);e.target.textContent=o?'모두 접기':'모두 펼치기'};
  pane.querySelectorAll('.dbody img').forEach(m=>m.onclick=()=>{$('#zoom img').src=m.src;$('#zoom').classList.add('on')})}
function pC(i){pane.innerHTML=`<div class="row" style="margin-bottom:10px"><span class="kbd" id="cdn">1 / ${i.cards.length}</span><a class="btn" href="https://github.com/changgi/archive-tools/tree/main/examples/${i.f}/cards" target="_blank" rel="noopener">원본 파일 ↗</a></div>
  <div class="cdv"><button class="ib l" type="button" aria-label="이전 카드">‹</button><div class="cdtrack" tabindex="0">${i.cards.map((f,j)=>`<img src="${i.f}/cards/${encodeURI(f)}" alt="${esc(i.t)} 카드 ${j+1}" loading="${j<3?'eager':'lazy'}">`).join('')}</div><button class="ib r" type="button" aria-label="다음 카드">›</button></div>`;
  const tr=pane.querySelector('.cdtrack'),ims=[...tr.children];const at=()=>{const x=tr.scrollLeft;let b=0;ims.forEach((m,j)=>{if(Math.abs(m.offsetLeft-tr.offsetLeft-x)<Math.abs(ims[b].offsetLeft-tr.offsetLeft-x))b=j});return b};
  const go=d=>{const n=Math.max(0,Math.min(ims.length-1,at()+d));tr.scrollTo({left:ims[n].offsetLeft-tr.offsetLeft})};
  pane.querySelector('.l').onclick=()=>go(-1);pane.querySelector('.r').onclick=()=>go(1);
  tr.onscroll=()=>{$('#cdn').textContent=`${at()+1} / ${ims.length}`};ims.forEach(m=>m.onclick=()=>{$('#zoom img').src=m.src;$('#zoom').classList.add('on')})}
function pE(i){pane.innerHTML=`<p class="kbd" style="margin-top:0"><b>문구 에디팅</b> — 자동 초안(<code>edit</code>가 문서명으로 만든 문장) → 에디팅 후(원문을 읽고 다듬은 이야기)</p><div class="edwrap"><table class="ed"><thead><tr><th>#</th><th>문서</th><th>자동 초안</th><th>에디팅 후</th></tr></thead><tbody>${i.edits.map(r=>`<tr><td>${esc(r.n)}</td><td>${esc(r.d)}</td><td style="color:var(--dim)">${esc(r.b)}</td><td>${esc(r.a)}</td></tr>`).join('')}</tbody></table></div>`}
function pD(i){const d=i.dv;const st=[['open','열기'],['unfold','펼치기'],['climax','절정'],['after','여운']];
  pane.innerHTML=`<p class="kbd" style="margin-top:0"><b>전달 에디팅</b> — 큐레이션으로 고른 기록을 <b>어떻게 표현하고, 어떤 물질과 감각, 어떤 통로와 매개로</b> 전할지 설계한 것. 같은 사실도 이렇게 전하면 마음에 남습니다.</p>
  <div class="dvh"><span class="dve">${esc(d.emotion||'')}</span><span>${esc(d.message||'')}</span></div>
  <div class="dvba"><div class="b0"><b>전달 에디팅 전 — 기록 그대로</b><p>${esc(d.before||'')}</p></div><div class="b1"><b>전달 에디팅 후 — 마음에 남게</b><p>${esc(d.afterd||'')}</p></div></div>
  <h4 class="dvt">장면 설계</h4><div class="dvf">${st.filter(([k])=>d[k]).map(([k,l],n)=>`<div class="dvs"><small>${n+1}</small><b>${l}</b><p>${esc(d[k])}</p></div>`).join('<i>→</i>')}</div>
  <div class="dvg">${[['matter','🧵 감각과 물질'],['path','🛤️ 통로와 매개'],['linger','✍️ 여운 장치']].filter(([k])=>d[k]).map(([k,l])=>`<div class="cnb"><b>${l}</b><p>${esc(d[k])}</p></div>`).join('')}</div>
  <div class="row" style="margin-top:12px"><a class="btn" href="${i.f}/delivery.md" target="_blank" rel="noopener">delivery.md ↗</a><a class="btn" href="${i.f}/exhibit.html#delivery" target="_blank" rel="noopener">전시 웹페이지의 연출 노트 ↗</a><a class="btn" href="about.html#delivery">왜 전달 에디팅인가 ↗</a></div>`}
const CNL=[['why','왜 이 문서들인가'],['message','전하고 싶은 것'],['look','이렇게 보이길 바랐다'],['use','이렇게 써 주세요'],['behind','만들며 있었던 일'],['question','남겨 둔 질문']];
function pB(i){const c=i.cn;pane.innerHTML=`<div class="cnw"><p class="kbd" style="margin-top:0">큐레이터 노트 — 이 편을 만든 이유와 비하인드</p>${c.message?`<blockquote class="cnq">${esc(c.message)}</blockquote>`:''}${i.f?`<div class="bcs">${['b1_전하고싶은것','b2_만들며있었던일','b3_남겨둔질문'].map(n=>`<img src="${i.f}/behind/${encodeURI(n)}.jpg" alt="비하인드 카드" loading="lazy" onerror="this.remove()">`).join('')}</div>`:''}<div class="cng">${CNL.filter(([k])=>c[k]&&k!=='message').map(([k,l])=>`<div class="cnb"><b>${l}</b><p>${esc(c[k])}</p></div>`).join('')}</div>${c.facts?`<p class="cnf"><b>제작 기록</b> ${c.facts.map(esc).join(' · ')}</p>`:''}<div class="row" style="margin-top:12px">${i.f?`<a class="btn" href="${i.f}/curator.md" target="_blank" rel="noopener">curator.md ↗</a><a class="btn" href="${i.f}/exhibit.html#curator" target="_blank" rel="noopener">전시 웹페이지의 노트 ↗</a>`:''}<a class="btn" href="${i.f}/channels.md" target="_blank" rel="noopener">채널별 홍보안 ↗</a><a class="btn" href="about.html">시리즈 기획 노트 ↗</a></div></div>`;pane.querySelectorAll('.bcs img').forEach(m=>m.onclick=()=>{$('#zoom img').src=m.src;$('#zoom').classList.add('on')})}
function pS(i){pane.innerHTML=`${i.links?`<h4 style="color:var(--gold);margin:0 0 8px">결과물</h4><div class="row links">${i.links.replace(/<a /g,'<a class="btn" target="_blank" rel="noopener" ')}${i.promo?`<a class="btn" href="${i.promo}" target="_blank" rel="noopener">홍보 글 ↗</a>`:''}</div>`:''}
  ${i.cap?`<h4 style="color:var(--gold);margin:20px 0 8px">릴스 홍보 문구</h4><div class="capbox" tabindex="0" role="region" aria-label="릴스 홍보 문구">${esc(i.cap)}</div><div class="row" style="margin-top:8px"><button class="btn pri" type="button" id="cp">문구 복사</button></div>`:''}
  <h4 style="color:var(--gold);margin:20px 0 8px">이 편 링크</h4><div class="row"><button class="btn" type="button" id="cl">링크 복사</button><span class="kbd">${esc(location.origin+location.pathname)}#${i.key}</span></div>
  <p class="kbd" style="margin-top:18px">이미지: 한국학중앙연구원 한국고문서자료관 소장·제공. 다시 쓰려면 자료관에 문의하세요. 문제가 있으면 알려 주시면 바로 내리겠습니다.</p>`;
  const copy=async(b,t)=>{try{await navigator.clipboard.writeText(t)}catch(e){const a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');a.remove()}const o=b.textContent;b.textContent='복사했어요 ✓';b.classList.add('done');setTimeout(()=>{b.textContent=o;b.classList.remove('done')},1600)};
  $('#cp')&&($('#cp').onclick=e=>copy(e.target,i.cap));$('#cl').onclick=e=>copy(e.target,location.origin+location.pathname+'#'+i.key)}
$('#dprev').onclick=()=>openAt(cur-1);$('#dnext').onclick=()=>openAt(cur+1);$('#dx').onclick=()=>dlg.close();
dlg.addEventListener('close',()=>{pane.innerHTML='';history.replaceState(null,'',location.pathname)});
dlg.addEventListener('click',e=>{if(e.target===dlg)dlg.close()});
dlg.addEventListener('keydown',e=>{if(e.target.closest('.cdtrack,input,select'))return;if(e.key==='ArrowRight'&&cur<LIST.length-1){e.preventDefault();openAt(cur+1)}if(e.key==='ArrowLeft'&&cur>0){e.preventDefault();openAt(cur-1)}});
$('#zoom').onclick=()=>$('#zoom').classList.remove('on');
document.querySelectorAll('#series ~ .bcs img').forEach(m=>m.onclick=()=>{$('#zoom img').src=m.src;$('#zoom').classList.add('on')});
(function(){const q=document.getElementById('q');if(!q)return;const up=()=>{const v=q.value.trim();['fts','fts2'].forEach(id=>{const a=document.getElementById(id);if(a)a.href='search.html'+(v?'?q='+encodeURIComponent(v):'')})};q.addEventListener('input',up)})();
document.querySelectorAll('.opent').forEach(x=>x.addEventListener('click',()=>{const d=document.getElementById('alltable');if(d)d.open=true}));
document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>{const fv=document.querySelector('.feat video');fv&&fv.pause();let j=LIST.findIndex(i=>i.key===b.dataset.open);if(j<0){st.q='';st.k='';st.g='';st.v=false;render();j=LIST.findIndex(i=>i.key===b.dataset.open)}openAt(j,b.dataset.tab||'r')});
// 전체 결과물 표
const ALLI=IT.filter(i=>i.f).sort((a,b)=>(b.ep||0)-(a.ep||0));
function allRender(q){q=(q||'').trim().toLowerCase();$('#allb').innerHTML=ALLI.filter(i=>!q||(i.t+' '+i.who+' EP.'+i.ep).toLowerCase().includes(q)).map(i=>`<tr><td>${i.ep?'EP.'+String(i.ep).padStart(2,'0'):'예시'}</td><td><a href="#${i.key}">${esc(i.t)}</a></td><td>${esc(i.who)}</td><td>${i.reel?`<a href="${i.reel}" target="_blank" rel="noopener">릴스</a>`:''}${i.wide?`<a href="${i.wide}" target="_blank" rel="noopener">가로</a>`:''}<a href="${i.f}/exhibit.html" target="_blank" rel="noopener">전시</a><a href="${i.f}/handout.html" target="_blank" rel="noopener">활동지</a><a href="https://github.com/changgi/archive-tools/tree/main/examples/${i.f}/cards" target="_blank" rel="noopener">카드</a><a href="${i.f}/selection.csv" download>CSV</a>${i.promo?`<a href="${i.promo}" target="_blank" rel="noopener">홍보 글</a>`:''}${i.cn?`<a href="${i.f}/curator.md" target="_blank" rel="noopener">노트</a><a href="${i.f}/channels.md" target="_blank" rel="noopener">채널</a>`:''}</td></tr>`).join('')}
allRender('');$('#aq').oninput=e=>allRender(e.target.value);
// 상단 메뉴 표시
const secs=['why','series','outputs','browse','compare','try'].map(id=>document.getElementById(id)).filter(Boolean);
if('IntersectionObserver' in window){const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)document.querySelectorAll('.topnav a').forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+e.target.id))}),{rootMargin:'-40% 0px -55% 0px'});secs.forEach(s=>io.observe(s))}
render();
function fromHash(){const h=location.hash.slice(1);if(!h)return;const j=LIST.findIndex(i=>i.key===h||('ep-'+i.ep)===h||('v-'+i.ep)===h||('ex-'+i.f)===h);if(j>=0&&j!==cur)openAt(j)}
fromHash();addEventListener('hashchange',fromHash);
</script>'''.replace('__ITEMS__', json.dumps(ITEMS, ensure_ascii=False))

tail2 = tail2.replace('</body>', JS + '\n</body>')
out = head2 + '\n</style>\n</head>\n<body>\n' + body + tail2
open(R + 'index.html', 'w', encoding='utf-8').write(out)
print('items', len(ITEMS), 'videos', NV, 'size', len(out))
