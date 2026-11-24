# examples/analysis.html — 예시 전체(101편) 통합 분석 (플러그인 analysis.py 로)
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import re, json, sys
sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts'))
import analysis as AN, series as SE, studio as ST
R = (P.REPO + '/examples/')
IT = json.loads(re.search(r'const IT=(\[.*?\]);\n', open(R + 'index.html', encoding='utf-8').read(), re.S).group(1))
eps = []; prev = ''
for i in IT:
    if not i.get('f'): continue
    coll = i['who'].split(' · ')[0]
    if coll.startswith('같은'): coll = prev
    prev = coll
    e = AN.episode(i.get('ep') or 0, i['t'], coll, R + i['f'], kind=i.get('k', ''), cards=len(i.get('cards', [])), dur=float(i.get('dr') or 0), link=f"index.html#{i['key']}")
    if not i.get('ep'): e['label'] = '기획 예시'
    e['proof'] = i['f'] + '/proof.html'
    eps.append(e)
eps_all = eps
eps = [e for e, i in zip(eps_all, [i for i in IT if i.get('f')]) if i.get('ep')]  # 통합 분석 · 숫자는 「고문서 한 장」 EP.1–EP.200만(기획 예시 3편은 갤러리에만)
body, s = AN.build(eps, '고문서 한 장')
nav = '<nav class="top"><a href="index.html">← 갤러리</a><a href="index.html#map">한눈에 보기</a><a href="analysis.html">통합 분석</a><a href="search.html">검색</a><a href="types.html">유형 사전</a><a href="quotes.html">문장</a><a href="timeline.html">연표</a><a href="people.html">인물</a><a href="questions.html">질문 카드</a><a href="review.html">검토 현황</a><a href="about.html">기획 노트</a><a href="promote.html">홍보 가이드</a><a href="use.html">활용 가이드</a><a href="tutorial/site/index.html">따라하기 예제</a></nav>'
foot = '<footer>이미지·문서: 한국학중앙연구원 한국고문서자료관 소장·제공 · 각 소장처 · 판독·번역은 이미지에 근거한 초안 · 텍스트 <a href="https://github.com/changgi/archive-tools/blob/main/LICENSE-CONTENT.md">CC BY 4.0</a>(이미지 제외) · 만든 도구: aks-archive-harvester (analysis.py) · Song Chang-gi · github.com/changgi/archive-tools</footer>'
AN.write(R + 'analysis.html', '고문서 한 장', body, nav=nav, foot=foot, base_css=SE.CSS, oh_url='media/oldhangul-sans.woff2')
AN.save_data(R, s)
AN.data_bundle(R + 'data.zip', [(('base-' if not i.get('ep') else f"ep{i['ep']:03d}-") + i['f'], R + i['f']) for i in IT if i.get('f')], R, '고문서 한 장', license='CC BY 4.0 — 출처(「고문서 한 장」 Song Chang-gi · https://changgi.github.io/archive-tools/examples/)를 밝히면 상업적 이용 · 수정 가능. 이미지는 제외(소장처 동의 필요). https://creativecommons.org/licenses/by/4.0/deed.ko')
AN.write_collections(R, eps, '고문서 한 장', nav=nav, foot=foot, base_css=SE.CSS, meta_fn=lambda fn, t, lead: ST.share_meta(t, lead, 'https://changgi.github.io/archive-tools/examples/media/share.jpg', 'https://changgi.github.io/archive-tools/examples/' + fn), oh_url='media/oldhangul-sans.woff2')
json.dump({k: v for k, v in s.items() if k != 'data'}, open((P.DATA + '/analysis_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(s['eps'], s['docs'], s['colls'], s['span'], s['han'], s['quotes']); print('\n'.join(re.sub('<[^>]+>', '', x) for x in s['insights']))
