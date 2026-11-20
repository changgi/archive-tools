# 예시 101편 전시·활동지 접근성 보완 — 큰 줄(이미지 base64)을 건드리지 않도록 </body> 앞에 작은 덧붙임 한 줄만
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import glob, re
R = (P.REPO + '/examples/')
ADD = ('<!--A11Y--><aside aria-label="이용 조건"><p style="text-align:center;font-size:12.5px;margin:24px 12px">판독 · 번역 · 해제 등 텍스트 <a href="https://github.com/changgi/archive-tools/blob/main/LICENSE-CONTENT.md" style="color:inherit;text-decoration:underline">CC BY 4.0</a> · 고문서 이미지는 소장처 동의 필요(한국고문서자료관 031-730-8873, 8876)</p></aside><style>:focus-visible{outline:2px solid #c4964a;outline-offset:2px}.dv-ba>div:first-child{opacity:1;border:1px dashed #4a3e2c;background:#1c1712}.box{color:#666}</style>'
       '<script>document.querySelectorAll(".tr").forEach(function(e,i){e.tabIndex=0;e.setAttribute("role","region");e.setAttribute("aria-label","원문 판독 "+(i+1))});'
       'document.querySelectorAll("p.meta").forEach(function(m){if(m.querySelector(".fix"))return;var t=(m.childNodes[0]&&m.childNodes[0].textContent||"").trim(),id=(m.childNodes[2]&&m.childNodes[2].textContent||"").split("·")[0].trim(),v=m.querySelector("a")?m.querySelector("a").href:"";'
       'var b="문서: "+t+"\\n자료 ID: "+id+"\\n원본 뷰어: "+v+"\\n전시: "+location.href+"\\n\\n고칠 곳(판독 · 번역 · 해제 · 연도 가운데):\\n\\n바르게 고친 내용:\\n\\n근거(원본 사진의 줄 · 다른 자료):\\n";'
       'var a=document.createElement("a");a.className="fix";a.target="_blank";a.rel="noopener";a.textContent="판독 고침 제보 ↗";a.href="https://github.com/changgi/archive-tools/issues/new?title="+encodeURIComponent("[판독 고침] "+t)+"&body="+encodeURIComponent(b)+"&labels="+encodeURIComponent("판독 고침");m.appendChild(document.createTextNode(" · "));m.appendChild(a)})</script><!--/A11Y-->\n')
n = 0
for f in glob.glob(R + '*/exhibit.html') + glob.glob(R + '*/handout.html'):  # 판독 고침 제보 링크도 함께
    s = open(f, encoding='utf-8').read()
    t = re.sub(r'<!--A11Y-->.*?<!--/A11Y-->\n?', '', s, flags=re.S)
    i = t.rfind('</body>')
    t = (t[:i].rstrip('\n') + '\n' + ADD + t[i:]) if i >= 0 else t + ADD  # 빈 줄이 쌓이지 않게
    if t != s: open(f, 'w', encoding='utf-8').write(t); n += 1
print('a11y', n)
