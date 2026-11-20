# 예시 101편 검토지 — 사진은 카드 이미지의 사진 부분만 잘라 보이게(파일을 새로 만들지 않고 가리킴)
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import csv, json, os, re, sys, html
sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts'))
import studio as ST
R = (P.REPO + '/examples/')
IT = json.loads(re.search(r'const IT=(\[.*?\]);\n', open(R + 'index.html', encoding='utf-8').read(), re.S).group(1))
CROP = '<div style="aspect-ratio:1080/800;overflow:hidden;border:1px solid #ccc;background:#16130f"><img src="{src}" alt="{alt}" style="width:100%;display:block;margin-top:-6.5%"></div>'
n = 0
for i in IT:
    if not i.get('f') or (sys.argv[1:] and i['f'] not in sys.argv[1:]): continue  # 폴더 이름을 주면 그 편만
    d = R + i['f'] + '/'; sel = list(csv.DictReader(open(d + 'selection.csv', encoding='utf-8-sig')))
    todo = [r for r in sel if not (r.get('검토') or '').strip()] or sel
    def img(r):
        f = f"cards/{int(r['순서']):02d}.jpg"
        return CROP.format(src=f, alt=html.escape(r['문서명'])) if os.path.exists(d + f) else '<div class="noimg">사진 없음 — 원본 뷰어 링크로 보세요</div>'
    title = (f"EP.{i['ep']:02d} " if i.get('ep') else '') + i['t']
    open(d + 'proof.html', 'w', encoding='utf-8').write(ST.proof_html(todo, title, img).replace('<style id="oldhangul">', '<style id="oldhangul">', 1))
    n += 1
print('proof', n)
