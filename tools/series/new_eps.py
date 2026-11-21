# new/*.json (판독·번역·해제·요약·이야기) → selection.csv, mediate, examples 폴더, 영상 설정
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import csv, json, os, re, glob, shutil, subprocess, sys
from PIL import Image
C = P.CAND; E = (P.REPO + '/examples'); S = P.DATA
STUDIO = (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/studio.py')
D = '일이삼사오육칠팔구'
def num(n):
    n = int(n); out = ''
    for v, u in [(1000, '천'), (100, '백'), (10, '십')]:
        q = n // v; n %= v
        if q: out += ('' if q == 1 else D[q - 1]) + u
    return out + (D[n - 1] if n else '')
def tts(t):
    t = re.sub(r'\([^)]*[一-鿿][^)]*\)', '', t)           # 한자 괄호 인용 제거
    t = re.sub(r'(\d{3,4})년', lambda m: num(m.group(1)) + ' 년', t)
    t = re.sub(r'(\d+)(냥|명|장|건|통|점|번|세|일|월|살|등|인)', lambda m: num(m.group(1)) + m.group(2), t)
    t = re.sub(r'\d+', lambda m: num(m.group()), t)
    return t.replace('『', '').replace('』', '').replace('"', '').replace('“', '').replace('”', '').replace('  ', ' ')
def clean(t): return re.sub(r'\s*\([^)]*[一-鿿ᄀ-ᇿ][^)]*\)', '', t).replace('  ', ' ')
def split(t):
    return [x.strip() for x in re.split(r'(?<=[.?!])\s+|(?<=[.?!]["”])\s+', t) if x.strip()]

def build(path, steps):
    J = json.load(open(path, encoding='utf-8')); M = J['meta']; w_ = os.path.basename(path)[:-5]; work = os.path.join(P.WORK if os.path.exists((P.WORK + '/') + w_) else C, w_)
    rd = os.path.join(E, M['folder'], 'README.md')  # 폴더 이름이 다른 편과 겹치면 덮어쓰지 않고 멈춤
    if os.path.exists(rd):
        m0 = re.match(r'#\s*EP\.(\d+)', open(rd, encoding='utf-8').readline())
        if m0 and int(m0.group(1)) != int(M['ep']):
            sys.exit(f"✗ examples/{M['folder']} 는 이미 EP.{m0.group(1)}의 폴더입니다 — meta.folder(와 작업 폴더 이름)를 바꾸세요")
    ed = os.path.join(work, 'edit', 'story')
    if not os.path.exists(ed + '/selection.orig.csv'): shutil.copy(ed + '/selection.csv', ed + '/selection.orig.csv')  # 다시 돌려도 원래 순서 유지
    rows = list(csv.DictReader(open(ed + '/selection.orig.csv', encoding='utf-8-sig')))
    keep = J.get('keep') or [int(k) for k in J['docs']]
    rows = sorted([r for r in rows if int(r['순서']) in keep], key=lambda r: keep.index(int(r['순서'])))
    newrows = []
    for i, r in enumerate(rows, 1):
        d = J['docs'][str(int(r['순서']))]
        r = {k: v for k, v in r.items()}
        r.update(이야기=d['이야기'], 판독=d['판독'], 원문=d['원문'], 번역=d['번역'], 해제=d['해제'], 요약=d['요약'], _src=d['이야기'])
        if d.get('연도'): r['연도'] = d['연도']
        r['순서'] = str(i); newrows.append(r)
    cols = ['순서', '자료ID', '문서명', '연도', '문서유형', '인물', '유형설명', '대표장', '이미지', '원본경로', '캡션', '이야기', '판독', '원문', '번역', '해제', '요약', '검토', '뷰어링크', '공유이미지']
    with open(ed + '/selection.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(newrows)
    th = json.load(open(ed + '/theme.json', encoding='utf-8')); th.update(title=M['title'], selected=len(newrows)); json.dump(th, open(ed + '/theme.json', 'w', encoding='utf-8'), ensure_ascii=False)
    if 'mediate' in steps:
        subprocess.run(['python3', STUDIO, 'mediate', '--work', work, '--theme', 'story', '--title', M['title'], '--lead', M['lead'], '--collection', M['coll']], check=True, capture_output=True)
        md = os.path.join(work, 'mediate', 'story'); f = os.path.join(E, M['folder']); os.makedirs(f + '/cards', exist_ok=True)
        for x in ['exhibit.html', 'handout.html', 'sns.txt']: shutil.copy(os.path.join(md, x), f)
        for x in ['selection.csv', 'theme.json']: shutil.copy(os.path.join(ed, x), f)
        for p in glob.glob(f + '/cards/*.jpg'): os.remove(p)
        for p in sorted(glob.glob(md + '/cards/*.png')): Image.open(p).convert('RGB').save(os.path.join(f, 'cards', os.path.basename(p)[:-4] + '.jpg'), quality=85, optimize=True)
        for x in ['metadata.csv', 'summary.md']:
            if os.path.exists(os.path.join(work, x)): shutil.copy(os.path.join(work, x), os.path.join(E, 'data', f"{M['folder']}_{x}"))
        os.makedirs(f'{S}/cap', exist_ok=True)
        subprocess.run(['node', '-e', f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await (await b.newContext({{viewport:{{width:1280,height:900}}}})).newPage();await p.goto('file://{md}/exhibit.html');await p.screenshot({{path:'{S}/cap/{M['folder']}_exhibit.jpg',quality:85,type:'jpeg'}});await b.close()}})()"""], check=True, cwd='/tmp')
    # 영상 설정
    L = lambda scene, text, t=None, **kw: dict(scene=scene, text=text, tts=t or tts(text), **kw)
    docs = json.load(open(work + '/docs.json')); n_docs = len(docs)
    lines = [L('hook', M.get('hook_text', J['hook']), q=J['hook'].replace('? ', '?\n') if len(J['hook']) > 26 else J['hook']),
             L('intro', f"{M['coll']}. 문서 {n_docs:,}건 가운데 {len(newrows)}점을 원문으로 읽었습니다.".replace(',', ''))]
    for i, r in enumerate(newrows, 1):
        st = r['_src']; m = re.search(r'\(([^)]*[一-鿿][^)]*)\)', st)
        src = m.group(1) if m else ''; src_ko = ''
        for qt in re.findall(r'"([^"]+)"', st):
            if src and src in qt: src_ko = clean(qt).rstrip('.'); break
        for j, sent in enumerate(split(clean(st))):
            kw = dict(doc=i, key=f'd{i}')
            if j == 0 and src:
                import hanja; rd = hanja.translate(src, 'substitution')
                kw.update(src=src, src_rd=rd, src_ko=src_ko)
            lines.append(L('doc', sent, **kw))
    q = J['quote']; lines.append(L('quote', ' '.join(q), big='\n'.join(q), doc=1))
    lines += [L('outputs', '원문 판독과 해석, 전시 웹페이지와 카드뉴스, 수업 활동지까지 만들었습니다.', '원문 판독과 해석, 전시 웹페이지와 카드뉴스, 수업 활동지까지 만들었습니다.'),
              L('cta', 'aks-archive-harvester. 깃허브에서 무료로 만나 보세요.', '에이케이에스 아카이브 하베스터. 깃허브에서 무료로 만나 보세요.')]
    import collections
    cats = collections.Counter(x['category'] for x in docs)
    cfg = dict(id=M['id'], series=f"EP.{M['ep']}", kind=M['kind'], kind_long=M['kind_long'], collection=M['coll'], voice=M['voice'], accent=M['accent'], glow=M['glow'],
               hero=1, hero_cx=.5, hero_cy=.4, tagline=q, bpm=76, root=57, selection=ed + '/selection.csv', mediate=os.path.join(work, 'mediate', 'story'),
               exhibit_cap=f"{S}/cap/{M['folder']}_exhibit.jpg", n_docs=n_docs, n_pages=sum(len(x['imgs']) for x in docs), cats=[[k, v] for k, v in cats.most_common()],
               lines=lines, title=M['title'], lead=M['lead'], work=os.path.basename(work), theme='story', folder=M['folder'])
    for k, v in list(cfg.items()):  # 저장소에 올릴 수 있게 폴더 위치는 $WORK · $DATA 같은 이름으로(showcase.py가 풀어 씀)
        if isinstance(v, str):
            for n in ('WORK', 'CAND', 'DATA', 'REPO', 'STATE'):
                if v.startswith(getattr(P, n) + os.sep) or v.startswith(getattr(P, n) + '/'): cfg[k] = '$' + n + v[len(getattr(P, n)):]; break
    json.dump(cfg, open(f"{S}/{M['id']}.json", 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(M['id'], len(newrows), 'docs', len(lines), 'lines')

if __name__ == '__main__':
    steps = sys.argv[2].split(',') if len(sys.argv) > 2 else ['mediate']
    for p in (sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else sorted(glob.glob(S + '/new/*.json'))):
        build(p if p.endswith('.json') else f'{S}/new/{p}.json', steps)
