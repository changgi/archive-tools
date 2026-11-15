#!/usr/bin/env python3
"""예시 사이트(examples/)와 루트 페이지의 상대 링크 · 그림 · 영상 주소가 실제 파일을 가리키는지 확인합니다.

  python3 tools/check_links.py [--all]     (--all: 101편의 전시 · 활동지까지 모두)
깨진 링크가 있으면 목록을 보이고 종료 코드 1.
"""
import glob, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
pages = ['index.html', '404.html'] + glob.glob('examples/*.html') + glob.glob('examples/tutorial/site/*.html') + glob.glob('examples/tutorial/site/eps/*/*.html')
if '--all' in sys.argv: pages += glob.glob('examples/*/exhibit.html') + glob.glob('examples/*/handout.html')
bad = []
for f in pages:
    s = open(f, encoding='utf-8').read(); d = os.path.dirname(f)
    for h in re.findall(r'(?:href|src)="([^"]+)"', s):
        if re.match(r'(https?:|#|mailto:|data:|javascript:)', h) or '{' in h or '${' in h: continue
        if h.startswith('/archive-tools/'): p = os.path.normpath(h[len('/archive-tools/'):].split('#')[0] or 'index.html')
        else: p = os.path.normpath(os.path.join(d, urllib.parse.unquote(h.split('#')[0].split('?')[0])))
        if not os.path.exists(p) and not os.path.exists(os.path.join(p, 'index.html')): bad.append((f, h))
print(f'페이지 {len(pages)}쪽 확인 · 깨진 링크 {len(bad)}개')
for f, h in bad[:50]: print(f'  {f}: {h}')
sys.exit(1 if bad else 0)
