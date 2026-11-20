# 예시 사이트 전체에 링크 미리 보기(og) 태그 넣기 — gallery/analysis/about/guides 를 다시 만든 뒤 마지막에 실행
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import re, json, os, glob, sys
sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts'))
import studio as ST
from PIL import Image
R = (P.REPO + '/examples/'); B = 'https://changgi.github.io/archive-tools/examples/'
IT = json.loads(re.search(r'const IT=(\[.*?\]);\n', open(R + 'index.html', encoding='utf-8').read(), re.S).group(1))
F = [i for i in IT if i.get('f')]
# 대표 링크 카드: 여러 편의 카드 표지를 모은 콜라주
pick = [i for i in F if i.get('ep')][::max(1, len(F) // 6)][:6]
col = Image.new('RGB', (560, 630), (22, 19, 15))
for k, i in enumerate(pick):
    im = Image.open(R + i['cover']).convert('RGB'); im.thumbnail((186, 315))
    col.paste(im, ((k % 3) * 187, (k // 3) * 316))
os.makedirs(R + 'media', exist_ok=True)
NEP = len(F)
ST.share_image(col, '고문서 한 장', f'{NEP}편 · 원문으로 읽는 옛 문서 이야기 — 영상 · 전시 · 활동지 · 카드뉴스 · 통합 분석', R + 'media/share.jpg', tag='ARCHIVE TOOLS')
an = json.load(open((P.DATA + '/analysis_summary.json'), encoding='utf-8'))
pages = {'index.html': ('고문서 한 장 — 원문으로 읽는 옛 문서 이야기', f'한국고문서자료관의 고문서 {an["docs"]}건을 한 장씩 원문으로 읽고 영상 · 전시 · 활동지 · 카드뉴스로 만든 {NEP}편. 누구나 만들 수 있는 Claude 플러그인과 따라하기 예제까지.'),
         'analysis.html': ('고문서 한 장 — 통합 분석', re.sub('<[^>]+>', '', ' '.join(an['insights'][:2]))),
         'about.html': ('고문서 한 장 — 기획 노트', '왜 만들었나 · 고른 기준 · 보이길 바란 모습 · 숫자로 본 100편 · 버전별 히스토리 · 지킨 원칙'),
         'promote.html': ('고문서 한 장 — 채널별 홍보 가이드', '인스타 · 유튜브 · 틱톡 · 페이스북 · 스레드 · X · 전시 · 책 · 웹툰 · 영상 · 광고 — 형식과 문구, 4주 계획'),
         'use.html': ('고문서 한 장 — 패키지 활용 가이드', '교사 · 학예사 · 연구자 · 기록관리자 · 문중 · 크리에이터 · 작가 · 개발자가 할 수 있는 것과 지킬 것')}
n = 0
for f, (t, d) in pages.items():
    p = R + f; s = open(p, encoding='utf-8').read()
    s = ST.put_share(s, ST.share_meta(t, d, B + 'media/share.jpg', B + ('' if f == 'index.html' else f)))
    if f == 'index.html' and 'hreflang="en"' not in s.split('</head>')[0]: s = s.replace('</head>', f'<link rel="alternate" hreflang="en" href="{B}en.html"></head>', 1)
    open(p, 'w', encoding='utf-8').write(s); n += 1
for i in F:
    d = R + i['f'] + '/'
    img = (B + i['wp']) if i.get('wp') else (B + i['f'] + '/cards/' + (i.get('cards') or ['00_표지.jpg'])[0])
    desc = (i.get('cn') or {}).get('message') or i.get('d') or ''
    lab = f"EP.{i['ep']:02d} " if i.get('ep') else ''
    for f, suf in (('exhibit.html', ''), ('handout.html', ' — 수업 활동지'), ('index.html', ' — 결과물 한눈에 보기')):
        if not os.path.exists(d + f): continue
        s = open(d + f, encoding='utf-8').read()
        open(d + f, 'w', encoding='utf-8').write(ST.put_share(s, ST.share_meta(f'📜 고문서 한 장 {lab}〈{i["t"]}〉{suf}', desc, img, B + i['f'] + '/' + f))); n += 1
print('pages', n)

# 옛한글 글꼴 조각(필요한 글자가 화면에 나올 때만 내려받음)
m = 0
for f in ['index.html', 'about.html', 'search.html', 'types.html'] + glob.glob(R + '*/exhibit.html') + glob.glob(R + '*/handout.html'):
    p = f if f.startswith('/') else R + f
    s = open(p, encoding='utf-8').read()
    rel = '../media/oldhangul-sans.woff2' if os.path.dirname(p) != R.rstrip('/') else 'media/oldhangul-sans.woff2'
    css = ST.oldhangul_css(s + ('ᄒᆞ' if f == 'index.html' else ''), url=rel)  # 갤러리는 원문을 불러와 보여 주므로 늘 준비
    t = ST.put_oldhangul(s, css)
    if t != s: open(p, 'w', encoding='utf-8').write(t); m += 1
print('oldhangul', m)
