# 저장소 README 「한눈에 보기」의 숫자를 통합 분석 요약(analysis_summary.json)에 맞춤 — 다른 빌드 뒤에
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import json, re
S = json.load(open((P.DATA + '/analysis_summary.json'), encoding='utf-8'))
p = (P.REPO + '/README.md'); s = open(p, encoding='utf-8').read()
new = f'문서 {S["docs"]}건 · 소장처 {S["colls"]}곳 · {S["span"][0]}–{S["span"][1]}년 · 판독 한자 {S["han"]:,}자 · 원문 인용 {S["quotes"]}곳'
t = re.sub(r'문서 \d+건 · 소장처 \d+곳 · \d{4}–\d{4}년 · 판독 한자 [\d,]+자 · 원문 인용 \d+곳', new, s, count=1)
import glob, csv, sys
sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts')); import analysis as AN
NP = len({x for f in glob.glob((P.REPO + '/examples/*/selection.csv')) for r in csv.DictReader(open(f, encoding='utf-8-sig')) for x in AN.persons_of(r)})
t = re.sub(r'인물 찾아보기 \d+명', f'인물 찾아보기 {NP}명', t)
t = re.sub(r'종이에 적힌 문장 \d+곳', f'종이에 적힌 문장 {S["quotes"]}곳', t)
t = re.sub(r'문서 \d+건의 판독 · 번역 · 해제 · 이야기 전문', f'문서 {S["docs"]}건의 판독 · 번역 · 해제 · 이야기 전문', t)
NEP = len([d for d in glob.glob((P.REPO + '/examples/*/selection.csv')) if '/tutorial/' not in d.replace('\\', '/')])
t = re.sub(r'「고문서 한 장」 \d+편\]', f'「고문서 한 장」 {NEP}편]', t)
if t != s: open(p, 'w', encoding='utf-8').write(t)
print('readme', 'updated' if t != s else 'same', new)
