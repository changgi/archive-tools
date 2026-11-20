# 예시 사이트 모든 웹페이지에 공통 접근성 손질(본문 바로가기 · main · 판독 상자 이름) — 다른 빌드 스크립트 다음, 맨 마지막에
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import glob, sys
sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts'))
import studio as ST
R = (P.REPO + '/examples/')
n = 0
for f in sorted(glob.glob(R + '*.html') + glob.glob(R + '*/*.html') + glob.glob(R + '*/*/*.html')):
    if f.endswith('/proof.html'): continue  # 예시의 검토지(인쇄용)는 그대로 — <body>가 이미지 줄에 붙어 있어 고치면 패치가 커짐(새로 만드는 검토지는 도구가 손질)
    s = open(f, encoding='utf-8').read(); t = ST.put_a11y(s)
    if t != s: open(f, 'w', encoding='utf-8').write(t); n += 1
print('a11y_all', n)
