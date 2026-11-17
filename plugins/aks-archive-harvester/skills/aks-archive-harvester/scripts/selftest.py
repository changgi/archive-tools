#!/usr/bin/env python3
"""설치 확인 — 인터넷 없이 가짜 문서 3건으로 전 과정을 돌려 보고 통과 · 실패를 표로 알려 줍니다.

  python3 selftest.py [--keep] [--video]

  수집은 가짜 DZI 서버(내 컴퓨터 안)로 조각 이어 붙이기 · 낮은 해상도 대체 · 없는 면 기록을 시험하고, curate → themes → edit → (문구·노트 채우기) → delivery → check → promo
  → mediate → page → (video --no-tts) → series(통합 분석 포함) → analysis → originals → report · bundle.
  --video: ffmpeg이 있으면 영상도 시험(30초가량 더 걸림).  --keep: 시험 폴더를 지우지 않음.
  결과물은 임시 폴더에만 만들고, 실제 작업 폴더는 건드리지 않습니다.
"""
import argparse, csv, json, os, shutil, subprocess, sys, tempfile, time

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(errors='replace')
    except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DOCS = [('교령류', '1646년 홍길동(洪吉童) 진사 백패(進士白牌)', ['敎旨', '幼學洪吉童進士三等第十八人入格者', '順治三年三月初八日'], 2),
        ('소차계장류', '1720년 김복남(金福男) 소지(所志)', ['右謹言所志矣段', '民矣身窮不得已', '行下向敎是事'], 1),
        ('서간통고류', '1801년 이아무개(李某) 간찰(簡札)', ['伏惟', '寒威比劇', '不備上狀'], 3)]


def make_work(root):
    from PIL import Image, ImageDraw
    import studio as ST
    w = os.path.join(root, 'W'); os.makedirs(w)
    json.dump({'id': 'TEST', 'name': '시험 소장처 가문', 'path': ['문중', '경상북도'], 'data_url': ''}, open(os.path.join(w, 'collection.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    docs = []
    for k, (cat, name, lines, pages) in enumerate(DOCS, 1):
        folder = f'{k:03d}_{name}'; d = os.path.join(w, 'out', cat, folder); os.makedirs(d)
        for p in range(1, pages + 1):
            im = Image.new('RGB', (900, 1200), (236, 226, 204)); dr = ImageDraw.Draw(im); f = ST.font(70, 'serif')
            for c, ln in enumerate(lines):
                for r, ch in enumerate(ln[:14]): dr.text((720 - c * 120, 80 + r * 76), ch, font=f, fill=(30, 25, 20))
            im.save(os.path.join(d, f'{p:03d}.jpg'), quality=85)
        docs.append({'id': f'TEST.{k}', 'name': name, 'title': name, 'path': ['고문서', cat], 'q': f'?dataId=TEST.{k}', 'category': cat, 'folder': folder,
                     'imgs': [{'dzi': f'/dzi/T/{k}/{p}.xml', 'fn': f'{p:03d}.jpg'} for p in range(1, pages + 1)]})
    json.dump(docs, open(os.path.join(w, 'docs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return w


def fill(w):
    """문구 에디팅 · 큐레이터 노트를 사람이 한 것처럼 채우기"""
    ed = os.path.join(w, 'edit', 't'); p = os.path.join(ed, 'selection.csv')
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig'))); cols = list(rows[0].keys())
    for r in rows:
        src = next(lines for _, n, lines, _ in DOCS if n == r['문서명'])
        r['판독'] = ' '.join(src) + ' □'; r['번역'] = '시험용 번역입니다.'; r['요약'] = '시험 요약'; r['해제'] = r.get('해제') or '시험 해제'
        r['이야기'] = f'종이에는 이렇게 적혀 있다. "시험으로 옮긴 한 줄({src[1]})." 그 뒤의 일은 알 수 없다.'
    with open(p, 'w', newline='', encoding='utf-8-sig') as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
    open(os.path.join(ed, 'curator.md'), 'w', encoding='utf-8').write(
        '# 큐레이터 노트 — 시험\n\n## 왜 이 문서들인가\n시험입니다.\n\n## 전하고 싶은 것\n도구가 끝까지 돈다는 것.\n\n## 이렇게 보이길 바랐다\n순서대로.\n\n'
        '## 이렇게 써 주세요\n설치 확인에.\n\n## 만들며 있었던 일\n가짜 문서를 만들었습니다.\n\n## 남겨 둔 질문\n다음엔 어떤 문서를 열어 볼까요?\n')


def make_dzi(root, img, name, ts=254, ov=1, drop_top_tile=False):
    """가짜 서버에 올릴 DZI(확대 조각) — 원본 크기 레벨부터 1px까지. drop_top_tile: 맨 위 레벨 조각 하나를 빼서 '낮은 해상도로 받기'를 시험"""
    import math
    w, h = img.size; L0 = math.ceil(math.log2(max(w, h)))
    d = os.path.join(root, 'srv', 'dzi'); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name + '.xml'), 'w', encoding='utf-8').write(
        f'<?xml version="1.0" encoding="UTF-8"?><Image TileSize="{ts}" Overlap="{ov}" Format="jpg" xmlns="http://schemas.microsoft.com/deepzoom/2008"><Size Width="{w}" Height="{h}"/></Image>')
    for L in range(L0, max(L0 - 4, 0), -1):
        f = 2 ** (L0 - L); W, H = math.ceil(w / f), math.ceil(h / f); im = img.resize((W, H))
        td = os.path.join(d, name + '_files', str(L)); os.makedirs(td, exist_ok=True)
        for r in range(math.ceil(H / ts)):
            for c in range(math.ceil(W / ts)):
                if drop_top_tile and L == L0 and (c, r) == (1, 1): continue
                x0, y0 = c * ts - (ov if c else 0), r * ts - (ov if r else 0)
                im.crop((x0, y0, min(W, (c + 1) * ts + ov), min(H, (r + 1) * ts + ov))).save(os.path.join(td, f'{c}_{r}.jpg'), quality=95)
    return w, h


def download_test(root, res, py, S):
    """가짜 DZI 서버로 harvest.py download — 조각 이어 붙이기 · 낮은 해상도 대체 · 서버에 없는 면 기록"""
    import threading, http.server
    from PIL import Image, ImageDraw, ImageChops, ImageStat
    t = time.time()
    try:
        img = Image.new('RGB', (900, 700), (236, 226, 204)); d = ImageDraw.Draw(img)
        for k in range(0, 900, 37): d.line((k, 0, 900 - k, 700), fill=(k % 255, 80, 160), width=3)
        d.rectangle((250, 250, 520, 460), outline=(20, 20, 20), width=9)
        make_dzi(root, img, 'ok'); make_dzi(root, img, 'part', drop_top_tile=True)
        D = os.path.join(root, 'D')
        TREE = {'': [('L01', '문중')], 'L01': [('L0101', '경상북도')], 'L0101': [('ROOT', '시험 소장처 가문'), ('L0102', '다른 가문')], 'L0102': [('F9', '빈 분류')],
                'ROOT': [('F1', '시험분류')], 'F1': [('G002.T1', '시험 문서'), ('G002.T2', '다른 문서')]}
        IMGS = {'G002.T1': ['ok', 'part', 'none'], 'G002.T2': ['ok']}
        srvdir = os.path.join(root, 'srv')

        class H(http.server.SimpleHTTPRequestHandler):  # 자료관 흉내: 목록 트리(treeAjax.do) · 면 목록(imgnode.do) · 확대 조각(/dzi)
            def __init__(self, *a, **k): super().__init__(*a, directory=srvdir, **k)
            def log_message(self, *a): pass
            def do_GET(self):
                import urllib.parse as up
                u = up.urlparse(self.path); q = up.parse_qs(u.query); did = (q.get('dataId') or [''])[0]
                if u.path.endswith('/treeAjax.do'):
                    body = ''.join(f"<li data-dataId='{c}' data-url ='?itemId=book&amp;gubun=booktree&amp;dataId={c}'><span class='t' title='{n}'>{n}</span></li>" for c, n in TREE.get(did, [])).encode()
                    ctype = 'text/html; charset=utf-8'
                elif u.path.endswith('/imgnode.do'):
                    body = json.dumps({'infoTitle': did, 'imgItems': [{'dzi': f'/dzi/{x}.xml', 'filename': f'{x}.jpg'} for x in IMGS.get(did, [])]}).encode(); ctype = 'application/json'
                else: return super().do_GET()
                self.send_response(200); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
        env = dict(os.environ, AKS_SITE=f'http://127.0.0.1:{srv.server_address[1]}', NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost', HTTP_PROXY='', http_proxy='')
        m = subprocess.run([py, S('harvest.py'), 'manifest', '--work', 'D', '--data-url', '?itemId=book&dataId=ROOT', '--match', '시험 문서'], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        dj = json.load(open(os.path.join(D, 'docs.json'), encoding='utf-8')) if os.path.exists(os.path.join(D, 'docs.json')) else []
        okm = (m.returncode == 0 and len(dj) == 2 and dj[0]['category'] == '시험분류' and dj[0]['folder'] == '001_시험 문서' and len(dj[0]['imgs']) == 3 and dj[1]['imgs'] == [])
        env['AKS_CATALOG'] = os.path.join(root, 'catalog.json')  # 내 컴퓨터의 진짜 소장처 목록 캐시는 건드리지 않음
        fdr = subprocess.run([py, S('harvest.py'), 'find', '시험 소장처', '--first', '--manifest', 'D2', '--match', '시험 문서'], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        cj = os.path.join(root, 'D2', 'collection.json')
        okf = (fdr.returncode == 0 and os.path.exists(cj) and json.load(open(cj, encoding='utf-8')).get('name') == '시험 소장처 가문'
               and os.path.exists(os.path.join(root, 'D2', 'docs.json')) and len(json.load(open(os.path.join(root, 'D2', 'docs.json'), encoding='utf-8'))) == 2)
        res.append(('harvest.py find → manifest (가짜 소장처 목록)', okf, '', '' if okf else ((fdr.stderr or fdr.stdout).strip().splitlines()[-1:] or ['?'])[0]))
        res.append(('harvest.py manifest (가짜 목록 · --match)', okm, f'{time.time() - t:.1f}s', '' if okm else ((m.stderr or m.stdout).strip().splitlines()[-1:] or [f'문서 {len(dj)}건'])[0]))
        r = subprocess.run([py, S('harvest.py'), 'download', '--work', 'D', '--time', '120'], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        srv.shutdown()
        out = os.path.join(D, 'out', '시험분류', '001_시험 문서')
        a1 = Image.open(os.path.join(out, '001.jpg')).convert('RGB')
        diff = ImageStat.Stat(ImageChops.difference(a1, img)).mean
        import io as _io  # 기준: 조각 없이 JPEG로 두 번 저장했을 때의 차이(이음매가 어긋나면 이보다 크게 벌어짐)
        b1 = _io.BytesIO(); img.save(b1, 'JPEG', quality=95); b2 = _io.BytesIO(); Image.open(b1).save(b2, 'JPEG', quality=92)
        base = ImageStat.Stat(ImageChops.difference(Image.open(b2).convert('RGB'), img)).mean
        shift = ImageStat.Stat(ImageChops.difference(a1, img.transform(img.size, Image.AFFINE, (1, 0, 1, 0, 1, 0)))).mean  # 1px 어긋난 것과 비교
        a2 = Image.open(os.path.join(out, '002.jpg'))
        miss = open(os.path.join(D, 'missing.txt'), encoding='utf-8').read(); part = open(os.path.join(D, 'partial.txt'), encoding='utf-8').read()
        ok = (r.returncode == 0 and a1.size == img.size and max(diff) < max(base) + 2 and max(diff) < max(shift) and a2.size == (450, 350) and '003.jpg' in miss and '002.jpg' in part and 'STATUS: DONE' in r.stdout)
        res.append(('harvest.py download (가짜 DZI 서버)', ok, f'{time.time() - t:.1f}s', '' if ok else f'크기 {a1.size} · 차이 {max(diff):.1f}(기준 {max(base):.1f}) · 2면 {a2.size} · {r.stdout.strip().splitlines()[-1:] or r.stderr[-200:]}'))
    except Exception as e:
        res.append(('harvest.py download (가짜 DZI 서버)', False, f'{time.time() - t:.1f}s', f'{type(e).__name__}: {e}'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--keep', action='store_true'); ap.add_argument('--video', action='store_true')
    a = ap.parse_args()
    root = tempfile.mkdtemp(prefix='aks-selftest-'); print('시험 폴더:', root)
    py = sys.executable; S = lambda n: os.path.join(HERE, n)
    res = []

    def run(label, args, expect=(), ok_codes=(0,)):
        t = time.time()
        r = subprocess.run([py] + args, cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace')
        miss = [e for e in expect if not os.path.exists(os.path.join(root, e))]
        good = r.returncode in ok_codes and not miss
        res.append((label, good, f'{time.time() - t:.1f}s', '' if good else (('없음: ' + ', '.join(miss)) if miss else (r.stderr or r.stdout).strip().splitlines()[-1:][0] if (r.stderr or r.stdout).strip() else f'종료 코드 {r.returncode}')))
        return good

    try:
        w = make_work(root); res.append(('가짜 작업 폴더 만들기', True, '', ''))
    except Exception as e:
        print('가짜 작업 폴더를 만들지 못했습니다:', e); sys.exit(1)
    W = 'W'
    try: import requests  # noqa — 수집(download) 시험은 requests가 있을 때만
    except Exception: res.append(('harvest.py download (requests 없음 — 건너뜀)', True, '', 'pip install requests'))
    else: download_test(root, res, py, S)
    run('harvest.py curate', [S('harvest.py'), 'curate', '--work', W], ['W/metadata.csv', 'W/summary.md'])
    run('studio.py themes', [S('studio.py'), 'themes', '--work', W])
    run('studio.py edit', [S('studio.py'), 'edit', '--work', W, '--all', '--id', 't'], ['W/edit/t/selection.csv', 'W/edit/t/curator.md', 'W/edit/t/delivery.md', 'W/edit/t/contact_sheet.jpg'])
    try: fill(os.path.join(root, W)); res.append(('문구 에디팅 · 큐레이터 노트 채우기', True, '', ''))
    except Exception as e: res.append(('문구 에디팅 · 큐레이터 노트 채우기', False, '', str(e)))
    run('studio.py delivery', [S('studio.py'), 'delivery', '--work', W, '--theme', 't'])
    run('studio.py check (할 일 남음 → 1)', [S('studio.py'), 'check', '--work', W, '--theme', 't', '--strict'], ok_codes=(1,))
    run('studio.py promo', [S('studio.py'), 'promo', '--work', W, '--theme', 't', '--ep', '1', '--url', 'https://example.test/s/eps/01-t/exhibit.html'], ['W/mediate/t/promo.md'])
    run('studio.py fix (미리 보기)', [S('studio.py'), 'fix', '--work', W, '--theme', 't', '--n', '1', '--field', '번역', '--replace-part', '시험용', '--text', '고친']) 
    run('studio.py fix --apply', [S('studio.py'), 'fix', '--work', W, '--theme', 't', '--n', '1', '--field', '번역', '--replace-part', '시험용', '--text', '고친', '--note', '시험', '--apply'], ['W/edit/t/corrections.csv'])
    run('studio.py proof', [S('studio.py'), 'proof', '--work', W, '--theme', 't'], ['W/edit/t/proof.html'])
    run('studio.py review', [S('studio.py'), 'review', '--work', W, '--theme', 't', '--n', '1', '--by', '시험'])
    run('studio.py page', [S('studio.py'), 'page', '--work', W, '--theme', 't', '--n', '1', '--page', '002.jpg'])
    if a.video and shutil.which('ffmpeg'):
        run('video.py --no-tts', [S('video.py'), '--work', W, '--theme', 't', '--ep', '1', '--no-tts', '--web'], ['W/mediate/t/video/ep01-t_reel.mp4', 'W/mediate/t/video/ep01-t.ko.vtt'])
    run('studio.py mediate', [S('studio.py'), 'mediate', '--work', W, '--theme', 't', '--url', 'https://example.test/s/eps/01-t/exhibit.html', '--issues', 'https://github.com/example/repo'],
        ['W/mediate/t/index.html', 'W/mediate/t/exhibit.html', 'W/mediate/t/handout.html', 'W/mediate/t/channels.md', 'W/mediate/t/share.jpg', 'W/mediate/t/selection.csv'])
    open(os.path.join(root, 'series.tsv'), 'w', encoding='utf-8').write('ep\twork\ttheme\tkind\n1\tW\tt\t문중\n')
    run('series.py', [S('series.py'), '--list', 'series.tsv', '--out', 'site', '--site-url', 'https://example.test/s/'],
        ['site/index.html', 'site/analysis.html', 'site/analysis-data.json', 'site/search.html', 'site/types.html', 'site/data.zip', 'site/review.html', 'site/quotes.html', 'site/timeline.html', 'site/questions.html', 'site/sitemap.xml', 'site/share.jpg', 'site/eps/01-t/index.html'])
    os.makedirs(os.path.join(root, 'an'), exist_ok=True)
    run('analysis.py', [S('analysis.py'), '--list', 'series.tsv', '--out', 'an/analysis.html'], ['an/analysis.html', 'an/analysis-episodes.csv', 'an/quotes.html'])
    run('studio.py originals', [S('studio.py'), 'originals', '--work', W, '--theme', 't'])
    run('harvest.py report', [S('harvest.py'), 'report', '--work', W, '--out', 'report.csv'], ['report.csv'])
    run('harvest.py bundle', [S('harvest.py'), 'bundle', '--work', W, '--dest', 'pkg', '--prefix', 'test', '--no-images'])
    # 결과
    width = max(len(r[0]) for r in res)
    print('\n' + '\n'.join(f"  {'✓' if g else '✗'} {l.ljust(width)}  {t:>5}  {m}" for l, g, t, m in res))
    bad = [r for r in res if not r[1]]
    print(f'\n통과 {len(res) - len(bad)} / {len(res)}' + ('' if not bad else ' — 실패한 줄의 메시지를 확인하세요(references/troubleshooting.md).'))
    if not shutil.which('ffmpeg'): print('참고: ffmpeg이 없어 영상(video.py)은 시험하지 않았습니다.')
    elif not a.video: print('참고: 영상까지 시험하려면 --video')
    if a.keep: print('시험 폴더를 남겼습니다:', root)
    else: shutil.rmtree(root, ignore_errors=True)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
