#!/usr/bin/env python3
"""
AKS 한국고문서자료관(archive.aks.ac.kr) 소장처 일괄 수집기.

  manifest : treeAjax.do 재귀 탐색 + imgnode.do로 문서·페이지 목록(docs.json) 생성
  download : DZI 타일을 받아 원본 해상도 JPG로 이어붙이기 (이어받기 지원, 시간제한 실행)
  report   : 문서목록 CSV (서버에 없는 장 / 저해상도 장 표시)
  pack     : 분류별 ZIP, 지정 용량(MB) 이하로 분할

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
# 주의: X-Requested-With 헤더를 넣으면 사이트 웹방화벽이 차단한다.
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130',
           'Referer': SITE + '/viewer/viewer.do'}
_tl = threading.local()


def sess():
    if not hasattr(_tl, 's'):
        s = requests.Session(); s.headers.update(HEADERS)
        s.mount('https://', requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=4))
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
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(info, docs))
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
        for k, im in enumerate(d['imgs'], 1):
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
        w.writerow(['분류', '폴더', '문서명', '자료ID(UCI)', '전체장수', '받은장수', '서버에없는장', '저해상도장'])
        for d in docs:
            ps = [os.path.join(a.work, 'out', d['category'], d['folder'], f'{k:03d}.jpg') for k in range(1, len(d['imgs']) + 1)]
            w.writerow([d['category'], d['folder'], d['name'], d['id'], len(ps), sum(os.path.exists(p) for p in ps),
                        ' '.join(os.path.basename(p) for p in ps if p in miss),
                        ' '.join(os.path.basename(p) for p in ps if p in part)])
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    m = sp.add_parser('manifest'); m.add_argument('--work', required=True)
    m.add_argument('--data-url', required=True, help="시작 노드의 data-url (?itemId=book&gubun=...&dataId=...)")
    m.add_argument('--name', help='시작 노드 바로 아래 문서들의 분류명(기본: dataId)')
    d = sp.add_parser('download'); d.add_argument('--work', required=True); d.add_argument('--category')
    d.add_argument('--time', type=float, default=540, help='이 시간(초)이 지나면 새 페이지를 시작하지 않음')
    d.add_argument('--tile-workers', type=int, default=16); d.add_argument('--page-workers', type=int, default=2)
    d.add_argument('--quality', type=int, default=92)
    r = sp.add_parser('report'); r.add_argument('--work', required=True); r.add_argument('--out', required=True)
    p = sp.add_parser('pack'); p.add_argument('--work', required=True); p.add_argument('--dest', required=True)
    p.add_argument('--prefix', default='AKS'); p.add_argument('--category'); p.add_argument('--max-mb', type=int, default=350)
    a = ap.parse_args()
    {'manifest': cmd_manifest, 'download': cmd_download, 'report': cmd_report, 'pack': cmd_pack}[a.cmd](a)


if __name__ == '__main__':
    main()
