# 예시 사이트: sitemap.xml · 저장소 루트 404.html · 통합 분석 데이터셋 설명(JSON-LD)
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import re, json, os, glob, html, datetime, sys
sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts'))
import studio as ST
ROOT = (P.REPO + '/'); R = ROOT + 'examples/'; B = 'https://changgi.github.io/archive-tools/examples/'
today = datetime.date.today().isoformat()
urls = [B, B + 'en.html', B + 'analysis.html', B + 'search.html', B + 'types.html', B + 'quotes.html', B + 'timeline.html', B + 'people.html', B + 'questions.html', B + 'review.html', B + 'about.html', B + 'promote.html', B + 'use.html', B + 'tutorial/site/', B + 'tutorial/site/analysis.html']
for f in sorted(glob.glob(R + '*/exhibit.html') + glob.glob(R + '*/handout.html') + glob.glob(R + 'tutorial/site/eps/*/*.html')):
    urls.append(B + os.path.relpath(f, R).replace(os.sep, '/'))
open(R + 'sitemap.xml', 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{html.escape(u)}</loc><lastmod>{today}</lastmod></url>\n' for u in urls) + '</urlset>\n')
an = json.load(open((P.DATA + '/analysis_summary.json'), encoding='utf-8'))
ld = {'@context': 'https://schema.org', '@type': 'Dataset', 'name': '고문서 한 장 — 통합 분석 데이터',
      'description': f'한국고문서자료관 고문서 {an["docs"]}건({an["eps"]}편)의 세기 · 문서 유형 · 지역 · 정서 · 판독 · 원문 인용 집계와 편별 표. 연도·유형·인물은 문서명에서 자동 추출한 초안입니다.',
      'url': B + 'analysis.html', 'inLanguage': 'ko', 'creator': {'@type': 'Person', 'name': 'Song Chang-gi', 'url': 'https://github.com/changgi'},
      'license': 'https://creativecommons.org/licenses/by/4.0/', 'temporalCoverage': f'{an["span"][0]}/{an["span"][1]}', 'isAccessibleForFree': True,
      'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': B + 'analysis-data.json'},
                       {'@type': 'DataDownload', 'encodingFormat': 'text/csv', 'contentUrl': B + 'analysis-episodes.csv'}]}
p = R + 'analysis.html'; s = open(p, encoding='utf-8').read()
s = re.sub(r'<script type="application/ld\+json">.*?</script>', '', s, flags=re.S)
s = s.replace('</head>', '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script></head>', 1)
open(p, 'w', encoding='utf-8').write(s)
nf = f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>찾는 페이지가 없습니다 — archive-tools</title><link rel="icon" href="{ST.FAVICON}">
<style>body{{margin:0;background:#16130f;color:#efe6d4;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;line-height:1.8}}main{{max-width:720px;margin:0 auto;padding:12vh 6vw}}h1{{font-family:'Noto Serif KR',serif;font-size:clamp(28px,5vw,44px);margin:.2em 0}}.k{{color:#c4964a;letter-spacing:.18em;font-size:13px}}a{{color:#c4964a}}ul{{padding-left:20px}}li{{margin:6px 0}}p{{color:#d9cfbb}}:focus-visible{{outline:2px solid #c4964a;outline-offset:2px}}</style></head>
<body><main><p class="k">404</p><h1>이 종이는 아직 찾지 못했습니다</h1><p>주소가 바뀌었거나 잘못 적혔을 수 있습니다. 아래에서 다시 시작해 보세요.</p>
<ul><li><a href="/archive-tools/examples/">갤러리 — 「고문서 한 장」 {an["eps"]}편</a></li><li><a href="/archive-tools/examples/#map">처음 오셨나요? — 여기 있는 것 전부</a></li><li><a href="/archive-tools/examples/analysis.html">통합 분석</a></li><li><a href="/archive-tools/examples/tutorial/site/">처음부터 끝까지 따라하기</a></li><li><a href="https://github.com/changgi/archive-tools">GitHub 저장소</a></li></ul>
<p style="font-size:14px;color:#9d917c">게재에 문제가 있는 자료는 chgsong@naver.com 또는 GitHub 이슈로 알려 주시면 바로 내립니다.</p></main></body></html>'''
open(ROOT + '404.html', 'w', encoding='utf-8').write(nf)
print('sitemap', len(urls), 'urls · 404.html · JSON-LD')
