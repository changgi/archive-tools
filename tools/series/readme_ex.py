# examples/README.md 에 EP.27–50 행을 넣고 개수를 고친다 (다시 돌려도 중복 없음)
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import json, glob, csv, re, os
R = (P.REPO + '/examples/'); RM = R + 'README.md'
s = open(RM, encoding='utf-8').read()
V = P.NEXT_URL  # 영상은 archive-tools-next (media_offload.py)
J = [json.load(open(p, encoding='utf-8')) for p in glob.glob((P.DATA + '/new2/*.json'))+glob.glob((P.DATA + '/new3/*.json'))+glob.glob((P.DATA + '/new4/*.json'))]
J = sorted([j for j in J if os.path.exists(R + j['meta']['folder'] + '/selection.csv')], key=lambda j: j['meta']['ep'])
def sel(f): return list(csv.DictReader(open(R + f + '/selection.csv', encoding='utf-8-sig')))
def quote(j):
    for k in j['keep']:
        m = re.search(r'\(([^)]*[一-鿿ᄀ-ᇿ][^)]*)\)', j['docs'][str(k)]['이야기'])
        if m: return m.group(1)
    return ''
def kind(j): return j['meta']['kind']
rows_story = []; rows_ex = []; rows_card = []; rows_ed = []
for j in J:
    M = j['meta']; f = M['folder']; S = sel(f); t = M['title'].replace('|', '/')
    rows_story.append(f"| [**EP.{M['ep']} {t}**]({f}/) | {M['coll']} ({kind(j)}) | {quote(j)} | [릴스]({V}{M['id']}_reel.mp4) · [가로]({V}{M['id']}_wide.mp4) · [홍보 글]({f}/promo.md) |")
    rows_ex.append(f"| [**EP.{M['ep']} {t}**]({f}/) | {M['coll']} ({kind(j)}) | {M['lead'][:60]}{'…' if len(M['lead']) > 60 else ''} | [전시]({f}/exhibit.html) · [활동지]({f}/handout.html) · [카드]({f}/cards/) · [selection.csv]({f}/selection.csv) |")
    c2 = '02.jpg' if os.path.exists(R + f + '/cards/02.jpg') else '99_마무리.jpg'
    rows_card.append(f"| EP.{M['ep']} {t} | ![]({f}/cards/00_표지.jpg) | ![]({f}/cards/01.jpg) | ![]({f}/cards/{c2}) |")
    r = S[0]; who = ', '.join(x.strip() for x in r['인물'].split(';')[:2] if x.strip())
    before = (f"{r['연도']}년 " if r['연도'] else '') + (who + '의 ' if who else '') + r['문서유형'] + (f" — {r['유형설명']}." if r['유형설명'] else '.')
    cell = lambda x: x.replace('|', '/').replace('\n', ' ')
    rows_ed.append(f"| EP.{M['ep']} {t} | {cell(r['문서명'])} | {cell(before)} | {cell(r['이야기'])} | {cell(r['요약'])} |")
mark = '<!-- EP27+ -->'
s = re.sub(r'\n?' + re.escape(mark) + r'.*?' + re.escape(mark + 'END') + r'\n?', '\n', s, flags=re.S)  # 재실행 시 이전 삽입 제거
def after(s, anchor, rows):
    i = s.index(anchor); e = s.index('\n', i)
    return s[:e + 1] + mark + '\n' + '\n'.join(rows) + '\n' + mark + 'END\n' + s[e + 1:]
# 표 안에 HTML 주석을 넣으면 표가 끊기므로 주석 없이 넣고, 다시 돌릴 때는 행 자체로 지운다
EPS = {str(j['meta']['ep']) for j in J}  # 이 편들의 예전 행은(폴더 이름이 바뀐 것까지) 모두 지우고 새로 넣는다
s = '\n'.join(l for l in s.split('\n') if not re.match(r'\| (?:\[\*\*)?EP\.(\d+) ', l) or re.match(r'\| (?:\[\*\*)?EP\.(\d+) ', l).group(1) not in EPS)
def ins(s, anchor, rows):
    i = s.index(anchor); e = s.index('\n', i)
    return s[:e + 1] + '\n'.join(rows) + '\n' + s[e + 1:]
s = ins(s, '| [**EP.26 꽃 편지지에 쓴 왕비의 마지막 편지들**](queen-min-letters-2/) | 국립고궁박물관 (박물관) | 福壽 |', rows_story)
s = ins(s, '| [**EP.26 꽃 편지지에 쓴 왕비의 마지막 편지들**](queen-min-letters-2/) | 국립고궁박물관 (박물관) | 매화와 새', rows_ex)
s = ins(s, '| EP.26 꽃 편지지에 쓴 왕비의 마지막 편지들 | ![](queen-min-letters-2/cards/00_표지.jpg)', rows_card)
s = ins(s, '| EP.26 꽃 편지지에 쓴 왕비의 마지막 편지들 | 1886년 명성황후가 민영소에게 보낸 편지', rows_ed)
last = J[-1]['meta']['ep'] if J else 26; n = 27 + len(J)
s = re.sub(r'원문으로 읽는 이야기 \(EP\.17–EP\.\d+\)', f'원문으로 읽는 이야기 (EP.17–EP.{last})', s)
s = re.sub(r'EP\.0[13]–EP\.\d+\)는', f'EP.{J[0]["meta"]["ep"]:02d}–EP.{last})는', s)
s = re.sub(r'예시 \(결과물 갤러리\) — \d+개', f'예시 (결과물 갤러리) — {n}개', s)
s = re.sub(r'카드뉴스 미리보기 — \d+개', f'카드뉴스 미리보기 — {n}개', s)
s = re.sub(r'(?:문구 )?에디팅 전과 후 — \d+개', f'문구 에디팅 전과 후 — {n}개', s)
open(RM, 'w', encoding='utf-8').write(s)
print('rows', len(J), 'examples', n)
