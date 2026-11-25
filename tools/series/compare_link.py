# 예시 편마다 원문 대조 편집기로 가는 길 — examples/compare.html(편 고르기판)을 다시 만들고,
# 각 편 exhibit.html의 문서 설명 줄(p.meta)에 「원문 대조 ↗」(../compare.html#폴더)를 붙인다. 여러 번 돌려도 같은 결과.
import _paths as P
import os, re, glob, subprocess, sys
R = P.REPO + '/examples/'; ST = P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/studio.py'
subprocess.run([sys.executable, ST, 'compare', '--folder-page', R + 'compare.html'], check=True, stdout=subprocess.DEVNULL)
JS = ('<!--CMP--><script>document.querySelectorAll("p.meta").forEach(function(m){if(m.querySelector(".cmp"))return;'
      'var a=document.createElement("a");a.className="cmp";a.href="../compare.html#{key}";a.textContent="원문 대조 ↗";'
      'a.title="원본 사진과 판독을 한 줄씩 맞춰 보고 고치기";m.appendChild(document.createTextNode(" · "));m.appendChild(a)})</script><!--/CMP-->')
n = 0
for p in sorted(glob.glob(R + '*/exhibit.html')):
    key = os.path.basename(os.path.dirname(p))
    if not os.path.exists(os.path.dirname(p) + '/selection.csv'): continue
    s = open(p, encoding='utf-8').read()
    t = re.sub(r'<!--CMP-->.*?<!--/CMP-->', '', s, flags=re.S)
    t = t.replace('</body>', JS.replace('{key}', key) + '</body>', 1) if '</body>' in t else t + JS.replace('{key}', key)
    if t != s: open(p, 'w', encoding='utf-8').write(t); n += 1
print(f'compare_link: 전시 {n}편에 「원문 대조」 링크 · examples/compare.html')
