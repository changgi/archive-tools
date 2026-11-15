#!/usr/bin/env python3
"""설치 확인 — 인터넷 없이 가짜 문서 3건으로 전 과정을 돌려 보고 통과 · 실패를 표로 알려 줍니다.

  python3 selftest.py [--keep] [--video]

  수집(서버 접속)만 빼고: curate → themes → edit → (문구·노트 채우기) → delivery → check → promo
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
    run('studio.py page', [S('studio.py'), 'page', '--work', W, '--theme', 't', '--n', '1', '--page', '002.jpg'])
    if a.video and shutil.which('ffmpeg'):
        run('video.py --no-tts', [S('video.py'), '--work', W, '--theme', 't', '--ep', '1', '--no-tts', '--web'], ['W/mediate/t/video/ep01-t_reel.mp4', 'W/mediate/t/video/ep01-t.ko.vtt'])
    run('studio.py mediate', [S('studio.py'), 'mediate', '--work', W, '--theme', 't', '--url', 'https://example.test/s/eps/01-t/exhibit.html', '--issues', 'https://github.com/example/repo'],
        ['W/mediate/t/index.html', 'W/mediate/t/exhibit.html', 'W/mediate/t/handout.html', 'W/mediate/t/channels.md', 'W/mediate/t/share.jpg', 'W/mediate/t/selection.csv'])
    open(os.path.join(root, 'series.tsv'), 'w', encoding='utf-8').write('ep\twork\ttheme\tkind\n1\tW\tt\t문중\n')
    run('series.py', [S('series.py'), '--list', 'series.tsv', '--out', 'site', '--site-url', 'https://example.test/s/'],
        ['site/index.html', 'site/analysis.html', 'site/analysis-data.json', 'site/quotes.html', 'site/timeline.html', 'site/questions.html', 'site/sitemap.xml', 'site/share.jpg', 'site/eps/01-t/index.html'])
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
