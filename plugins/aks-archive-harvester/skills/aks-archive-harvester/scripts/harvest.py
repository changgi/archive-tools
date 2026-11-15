#!/usr/bin/env python3
"""
AKS 한국고문서자료관(archive.aks.ac.kr) 소장처 일괄 수집기.

  manifest : treeAjax.do 재귀 탐색 + imgnode.do로 문서·페이지 목록(docs.json) 생성
  download : DZI 타일을 받아 원본 해상도 JPG로 이어붙이기 (이어받기 지원, 시간제한 실행)
  report   : 문서목록 CSV (서버에 없는 장 / 저해상도 장 표시)
  pack     : 분류별 ZIP, 지정 용량(MB) 이하로 분할
  curate   : 큐레이션 — 연도·문서유형·인명 자동 추출 → metadata.csv/jsonl, summary.md(분포·인물 연표)
  bundle   : 연구 패키지 — 메타데이터 + 수집현황 + 인용정보 + 이미지 ZIP을 한 폴더로
  batch    : 여러 소장처(collections.tsv)를 차례로 manifest/download/curate
  compare  : 소장처 간 비교표(문서유형·세기) — 대량 유사 연구용
  catalog  : 사이트 전체 소장처 목록(문중·서원향교·…), --tsv 로 batch 목록 생성
  find     : 이름으로 소장처 찾기 ("동춘당 송준길"), --manifest WORK 로 바로 목록 수집
  (에디팅·매개는 studio.py: themes / edit / mediate / report)

예)
  python3 harvest.py manifest --work W --data-url '?itemId=book&gubun=booktree&depth=3&upPath=01%5E0130&dataId=L013001&itemType='
  python3 harvest.py download --work W --time 540            # 반복 실행 → 이어받기
  python3 harvest.py download --work W --category 시문류
  python3 harvest.py report --work W --out 목록.csv
  python3 harvest.py pack --work W --dest OUTDIR --prefix 동춘당 --max-mb 350
"""
import argparse, csv, html, io, json, math, os, re, sys, threading, time, zipfile
from concurrent.futures import ThreadPoolExecutor
import requests
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SITE = 'https://archive.aks.ac.kr'
VIEWER = SITE + '/viewer/'


def viewer_link(q):
    """문서 하나를 바로 여는 뷰어 주소 (해시 라우트)."""
    return SITE + '/viewer/viewer.do#imgnode.do' + q
# 주의: X-Requested-With 헤더를 넣으면 사이트 웹방화벽이 차단한다.
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130',
           'Referer': SITE + '/viewer/viewer.do'}
_tl = threading.local()


class _Adapter(requests.adapters.HTTPAdapter):
    """시스템 인증서 저장소(Windows/macOS/Linux) + certifi를 함께 신뢰 — 중간 인증서 누락 사이트 대비."""
    @staticmethod
    def _ctx():
        import ssl
        ctx = ssl.create_default_context(); ctx.load_default_certs()
        for extra in [os.environ.get('REQUESTS_CA_BUNDLE'), os.environ.get('SSL_CERT_FILE')]:
            if extra and os.path.exists(extra):
                ctx.load_verify_locations(extra)
        try:
            import certifi; ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
        return ctx

    def init_poolmanager(self, *a, **kw):
        kw['ssl_context'] = self._ctx()
        return super().init_poolmanager(*a, **kw)

    def proxy_manager_for(self, proxy, **kw):
        kw['ssl_context'] = self._ctx()
        return super().proxy_manager_for(proxy, **kw)

    def cert_verify(self, conn, url, verify, cert):
        # ssl_context가 검증을 맡으므로 requests의 기본 CA 경로 덮어쓰기를 막는다
        super().cert_verify(conn, url, verify, cert)
        if hasattr(conn, 'ca_certs'):
            conn.ca_certs = None; conn.ca_cert_dir = None


def sess():
    if not hasattr(_tl, 's'):
        s = requests.Session(); s.headers.update(HEADERS); s.trust_env = True
        s.mount('https://', _Adapter(pool_connections=4, pool_maxsize=4))
        _tl.s = s
    return _tl.s


def get(url, tries=6):
    """200이면 bytes, 404면 None, 그 외는 재시도 후 예외."""
    for i in range(tries):
        try:
            r = sess().get(url, timeout=40)
            if r.status_code == 404:
                return None
            if r.content.startswith(b'WEBFIREWALL'):
                print('  [방화벽 응답] 30초 대기', file=sys.stderr); time.sleep(30); continue
            if r.status_code == 200:
                return r.content
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    raise RuntimeError('fail ' + url)


def safe(s):
    return re.sub(r'[\\/:*?"<>|\n\r\t]', '_', s).strip()[:120]


# ---------------------------------------------------------------- manifest
NODE_RE = re.compile(r"<li data-dataId='([^']+)'\s+data-url\s*='([^']+)'\s*>\s*<span[^>]*title='([^']*)'")


def cmd_manifest(a):
    os.makedirs(a.work, exist_ok=True)
    q = a.data_url.strip().replace('&amp;', '&')
    if not q.startswith('?'):
        q = '?' + q.split('?', 1)[-1]
    docs = []

    def walk(q, path):
        t = get(VIEWER + 'treeAjax.do' + q).decode('utf-8', 'replace')
        for did, url, name in NODE_RE.findall(t):
            url, name = html.unescape(url), html.unescape(name)
            if did.startswith('G002'):
                docs.append(dict(id=did, name=name, path=path, q=url))
            else:
                walk(url, path + [name])
    walk(q, [])
    print(f'문서 {len(docs)}건 발견. 페이지 목록 수집 중...')

    def info(d):
        for _ in range(3):
            try:
                j = json.loads(get(VIEWER + 'imgnode.do' + d['q']))
                d['title'] = j.get('infoTitle')
                d['imgs'] = [dict(dzi=x['dzi'], fn=x['filename']) for x in j['imgItems']]
                return
            except Exception:
                time.sleep(2)
        d['imgs'] = []
        print('  페이지 목록 실패:', d['name'], file=sys.stderr)
    prev = {}
    pj = os.path.join(a.work, 'docs.json')
    if os.path.exists(pj):
        prev = {d['id']: d for d in json.load(open(pj)) if d.get('imgs')}
    todo = []
    for d in docs:
        if d['id'] in prev:
            d['title'], d['imgs'] = prev[d['id']].get('title'), prev[d['id']]['imgs']
        elif getattr(a, 'tree_only', False) or (getattr(a, 'match', None) and not re.search(a.match, d['name'])):
            d['title'], d['imgs'] = d['name'], []
        else:
            todo.append(d)
    if getattr(a, 'tree_only', False) or getattr(a, 'match', None):
        print(f'  페이지 목록은 {len(todo)}건만 가져옵니다 (--tree-only / --match)')
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(info, todo))
    # 분류명 = 문서 바로 위 폴더 이름 (시작 노드 바로 아래 문서면 --name 또는 dataId)
    cnt = {}
    for d in docs:
        d['category'] = d['path'][-1] if d['path'] else (a.name or re.search(r'dataId=([^&]+)', q).group(1))
        cnt[d['category']] = cnt.get(d['category'], 0) + 1
        d['folder'] = f"{cnt[d['category']]:03d}_{safe(d['name'])}"
    json.dump(docs, open(os.path.join(a.work, 'docs.json'), 'w'), ensure_ascii=False, indent=1)
    by = {}
    for d in docs:
        c = by.setdefault(d['category'], [0, 0]); c[0] += 1; c[1] += len(d['imgs'])
    for k, (n, p) in by.items():
        print(f'  {k}: 문서 {n}건 / {p}장')
    print(f'합계: 문서 {len(docs)}건 / {sum(v[1] for v in by.values())}장 → {a.work}/docs.json')


# ---------------------------------------------------------------- download
def jobs_of(a):
    docs = json.load(open(os.path.join(a.work, 'docs.json')))
    jobs = []
    for d in docs:
        if a.category and d['category'] != a.category:
            continue
        if getattr(a, 'match', None) and not re.search(a.match, d['name']):
            continue
        for k, im in enumerate(d['imgs'], 1):
            if getattr(a, 'pages', None) and k > a.pages: break
            jobs.append((os.path.join(a.work, 'out', d['category'], d['folder'], f'{k:03d}.jpg'), im['dzi']))
    return jobs


def cmd_download(a):
    jobs = jobs_of(a)
    deadline = time.time() + a.time
    tex = ThreadPoolExecutor(a.tile_workers)
    log = lambda name, line: open(os.path.join(a.work, name), 'a').write(line + '\n')

    def page(job):
        out, dzi = job
        if os.path.exists(out) or time.time() > deadline:
            return 0
        base = SITE + dzi
        x = get(base)
        if x is None:
            log('missing.txt', f'{out}\tXML404\t{base}'); return 0
        x = x.decode()
        w, h = map(int, re.search(r'Width="(\d+)" Height="(\d+)"', x).groups())
        ts = int(re.search(r'TileSize="(\d+)"', x).group(1))
        ov = int(re.search(r'Overlap="(\d+)"', x).group(1))
        L0 = math.ceil(math.log2(max(w, h)))          # 원본 해상도 레벨
        for L in range(L0, max(L0 - 4, 0), -1):        # 타일이 빠졌으면 한 단계씩 낮춤
            f = 2 ** (L0 - L); W, H = math.ceil(w / f), math.ceil(h / f)
            tb = base[:-4] + f'_files/{L}/'
            if get(tb + '0_0.jpg') is None:
                continue
            coords = [(c, r) for r in range(math.ceil(H / ts)) for c in range(math.ceil(W / ts))]
            tiles = list(tex.map(lambda cr: get(tb + '%d_%d.jpg' % cr), coords))
            if all(t is not None for t in tiles):
                break
        else:
            log('missing.txt', f'{out}\tNOTILES\t{base}'); return 0
        if L != L0:
            log('partial.txt', f'{out}\tlevel {L}/{L0} ({W}x{H}, original {w}x{h})')
        img = Image.new('RGB', (W, H))
        for (c, r), b in zip(coords, tiles):
            img.paste(Image.open(io.BytesIO(b)), (c * ts - (ov if c else 0), r * ts - (ov if r else 0)))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        img.save(out + '.tmp', format='JPEG', quality=a.quality); os.replace(out + '.tmp', out)
        return 1

    t0 = time.time(); n = 0
    with ThreadPoolExecutor(a.page_workers) as ex:
        for r in ex.map(page, jobs):
            n += r
    done = sum(os.path.exists(j[0]) for j in jobs)
    miss = set()
    p = os.path.join(a.work, 'missing.txt')
    if os.path.exists(p):
        miss = {l.split('\t')[0] for l in open(p)}
    left = len([j for j in jobs if not os.path.exists(j[0]) and j[0] not in miss])
    print(f'이번 실행 {n}장 / {time.time()-t0:.0f}s · 완료 {done}/{len(jobs)} · 서버에 없음 {len(miss & {j[0] for j in jobs})} · 남음 {left}')
    print('STATUS:', 'DONE' if left == 0 else 'CONTINUE')


# ---------------------------------------------------------------- report
def cmd_report(a):
    docs = json.load(open(os.path.join(a.work, 'docs.json')))
    rd = lambda n: [l.rstrip('\n').split('\t') for l in open(os.path.join(a.work, n))] if os.path.exists(os.path.join(a.work, n)) else []
    miss = {l[0] for l in rd('missing.txt')}
    part = {l[0]: l[1] for l in rd('partial.txt')}
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['분류', '폴더', '문서명', '자료ID(UCI)', '전체장수', '받은장수', '서버에없는장', '저해상도장', '뷰어링크'])
        for d in docs:
            ps = [os.path.join(a.work, 'out', d['category'], d['folder'], f'{k:03d}.jpg') for k in range(1, len(d['imgs']) + 1)]
            w.writerow([d['category'], d['folder'], d['name'], d['id'], len(ps), sum(os.path.exists(p) for p in ps),
                        ' '.join(os.path.basename(p) for p in ps if p in miss),
                        ' '.join(os.path.basename(p) for p in ps if p in part), viewer_link(d['q'])])
    print('→', a.out)


# ---------------------------------------------------------------- pack
def cmd_pack(a):
    os.makedirs(a.dest, exist_ok=True)
    root = os.path.join(a.work, 'out')
    if not os.path.isdir(root):
        sys.exit('받은 파일이 없습니다: ' + root)
    lim = a.max_mb * 1024 * 1024
    cats = [a.category] if a.category else sorted(os.listdir(root))
    for cat in cats:
        cdir = os.path.join(root, cat)
        files = [os.path.join(d, f) for d in sorted(os.listdir(cdir)) for f in sorted(os.listdir(os.path.join(cdir, d)))]
        parts, size = [[]], 0
        for f in files:
            s = os.path.getsize(os.path.join(cdir, f))
            if parts[-1] and size + s > lim:
                parts.append([]); size = 0
            parts[-1].append(f); size += s
        for i, p in enumerate(parts, 1):
            rng = f"{p[0][:3]}-{p[-1].split(os.sep)[0][:3]}"
            fn = f'{a.prefix}_{cat}.zip' if len(parts) == 1 else f'{a.prefix}_{cat}_part{i:02d}of{len(parts):02d}_{rng}.zip'
            with zipfile.ZipFile(os.path.join(a.dest, fn), 'w', zipfile.ZIP_STORED) as z:
                for f in p:
                    z.write(os.path.join(cdir, f), os.path.join(cat, f))
            print(f'{fn}\t{os.path.getsize(os.path.join(a.dest, fn))//2**20}MB')


# ---------------------------------------------------------------- curate (큐레이션)
TOK = re.compile(r'([가-힣]{1,10})\(([^()]+)\)')


def parse_title(t):
    """문서명에서 연도·문서유형·인명/기관을 자동 추출 (초안: 사람이 검토할 것)."""
    y = re.findall(r'(\d{4})(?:〜|~)?(\d{4})?년', t)
    ys = int(y[0][0]) if y else None
    ye = int(y[0][1]) if y and y[0][1] else ys
    toks = TOK.findall(re.sub(r'[－-]\s*\d+$', '', t))
    if toks:
        typ = toks[-1][0]
    else:  # 한자 병기가 없는 제목: 마지막 낱말(번호 제외)을 유형으로
        words = re.sub(r'[\[\]]', '', re.sub(r'[－-]\s*\d+$', '', t)).split()
        typ = words[-1] if words else t
    ents = [f'{a}({b})' for a, b in toks[:-1] if 2 <= len(a) <= 5 and re.fullmatch(r'[一-鿿]{2,5}', b)]
    return ys, ye, typ, ents


def curate_rows(work, collection=None):
    docs = json.load(open(os.path.join(work, 'docs.json')))
    rows = []
    for d in docs:
        ys, ye, typ, ents = parse_title(d['name'])
        rows.append({'소장처': collection or os.path.basename(os.path.abspath(work)), '분류': d['category'], '폴더': d['folder'],
                     '문서명': d['name'], '시작연도': ys or '', '끝연도': ye or '', '세기': (f'{(ys-1)//100+1}세기' if ys else ''),
                     '문서유형': typ, '인명·기관': '; '.join(ents), '장수': len(d['imgs']), '자료ID': d['id'], '뷰어링크': viewer_link(d['q'])})
    return rows


def write_summary(rows, path, title):
    from collections import Counter, defaultdict
    L = [f'# {title} — 큐레이션 요약 (자동 생성 초안)', '',
         f'- 문서 {len(rows)}건 / {sum(r["장수"] for r in rows)}장', '- 연도·유형·인명은 문서명에서 자동 추출한 값이라 검토가 필요함', '']
    def table(head, cnt, n=20):
        L.extend([f'## {head}', '', '| 항목 | 건수 |', '|---|---|'] + [f'| {k} | {v} |' for k, v in cnt.most_common(n)] + [''])
    table('문서 유형', Counter(r['문서유형'] for r in rows))
    table('분류', Counter(r['분류'] for r in rows))
    half = Counter(f'{r["시작연도"]//50*50}년대 후반' if r['시작연도'] and r['시작연도'] % 100 >= 50 else (f'{r["시작연도"]//50*50}년대 전반' if r['시작연도'] else '연도 미상') for r in rows)
    L.extend(['## 50년 단위 분포', '', '| 시기 | 건수 |', '|---|---|'] + [f'| {k} | {v} |' for k, v in sorted(half.items())] + [''])
    ent = Counter(e for r in rows for e in r['인명·기관'].split('; ') if e)
    table('인명·기관 상위', ent)
    tl = defaultdict(list)
    for r in rows:
        for e in r['인명·기관'].split('; '):
            if e and ent[e] >= 5:
                tl[e].append((r['시작연도'] or 9999, r['문서유형']))
    L.extend(['## 인물별 연표 (5건 이상)', ''])
    for e, v in sorted(tl.items(), key=lambda kv: -len(kv[1])):
        v.sort(); L.append(f'- **{e}** ({len(v)}건): ' + ', '.join(f'{y if y != 9999 else "?"} {t}' for y, t in v[:25]) + (' …' if len(v) > 25 else ''))
    L.extend(['', '## 에디팅·매개 아이디어 (Claude에게 요청)', '',
              '- 인물 한 명의 관직 생애를 고신·교지로 따라가는 전시 스토리라인',
              '- 혼인(납폐서·허혼서)·호적(호구단자)으로 보는 집안의 생활사 카드뉴스',
              '- 문서 유형별 대표 1점씩 고른 수업용 고문서 입문 교재', ''])
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def write_rows(rows, path):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def cmd_curate(a):
    rows = curate_rows(a.work, a.collection)
    write_rows(rows, os.path.join(a.work, 'metadata.csv'))
    with open(os.path.join(a.work, 'metadata.jsonl'), 'w', encoding='utf-8') as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    write_summary(rows, os.path.join(a.work, 'summary.md'), a.collection or os.path.basename(os.path.abspath(a.work)))
    print('→', os.path.join(a.work, 'metadata.csv'), '/ metadata.jsonl / summary.md')


# ---------------------------------------------------------------- bundle (연구 패키지)
def cmd_bundle(a):
    import shutil
    if not os.path.exists(os.path.join(a.work, 'metadata.csv')):
        cmd_curate(argparse.Namespace(work=a.work, collection=a.prefix))
    dest = os.path.join(a.dest, f'{a.prefix}_연구패키지'); os.makedirs(dest, exist_ok=True)
    for f in ['metadata.csv', 'metadata.jsonl', 'summary.md', 'missing.txt', 'partial.txt']:
        if os.path.exists(os.path.join(a.work, f)): shutil.copy(os.path.join(a.work, f), dest)
    cmd_report(argparse.Namespace(work=a.work, out=os.path.join(dest, '수집현황.csv')))
    today = time.strftime('%Y-%m-%d')
    open(os.path.join(dest, 'CITATION.txt'), 'w', encoding='utf-8').write(
        f'자료 출처: 한국학중앙연구원 한국고문서자료관 (https://archive.aks.ac.kr), {a.prefix}\n수집일: {today}\n'
        '수집 도구: aks-archive-harvester (https://github.com/changgi/archive-tools)\n'
        '이미지의 이용·재배포는 한국고문서자료관 이용 조건을 따른다.\n')
    open(os.path.join(dest, 'README.md'), 'w', encoding='utf-8').write(
        f'# {a.prefix} 연구 패키지\n\n- `metadata.csv` / `metadata.jsonl`: 문서별 연도·유형·인명(자동 추출 초안)·장수·자료ID\n'
        '- `summary.md`: 유형·시기·인물 분포와 인물별 연표\n- `수집현황.csv`: 장별 수집 결과(서버 누락·저해상도 표시)\n'
        '- `images/`: 분류별 ZIP (같은 분류 part는 한 폴더에 풀 것)\n- `CITATION.txt`: 인용 정보\n'
        '- `datapackage.json`: 데이터 설명서(Frictionless Data) — 다른 소장처 패키지와 같은 구조로 합쳐 분석\n'
        '- `edit/`, `mediate/`: 에디팅(선별·캡션)과 매개(전시·카드뉴스·수업자료) 결과가 있으면 함께 포함\n')
    for sub in ['edit', 'mediate']:
        src = os.path.join(a.work, sub)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, sub), dirs_exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(a.work, 'metadata.csv'), encoding='utf-8-sig')))
    json.dump({'name': re.sub(r'[^a-z0-9-]', '-', 'aks-' + str(abs(hash(a.prefix)) % 10**8)), 'title': f'{a.prefix} 연구 패키지',
               'sources': [{'title': '한국학중앙연구원 한국고문서자료관', 'path': 'https://archive.aks.ac.kr'}],
               'created': today, 'resources': [{'name': 'metadata', 'path': 'metadata.csv', 'format': 'csv', 'encoding': 'utf-8-sig',
                                                'schema': {'fields': [{'name': k, 'type': 'integer' if k in ('시작연도', '끝연도', '장수') else 'string'} for k in rows[0].keys()]}}]},
              open(os.path.join(dest, 'datapackage.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if not a.no_images:
        cmd_pack(argparse.Namespace(work=a.work, dest=os.path.join(dest, 'images'), prefix=a.prefix, category=None, max_mb=a.max_mb))
    print('→', dest)


# ---------------------------------------------------------------- batch / compare (대량 유사 연구)
def read_list(path):
    out = []
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#'):
            name, url = line.split('\t', 1) if '\t' in line else line.split(None, 1)
            out.append((name.strip(), url.strip()))
    return out


def cmd_batch(a):
    """collections.tsv: 한 줄에 '소장처이름<TAB>data-url'. step을 소장처마다 차례로 실행."""
    for name, url in read_list(a.list):
        work = os.path.join(a.root, safe(name)); print(f'=== {name} ({a.step})')
        if a.step == 'manifest':
            if os.path.exists(os.path.join(work, 'docs.json')) and not a.force: print('  이미 있음'); continue
            cmd_manifest(argparse.Namespace(work=work, data_url=url, name=None))
        elif a.step == 'download':
            cmd_download(argparse.Namespace(work=work, category=None, match=None, time=a.time, tile_workers=16, page_workers=2, quality=92))
            if time.time() > a._t0 + a.time: print('시간 제한 도달 — 다시 실행하면 이어서 진행'); break
        elif a.step == 'curate':
            cmd_curate(argparse.Namespace(work=work, collection=name))


def cmd_compare(a):
    from collections import Counter
    rows = []
    for name, _ in read_list(a.list):
        work = os.path.join(a.root, safe(name))
        if os.path.exists(os.path.join(work, 'docs.json')): rows += curate_rows(work, name)
    write_rows(rows, os.path.join(a.root, 'compare_metadata.csv'))
    cols = sorted({r['소장처'] for r in rows}); types = [t for t, _ in Counter(r['문서유형'] for r in rows).most_common(25)]
    L = ['# 소장처 비교 (자동 생성 초안)', '', '| 문서유형 | ' + ' | '.join(cols) + ' |', '|---|' + '---|' * len(cols)]
    for t in types: L.append(f'| {t} | ' + ' | '.join(str(sum(1 for r in rows if r['소장처'] == c and r['문서유형'] == t)) for c in cols) + ' |')
    L += ['', '| 세기 | ' + ' | '.join(cols) + ' |', '|---|' + '---|' * len(cols)]
    for cent in sorted({r['세기'] for r in rows if r['세기']}): L.append(f'| {cent} | ' + ' | '.join(str(sum(1 for r in rows if r['소장처'] == c and r['세기'] == cent)) for c in cols) + ' |')
    open(os.path.join(a.root, 'compare_summary.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('→', os.path.join(a.root, 'compare_metadata.csv'), '/ compare_summary.md', f'({len(rows)}건, 소장처 {len(cols)}곳)')


# ---------------------------------------------------------------- catalog / find (이름으로 소장처 찾기)
ROOT_Q = '?itemId=book&gubun=booktree&depth=0&upPath=&dataId=&itemType='
CACHE = os.path.join(os.path.expanduser('~'), '.aks-archive-catalog.json')


def build_catalog(levels=2, refresh=False):
    """최상위(문중·서원향교·…) → 지역 → 소장처까지 훑어 소장처 목록을 캐시."""
    if os.path.exists(CACHE) and not refresh:
        return json.load(open(CACHE, encoding='utf-8'))
    out = []

    def kids(q):
        t = get(VIEWER + 'treeAjax.do' + q).decode('utf-8', 'replace')
        return [(d, html.unescape(u), html.unescape(n)) for d, u, n in NODE_RE.findall(t)]
    for gid, gq, gname in kids(ROOT_Q):
        for rid, rq, rname in kids(gq):
            subs = kids(rq)
            if subs and all(not d.startswith('G002') for d, _, _ in subs):
                for cid, cq, cname in subs:
                    if not cid.startswith('G002'):
                        out.append(dict(id=cid, name=cname, path=[gname, rname], data_url=cq))
            else:  # 지역 단계 없이 바로 소장처인 그룹
                out.append(dict(id=rid, name=rname, path=[gname], data_url=rq))
        print(f'  {gname}: 누적 {len(out)}곳', file=sys.stderr)
    json.dump(out, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return out


def find_collections(query, refresh=False):
    cat = build_catalog(refresh=refresh)
    toks = [t for t in re.split(r'\s+', query.strip()) if t]
    def score(c):
        hay = ' '.join(c['path'] + [c['name']])
        return sum(1 for t in toks if t in hay)
    hits = sorted((c for c in cat if score(c) > 0), key=lambda c: (-score(c), c['name']))
    full = [c for c in hits if score(c) == len(toks)]
    return full or hits[:10]


def cmd_catalog(a):
    cat = build_catalog(refresh=a.refresh)
    rows = [c for c in cat if not a.group or a.group in c['path'][0]]
    if a.region: rows = [c for c in rows if any(a.region in p for p in c['path'][1:])]
    if a.tsv:
        with open(a.tsv, 'w', encoding='utf-8') as f:
            f.write('# 이름\tdata-url  (필요 없는 줄은 지우세요)\n')
            for c in rows: f.write(f"{safe(c['name'])}\t{c['data_url']}\n")
        print(f'→ {a.tsv} ({len(rows)}곳) — batch --list 로 바로 사용')
    else:
        for c in rows: print(' > '.join(c['path']), '>', c['name'], f"[{c['id']}]")
        print(f'{len(rows)}곳')


def cmd_find(a):
    hits = find_collections(a.query, a.refresh)
    if not hits:
        print('찾지 못했습니다. 지역명·성씨·인물명 등 다른 단어로 다시 시도하세요.'); return
    for i, c in enumerate(hits, 1):
        print(f"{i}. {' > '.join(c['path'])} > {c['name']}  [{c['id']}]\n   --data-url '{c['data_url']}'")
    if a.manifest:
        if len(hits) > 1 and not a.first:
            print('\n여러 곳이 맞습니다. 하나만 고르려면 검색어를 더 구체적으로 쓰거나 --first 를 붙이세요.'); return
        c = hits[0]
        cmd_manifest(argparse.Namespace(work=a.manifest, data_url=c['data_url'], name=None, tree_only=a.tree_only, match=a.match))
        meta = os.path.join(a.manifest, 'collection.json')
        json.dump(c, open(meta, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    m = sp.add_parser('manifest'); m.add_argument('--work', required=True)
    m.add_argument('--data-url', required=True, help="시작 노드의 data-url (?itemId=book&gubun=...&dataId=...)")
    m.add_argument('--name', help='시작 노드 바로 아래 문서들의 분류명(기본: dataId)')
    m.add_argument('--tree-only', action='store_true', help='문서 목록만 (페이지 목록 생략 — 큰 소장처를 빨리 훑을 때)')
    m.add_argument('--match', help='문서명 정규식 — 맞는 문서만 페이지 목록 수집 (이미 받은 것은 유지)')
    d = sp.add_parser('download'); d.add_argument('--work', required=True); d.add_argument('--category')
    d.add_argument('--pages', type=int, help='문서마다 앞에서 N장만 받기 (긴 책을 표지·첫 장만 볼 때)')
    d.add_argument('--match', help='문서명 정규식 — 맞는 문서만 받기 (예: "상량문|건치도")')
    d.add_argument('--time', type=float, default=540, help='이 시간(초)이 지나면 새 페이지를 시작하지 않음')
    d.add_argument('--tile-workers', type=int, default=16); d.add_argument('--page-workers', type=int, default=2)
    d.add_argument('--quality', type=int, default=92)
    r = sp.add_parser('report'); r.add_argument('--work', required=True); r.add_argument('--out', required=True)
    p = sp.add_parser('pack'); p.add_argument('--work', required=True); p.add_argument('--dest', required=True)
    p.add_argument('--prefix', default='AKS'); p.add_argument('--category'); p.add_argument('--max-mb', type=int, default=350)
    ct = sp.add_parser('catalog'); ct.add_argument('--group', help='문중/서원향교/박물관도서관/…'); ct.add_argument('--region')
    ct.add_argument('--tsv', help='batch용 목록 파일로 저장'); ct.add_argument('--refresh', action='store_true')
    fd = sp.add_parser('find'); fd.add_argument('query'); fd.add_argument('--manifest', metavar='WORK', help='찾은 소장처로 바로 manifest')
    fd.add_argument('--first', action='store_true'); fd.add_argument('--refresh', action='store_true')
    fd.add_argument('--tree-only', action='store_true'); fd.add_argument('--match')
    c = sp.add_parser('curate'); c.add_argument('--work', required=True); c.add_argument('--collection')
    b = sp.add_parser('bundle'); b.add_argument('--work', required=True); b.add_argument('--dest', required=True)
    b.add_argument('--prefix', required=True); b.add_argument('--max-mb', type=int, default=350); b.add_argument('--no-images', action='store_true')
    bt = sp.add_parser('batch'); bt.add_argument('--list', required=True); bt.add_argument('--root', required=True)
    bt.add_argument('--step', choices=['manifest', 'download', 'curate'], required=True); bt.add_argument('--time', type=float, default=540); bt.add_argument('--force', action='store_true')
    cp = sp.add_parser('compare'); cp.add_argument('--list', required=True); cp.add_argument('--root', required=True)
    a = ap.parse_args(); a._t0 = time.time()
    {'manifest': cmd_manifest, 'download': cmd_download, 'report': cmd_report, 'pack': cmd_pack, 'curate': cmd_curate,
     'bundle': cmd_bundle, 'batch': cmd_batch, 'compare': cmd_compare, 'catalog': cmd_catalog, 'find': cmd_find}[a.cmd](a)


if __name__ == '__main__':
    main()
