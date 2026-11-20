# EP.101~: new4/*.json 한 파일에 든 홍보 문구(cap) · 큐레이터 노트(cn) · 전달 에디팅(dv)을 예시 편 폴더에 적용
#   promo.md · curator.md · delivery.md · exhibit/handout/README 블록 · behind 카드 · channels.md · collect.json(원본 묶음용)
#   captions.json · curator.json · delivery.json에는 이 편들만 덧붙여 넣음(기존 101편은 건드리지 않음)
#   usage: python3 new4_post.py [folder ...]   (없으면 new4 전부)
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import sys, os, csv, json, re, glob
sys.path.insert(0, P.DATA); sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts'))
import studio as ST
from PIL import Image
import captions as CP
E = (P.REPO + '/examples/'); S = (P.DATA + '/'); B = CP.B
only = set(sys.argv[1:])
K = [k for k, _, _ in ST.CURATOR_KEYS]; LAB = {k: h for k, h, _ in ST.CURATOR_KEYS}; DLAB = {k: h for k, h, _ in ST.DELIVERY_KEYS}
CAPJ = json.load(open(S + 'captions.json', encoding='utf-8')); CNJ = json.load(open(S + 'curator.json', encoding='utf-8')); DVJ = json.load(open(S + 'delivery.json', encoding='utf-8'))
COL = json.load(open((P.STATE + '/collect.json'), encoding='utf-8'))
T, EE = '#고문서한장 ', ' #고문서 #한국고문서자료관 #원문판독 #Claude #오픈소스'


def caption_dict(J):
    M = J['meta']; c = J['cap']; ks = [str(k) for k in J['keep']]
    body = M['lead'] + '\n\n' + '\n'.join(J['docs'][k]['이야기'] for k in ks)
    return dict(n=M['ep'], id=M['id'], folder=M['folder'], coll=M['coll'], title=M['title'], hook=c['hook'], body=body, follow=c['follow'], q=c['q'], label=c['label'],
                tags=T + ' '.join(M['tag']) + EE)


for jp in sorted(glob.glob(S + 'new4/*.json')):
    J = json.load(open(jp, encoding='utf-8')); M = J['meta']; f = M['folder']
    if only and f not in only: continue
    if not os.path.exists(E + f + '/selection.csv'): continue
    sel = list(csv.DictReader(open(E + f + '/selection.csv', encoding='utf-8-sig')))
    # 1) 홍보 문구 · promo.md
    d = caption_dict(J); cap = CP.caption(d)
    for p in [E + f + '/promo.md', S + f"promo/{M['id']}.md"]:
        yt = ', '.join(t.lstrip('#') for t in d['tags'].split() if t not in ('#고문서한장', '#Claude', '#오픈소스'))
        s = CP.PROMO.format(n=d['n'], title=d['title'], coll=d['coll'], hook=d['hook'], lead=M['lead'], url=f"{B}{f}/exhibit.html", ytags=yt)
        s = re.sub(r'(## 1\. 릴스·쇼츠 \(9:16\) 게시 글\n```\n).*?(\n```)', lambda m: m.group(1) + cap + m.group(2), s, count=1, flags=re.S)
        open(p, 'w', encoding='utf-8').write(s)
    CAPJ[M['id']] = dict(n=d['n'], title=d['title'], folder=f, coll=d['coll'], caption=cap)
    # 2) 원본 묶음 목록(collect.json)
    work = (P.WORK + '/') + f if os.path.exists((P.WORK + '/') + f) else (P.CAND + '/') + f
    COL = [x for x in COL if x['folder'] != f]
    for s_ in sel:
        src = os.path.join(work, s_['원본경로']); pages = sorted(glob.glob(os.path.join(os.path.dirname(src), '*.jpg')))
        COL.append(dict(folder=f, n=s_['순서'], name=s_['문서명'], pages=pages, link=s_.get('뷰어링크', '')))
    pages_n = sum(len(x['pages']) for x in COL if x['folder'] == f)
    # 3) 큐레이터 노트
    c = {k: v for k, v in zip(K, J['cn']) if v}
    md = [f'# 큐레이터 노트 — {M["title"]}', '']
    for k in K:
        if c.get(k): md += [f'## {LAB[k]}', c[k], '']
    open(E + f + '/curator.md', 'w', encoding='utf-8').write('\n'.join(md))
    facts = ST.curator_facts(sel); facts.insert(1, f'원본 사진 {pages_n}면(문서 전체)')
    p = E + f + '/exhibit.html'; s = open(p, encoding='utf-8').read()
    s = re.sub(r'<p style="font:15px sans-serif"><a href="#curator"[^<]*</a></p>', '', s)
    s = s.replace('</p></header>', '</p><p style="font:15px sans-serif"><a href="#curator" style="color:#c4964a">이 전시를 만든 이유 — 큐레이터 노트 ↓</a></p></header>', 1)
    s = ST.put_curator(s, ST.curator_html(c, facts, 'exhibit'), '</main>')
    # 4) 전달 에디팅
    emo, mat, ling = J['dv']
    key = re.sub(r'["“”]', '', J['quote'][0]).strip()
    dv = ST.delivery_draft(sel, c, hook=re.sub(r'^\W+\s*', '', J['cap']['hook']), key=key)
    dv['emotion'] = emo; dv['matter'] = mat + (' · ' + dv['matter'] if dv['matter'] else ''); dv['linger'] = ling
    cl = dv['climax'].split(' — ')[0]
    dv['afterd'] = (f"핵심 정서는 「{emo}」. 「{J['hook']}」로 열고, 문서를 {('대비와 순서' if len(sel) > 1 else '한 장의 집중')}로 펼친 뒤, {cl}에서 멈춘다. {mat}. "
                    f"마지막엔 「{ling}」로 보는 사람이 자기 이야기를 남기고 떠나게 한다.")
    md = [f'# 전달 에디팅 — {M["title"]}', '']
    for k, h, _ in ST.DELIVERY_KEYS:
        if dv.get(k): md += [f'## {h}', dv[k], '']
    open(E + f + '/delivery.md', 'w', encoding='utf-8').write('\n'.join(md))
    s = ST.put_delivery(s, ST.delivery_html(dv), '</main>'); open(p, 'w', encoding='utf-8').write(s)
    p = E + f + '/handout.html'; h_ = open(p, encoding='utf-8').read()
    open(p, 'w', encoding='utf-8').write(ST.put_curator(h_, ST.curator_html(c, None, 'handout'), None))
    # 5) README 블록
    p = E + f + '/README.md'
    if os.path.exists(p):
        s = open(p, encoding='utf-8').read()
        s = re.sub(r'\n<!-- CURATOR -->.*?<!-- /CURATOR -->\n', '\n', s, flags=re.S); s = re.sub(r'\n<!-- DELIVERY -->.*?<!-- /DELIVERY -->\n', '\n', s, flags=re.S)
        blk_c = ('\n<!-- CURATOR -->\n## 비하인드 — 큐레이터 노트\n\n' + '\n'.join(f'- **{LAB[k]}** — {c[k]}' for k in K if c.get(k)) + f'\n- **제작 기록** — {" · ".join(facts)}\n\n'
                 '전문: [`curator.md`](curator.md) · 비하인드 카드: [`behind/`](behind/) · 채널별 홍보안: [`channels.md`](channels.md)\n<!-- /CURATOR -->\n')
        blk_d = ('<!-- DELIVERY -->\n## 전달 에디팅 — 이 기록을 이렇게 전합니다\n\n' + '\n'.join(f'- **{DLAB[k]}** — {dv[k]}' for k, _, _ in ST.DELIVERY_KEYS if dv.get(k))
                 + '\n\n전문: [`delivery.md`](delivery.md)\n<!-- /DELIVERY -->\n')
        m = re.search(r'\n## (선별 문서|이야기 — )', s)
        s = s[:m.start()] + '\n' + blk_d + blk_c + s[m.start():] if m else s + '\n' + blk_d + blk_c
        open(p, 'w', encoding='utf-8').write(s)
    # 6) 비하인드 카드 · 채널별 홍보안
    first = next((x for x in COL if x['folder'] == f and x['n'] == sel[0]['순서']), None)
    img = None
    if first and first['pages']:
        rep = sel[0].get('대표장') or ''
        img = next((q for q in first['pages'] if os.path.basename(q) == rep), first['pages'][0])
    od = E + f + '/behind'; os.makedirs(od, exist_ok=True)
    for old in os.listdir(od): os.remove(os.path.join(od, old))
    src = f'자료: 한국학중앙연구원 한국고문서자료관 · {M["coll"]}'
    for q in ST.behind_cards(c, facts, f"EP.{M['ep']} " + M['title'], src, img, od, ext='jpg'):
        Image.open(q).convert('RGB').save(q, quality=80, optimize=True)
    QRX = r'"([^"(]{2,80})\(([^)]+)\)[.,]?"'
    qm = next((re.search(QRX, x.get('이야기') or '') for x in sel if re.search(QRX, x.get('이야기') or '')), None)
    ch = ST.channel_plan(c, M['title'], M['coll'], B + f + '/exhibit.html', quote=(f'"{qm.group(1)}({qm.group(2)})"' if qm else ''), ep=str(M['ep']),
                         tags=d['tags'].replace('#고문서한장 ', ''))
    open(E + f + '/channels.md', 'w', encoding='utf-8').write(ch)
    CNJ[f] = dict(c, facts=facts); DVJ[f] = dv
    print('post', M['id'], len(sel), 'docs', pages_n, 'pages')
json.dump(CAPJ, open(S + 'captions.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(CNJ, open(S + 'curator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(DVJ, open(S + 'delivery.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(COL, open((P.STATE + '/collect.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
