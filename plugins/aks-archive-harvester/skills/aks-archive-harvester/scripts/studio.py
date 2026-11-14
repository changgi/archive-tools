#!/usr/bin/env python3
"""
aks-archive-harvester 스튜디오 — 수집한 고문서로 큐레이션 테마 → 에디팅 → 매개 산출물 만들기.
(harvest.py manifest·download·curate 이후에 사용. 이미지 처리는 Pillow만 필요, 네트워크 불필요)

  themes  : metadata.csv에서 큐레이션 테마 후보(인물 생애·생활사·시대·문서유형) 자동 제안 → themes.json
  edit    : 테마의 대표 문서 선별(시기·유형 고르게, 표지 제외) + 캡션 초안 + 이미지·밀착인화
            → WORK/edit/<테마>/selection.csv, images/, contact_sheet.jpg
  mediate : selection.csv(사람·Claude가 다듬은 캡션 반영)로
            전시 웹페이지(exhibit.html) · 카드뉴스(cards/*.png, 1080×1350) · 수업 활동지(handout.html) · SNS 글(sns.txt)
  report  : compare_metadata.csv → 소장처 비교 리포트(compare_report.html, 막대그래프)

예)
  python3 studio.py themes  --work W
  python3 studio.py edit    --work W --theme person-1 [--count 9]
  python3 studio.py edit    --work W --person 송준길 --types 고신,교지 --years 1650-1680 --title "송준길의 관직 생애"
  python3 studio.py mediate --work W --theme person-1
  python3 studio.py report  --root ROOT
"""
import argparse, base64, csv, html, io, json, os, re, sys
from collections import Counter, defaultdict
from PIL import Image, ImageDraw, ImageFont, ImageStat

Image.MAX_IMAGE_PIXELS = None

# 문서 유형 풀이 (일반적 설명 — 개별 문서 내용은 원문 확인 필요)
GLOSSARY = {
    '고신': '국왕이 관직·품계를 내린 임명장', '고신첩': '여러 고신을 묶은 첩', '교지': '국왕이 관직·작위 등을 내린 문서',
    '추증교지': '죽은 이에게 관직을 높여 내린 교지', '교지첩': '교지를 묶은 첩', '유서': '국왕이 관원에게 내린 명령서',
    '비답': '상소에 대한 국왕의 답', '녹패': '녹봉 지급을 증명한 문서', '백패': '소과(생원·진사시) 합격 증서',
    '홍패': '문과·무과 합격 증서', '시권': '과거 시험 답안지', '차첩': '하급 관직 임명장', '첩정': '하급 관청이 상급 관청에 올린 보고',
    '호구단자': '집안 식구를 관에 신고한 호적 서류', '준호구': '관에서 발급한 호적 증명서', '납폐서': '혼인 때 신랑 집이 예물과 함께 보낸 편지',
    '허혼서': '혼인을 허락하는 편지', '허혼답서': '혼인 허락에 대한 답장', '연길단자': '혼인 날짜를 정해 보낸 문서', '사주단자': '신랑의 생년월일시를 적어 보낸 문서',
    '정사': '관직을 그만두거나 휴가를 청한 글', '소지': '관에 올린 청원서', '발괄': '관에 억울함을 호소한 청원서', '완문': '권리·특혜를 확인해 준 관의 증명서',
    '자문': '물건이나 권리를 사고판 계약 문서', '명문': '토지·노비 등을 사고판 계약 문서', '분재기': '재산 상속을 기록한 문서', '고목': '하급 관리가 상관에게 올린 보고 편지',
    '이관': '관청 사이에 주고받은 공문', '도기': '모임·행사 참석자 명단', '좌목': '모임 구성원 명단', '청금록': '서원·향교 유생 명단',
    '유지': '승정원이 국왕의 뜻을 전한 문서', '상소': '신하가 국왕에게 올린 글', '포폄단자': '관원의 근무 평가 보고', '기우제문': '비를 빌며 읽은 제문',
    '토지매매명문': '토지를 사고판 계약 문서', '노비매매명문': '노비를 사고판 계약 문서', '전령': '관청이 내린 명령서', '품목': '관청에 올린 보고·청원',
    '제문': '제사 때 읽은 글', '사제문': '국왕이 내린 제문', '간찰': '편지', '서간': '편지', '치부': '재물·출납을 적은 장부',
}

def glossary(t):
    if t in GLOSSARY: return GLOSSARY[t]
    for k, v in GLOSSARY.items():
        if k in t: return v
    return ''

FAMILY_LIFE = ['납폐서', '허혼서', '허혼답서', '연길단자', '사주단자', '호구단자', '준호구', '분재기']
LETTERS = ['간찰', '서간', '제문', '만사', '고목']
NON_PERSON = {'제신', '호노', '노비', '사노', '승', '현감', '군수', '부사', '목사', '관찰사', '이방', '호장', '유생', '문중', '종중'}
OFFICE = ['고신', '교지', '추증교지', '유서', '유지', '비답', '녹패', '차첩', '백패', '홍패', '시권', '정사', '포폄단자']


def image_groups(work):
    """자료ID → (이미지 묶음 서명, 같은 이미지를 공유하는 문서 수). 첩(帖)에 든 낱장 문서들은 서버가 첩 전체 이미지를 똑같이 준다."""
    p = os.path.join(work, 'docs.json')
    if not os.path.exists(p): return {}
    docs = json.load(open(p, encoding='utf-8'))
    sig = {d['id']: tuple(i['dzi'] for i in d.get('imgs', [])) for d in docs}
    cnt = Counter(v for v in sig.values() if v)
    return {k: (v, cnt[v]) for k, v in sig.items()}


def load_rows(work):
    p = os.path.join(work, 'metadata.csv')
    if not os.path.exists(p):
        sys.exit('metadata.csv가 없습니다. 먼저 harvest.py curate --work WORK 를 실행하세요.')
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig')))
    for r in rows:
        r['_y'] = int(r['시작연도']) if r.get('시작연도') else None
        r['_ents'] = [e for e in r.get('인명·기관', '').split('; ') if e]
    return rows


def doc_images(work, r):
    d = os.path.join(work, 'out', r['분류'], r['폴더'])
    if not os.path.isdir(d): return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.jpg'))


def is_cover(path):
    im = Image.open(path); im.draft('L', (200, 200)); im = im.convert('L'); im.thumbnail((160, 160))
    return ImageStat.Stat(im).mean[0] < 140  # 어두운 표지·장정


def best_page(work, r):
    """표지·빈 면을 피해 글씨가 가장 많은 면(밝기 편차가 큰 면)을 고른다."""
    ims = doc_images(work, r)
    best, score = None, -1
    for p in ims[:8]:
        im = Image.open(p); im.draft('L', (300, 300)); im = im.convert('L'); im.thumbnail((240, 240))
        st = ImageStat.Stat(im)
        if st.mean[0] < 140: continue  # 어두운 표지·장정
        if st.stddev[0] > score: best, score = p, st.stddev[0]
    return best or (ims[0] if ims else None)


# ---------------------------------------------------------------- themes (큐레이션)
def cmd_themes(a):
    rows = load_rows(a.work)
    themes = []
    ent = Counter(e for r in rows for e in r['_ents'])
    persons = [e for e, n in ent.most_common(40) if n >= 5 and re.match(r'^[가-힣]{2,4}\(', e)
               and e.split('(')[0] not in NON_PERSON and not re.search(r'(계|청|현감|군수|부사|목사|노|도|원|사)\(', e)]
    for i, p in enumerate(persons[:5], 1):
        docs = filter_rows(rows, dict(person=p))
        ys = [r['_y'] for r in docs if r['_y']]
        types = Counter(r['문서유형'] for r in docs).most_common(4)
        themes.append(dict(id=f'person-{i}', title=f"{p.split('(')[0]}의 기록으로 본 생애", kind='인물',
                           filter=dict(person=p), count=len(docs),
                           span=f"{min(ys)}–{max(ys)}" if ys else '', note='주요 유형: ' + ', '.join(f'{t} {n}' for t, n in types)))
    fam = filter_rows(rows, dict(types=FAMILY_LIFE))
    if len(fam) >= 5:
        themes.append(dict(id='life-1', title='혼인과 호적으로 보는 집안의 생활사', kind='생활사', filter=dict(types=FAMILY_LIFE), count=len(fam), span='', note=', '.join(f'{t} {n}' for t, n in Counter(r['문서유형'] for r in fam).most_common(5))))
    let = filter_rows(rows, dict(types=LETTERS))
    if len(let) >= 5:
        themes.append(dict(id='letters-1', title='편지와 제문으로 보는 사람들 사이', kind='관계', filter=dict(types=LETTERS), count=len(let), span='', note=', '.join(f'{t} {n}' for t, n in Counter(r['문서유형'] for r in let).most_common(5))))
    off = filter_rows(rows, dict(types=OFFICE))
    if len(off) >= 5:
        themes.append(dict(id='office-1', title='임명장과 과거로 보는 관직의 길', kind='관직', filter=dict(types=OFFICE), count=len(off), span='', note=', '.join(f'{t} {n}' for t, n in Counter(r['문서유형'] for r in off).most_common(5))))
    cent = Counter(r['_y'] // 100 + 1 for r in rows if r['_y'])
    for c, n in sorted(cent.items()):
        if n >= 15:
            themes.append(dict(id=f'century-{c}', title=f'{c}세기의 집안 문서', kind='시대', filter=dict(years=f'{(c-1)*100}-{c*100-1}'), count=n, span=f'{(c-1)*100}–{c*100-1}', note=''))
    types = [t for t, n in Counter(r['문서유형'] for r in rows).most_common() if n >= 3]
    themes.append(dict(id='primer-1', title='문서 유형별 대표 한 점 — 고문서 입문', kind='교육', filter=dict(one_per_type=True, types=types[:12]), count=len(types[:12]), span='', note=', '.join(types[:12])))
    json.dump(themes, open(os.path.join(a.work, 'themes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for t in themes:
        print(f"[{t['id']}] {t['title']} — {t['count']}건 {t['span']}  {t['note']}")
    print('→', os.path.join(a.work, 'themes.json'))


# ---------------------------------------------------------------- edit (에디팅)
def pick(rows, n, one_per_type=False):
    rows = sorted(rows, key=lambda r: (r['_y'] or 9999, r['문서명']))
    if one_per_type:
        seen, out = set(), []
        for r in rows:
            if r['문서유형'] not in seen: seen.add(r['문서유형']); out.append(r)
        return out[:n]
    if len(rows) <= n: return rows
    seen, first = set(), []
    for r in rows:  # 유형마다 하나씩 먼저
        if r['문서유형'] not in seen: seen.add(r['문서유형']); first.append(r)
    first = first[:max(1, n // 2)]
    rest = [r for r in rows if r not in first]
    k = n - len(first)
    even = [rest[round(i * (len(rest) - 1) / max(1, k - 1))] for i in range(k)] if k > 0 else []
    out = []
    for r in sorted(first + even, key=lambda r: (r['_y'] or 9999, r['문서명'])):
        if r not in out: out.append(r)
    return out[:n]


def filter_rows(rows, f):
    out = rows
    if f.get('person'): out = [r for r in out if any(f['person'].split('(')[0] in e for e in r['_ents']) or f['person'].split('(')[0] in r['문서명']]
    if f.get('types'): out = [r for r in out if r['문서유형'] in f['types'] or any(t in r['문서유형'] for t in f['types'])]
    if f.get('years'):
        a, b = [int(x) for x in f['years'].split('-')]; out = [r for r in out if r['_y'] and a <= r['_y'] <= b]
    if f.get('query'): out = [r for r in out if f['query'] in r['문서명']]
    return out


def draft_caption(r):
    who = ', '.join(e.split('(')[0] for e in r['_ents'][:2])
    y = f"{r['_y']}년 " if r['_y'] else ''
    g = glossary(r['문서유형'])
    return f"{y}{who + '의 ' if who else ''}{r['문서유형']}" + (f" — {g}." if g else '.')


def cmd_edit(a):
    rows = load_rows(a.work)
    if a.theme:
        th = next((t for t in json.load(open(os.path.join(a.work, 'themes.json'), encoding='utf-8')) if t['id'] == a.theme), None)
        if not th: sys.exit('themes.json에 없는 테마입니다. studio.py themes 로 목록을 확인하세요.')
        f, title, tid = th['filter'], a.title or th['title'], th['id']
    else:
        f = dict(person=a.person, types=a.types.split(',') if a.types else None, years=a.years, query=a.query)
        title = a.title or '사용자 테마'; tid = a.id or 'custom'
    cand = [r for r in filter_rows(rows, f) if doc_images(a.work, r)]
    if not cand: sys.exit('조건에 맞고 이미지가 받아진 문서가 없습니다.')
    grp = image_groups(a.work)
    # 같은 첩 이미지를 공유하는 문서는 하나만 (첩 문서 자체를 우선)
    seen, uniq = {}, []
    for r in sorted(cand, key=lambda r: (0 if '첩' in r['문서유형'] else 1, r['_y'] or 9999)):
        g = grp.get(r['자료ID'], (None, 1))
        if g[1] > 1:
            if g[0] in seen: continue
            seen[g[0]] = True
        uniq.append(r)
    sel = pick(uniq, a.count, f.get('one_per_type', False))
    od = os.path.join(a.work, 'edit', tid); os.makedirs(os.path.join(od, 'images'), exist_ok=True)
    out = []
    for i, r in enumerate(sel, 1):
        src = best_page(a.work, r)
        shared = grp.get(r['자료ID'], (None, 1))[1]
        im = Image.open(src).convert('RGB'); im.thumbnail((1600, 1600))
        fn = f'{i:02d}.jpg'; im.save(os.path.join(od, 'images', fn), quality=88)
        out.append({'순서': i, '자료ID': r['자료ID'], '문서명': r['문서명'], '연도': r['_y'] or '', '문서유형': r['문서유형'],
                    '인물': '; '.join(e.split('(')[0] for e in r['_ents']), '유형설명': glossary(r['문서유형']),
                    '대표장': os.path.basename(src), '이미지': f'images/{fn}', '원본경로': os.path.relpath(src, a.work),
                    '캡션': draft_caption(r) + (f' (첩 이미지 {len(doc_images(a.work, r))}면 중 한 면 — 해당 면은 원문 확인 필요)' if shared > 1 else ''),
                    '이야기': '', '검토': '', '뷰어링크': r.get('뷰어링크', ''), '공유이미지': (f'{shared}건이 같은 첩 이미지를 공유' if shared > 1 else '')})
    with open(os.path.join(od, 'selection.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    json.dump(dict(id=tid, title=title, filter=f, candidates=len(cand), selected=len(out)), open(os.path.join(od, 'theme.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # 밀착인화
    cols = 3; tw, th_ = 360, 300; rows_n = (len(out) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows_n * (th_ + 60)), (245, 241, 232)); d = ImageDraw.Draw(sheet); fnt = font(22)
    for i, o in enumerate(out):
        im = Image.open(os.path.join(od, o['이미지'])); im.thumbnail((tw - 20, th_ - 20))
        x, y = (i % cols) * tw, (i // cols) * (th_ + 60)
        sheet.paste(im, (x + (tw - im.width) // 2, y + 10 + (th_ - 20 - im.height) // 2))
        d.text((x + 10, y + th_ + 8), f"{o['순서']:02d} {o['연도']} {o['문서유형']}", font=fnt, fill=(40, 30, 20))
    sheet.save(os.path.join(od, 'contact_sheet.jpg'), quality=85)
    print(f'테마 "{title}": 후보 {len(cand)}건 중 {len(out)}건 선별')
    for o in out: print(f"  {o['순서']:02d}. {o['연도']} {o['문서유형']} — {o['문서명']}")
    print('→', od, '(selection.csv의 캡션·이야기 칸을 다듬은 뒤 mediate)')


# ---------------------------------------------------------------- fonts
FONT_CANDIDATES = {
    'regular': ['C:/Windows/Fonts/malgun.ttf', '/System/Library/Fonts/AppleSDGothicNeo.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                '/usr/share/fonts/truetype/nanum/NanumGothic.ttf', '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'],
    'bold': ['C:/Windows/Fonts/malgunbd.ttf', '/System/Library/Fonts/AppleSDGothicNeo.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
             '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf', '/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc'],
    'serif': ['C:/Windows/Fonts/batang.ttc', '/System/Library/Fonts/Supplemental/AppleMyungjo.ttf', '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',
              '/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf'],
}
FONT_OVERRIDE = {}

def font(size, kind='regular'):
    for p in ([FONT_OVERRIDE[kind]] if kind in FONT_OVERRIDE else []) + FONT_CANDIDATES[kind] + FONT_CANDIDATES['regular']:
        if p and os.path.exists(p):
            idx = 1 if 'NotoS' in p and p.endswith('.ttc') else 0  # Noto CJK: KR = index 1
            try: return ImageFont.truetype(p, size, index=idx)
            except Exception: continue
    return ImageFont.load_default()


def wrap(d, text, f, width):
    lines, cur = [], ''
    for ch in text:
        if d.textlength(cur + ch, font=f) > width and cur:
            cut = cur.rfind(' ')
            if cut > len(cur) * 0.6: lines.append(cur[:cut]); cur = cur[cut + 1:] + ch
            else: lines.append(cur); cur = ch
        else: cur += ch
    if cur: lines.append(cur)
    return lines


# ---------------------------------------------------------------- mediate (매개)
INK = (24, 20, 15); PAPER = (244, 238, 226); GOLD = (196, 150, 70)

def placeholder_img(title, ident, w=980, h=740):
    """원본 이미지 대신 넣는 자리 표시 — 이미지 이용 동의 전 공개용."""
    im = Image.new('RGB', (w, h), (236, 228, 210)); d = ImageDraw.Draw(im)
    for i in range(0, w + h, 28): d.line((i, 0, i - h, h), fill=(228, 219, 199), width=10)
    d.rounded_rectangle((24, 24, w - 24, h - 24), 18, outline=(176, 150, 104), width=4)
    d.text((w / 2, h / 2 - 70), '원본 이미지 자리', font=font(44, 'bold'), fill=(120, 95, 55), anchor='ms')
    for k, ln in enumerate(wrap(d, title, font(36, 'serif'), w - 140)[:2]):
        d.text((w / 2, h / 2 + k * 48), ln, font=font(36, 'serif'), fill=INK, anchor='ms')
    d.text((w / 2, h / 2 + 120), '한국고문서자료관 뷰어에서 보기', font=font(30, 'bold'), fill=(150, 110, 50), anchor='ms')
    d.text((w / 2, h - 60), ident[:70], font=font(20), fill=(140, 125, 100), anchor='ms')
    return im


def card(img_path, title, sub, body, foot, out, size=(1080, 1350), ph=None):
    W, H = size; c = Image.new('RGB', size, (22, 19, 15)); d = ImageDraw.Draw(c)
    if ph is not None:
        c.paste(ph, ((W - ph.width) // 2, 80))
    elif img_path:
        im = Image.open(img_path).convert('RGB'); im.thumbnail((W - 100, 760))
        c.paste(im, ((W - im.width) // 2, 70 + (760 - im.height) // 2))
    y = 870
    for ln in wrap(d, title, font(56, 'bold'), W - 140)[:2]:
        d.text((70, y), ln, font=font(56, 'bold'), fill=PAPER); y += 70
    if sub: d.text((70, y + 6), sub, font=font(34, 'bold'), fill=GOLD); y += 60
    for ln in wrap(d, body, font(34), W - 140)[:5]:
        d.text((70, y + 10), ln, font=font(34), fill=(220, 210, 192)); y += 50
    d.line((70, H - 120, W - 70, H - 120), fill=(80, 70, 55), width=2)
    ff = font(24)
    for k, ln in enumerate(foot.split(' · 자료: ', 1)[:2]):
        ln = ln if k == 0 else '자료: ' + ln
        while d.textlength(ln, font=ff) > W - 140 and len(ln) > 4: ln = ln[:-2] + '…'
        d.text((70, H - 98 + k * 38), ln, font=ff, fill=(160, 150, 130))
    c.save(out, quality=92)


IMG_MAX = [1400]

def b64(path, maxw=None):
    maxw = min(maxw or IMG_MAX[0], IMG_MAX[0])
    im = path if isinstance(path, Image.Image) else Image.open(path).convert('RGB')
    im = im.copy(); im.thumbnail((maxw, maxw)); bio = io.BytesIO(); im.save(bio, 'JPEG', quality=82)
    return 'data:image/jpeg;base64,' + base64.b64encode(bio.getvalue()).decode()


def cmd_mediate(a):
    if a.font: FONT_OVERRIDE.update(regular=a.font, bold=a.font)
    IMG_MAX[0] = a.img_max
    PH = a.placeholder
    def pic(s):  # 이미지 경로 또는 자리 표시
        return placeholder_img(s['문서명'], s['자료ID']) if PH else os.path.join(ed, s['이미지'])
    def fig(s, maxw=None):
        if PH:
            link = s.get('뷰어링크') or 'https://archive.aks.ac.kr'
            return (f'<a class="ph" href="{html.escape(link)}" target="_blank" rel="noopener"><span>원본 이미지 자리</span>'
                    f'<b>{html.escape(s["문서명"])}</b><em>한국고문서자료관 뷰어에서 보기 ↗</em></a>')
        return f'<img src="{b64(os.path.join(ed, s["이미지"]), maxw)}" alt="{html.escape(s["문서명"])}">'
    ed = os.path.join(a.work, 'edit', a.theme)
    sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
    th = json.load(open(os.path.join(ed, 'theme.json'), encoding='utf-8'))
    coll = a.collection
    if not coll and os.path.exists(os.path.join(a.work, 'collection.json')):
        coll = json.load(open(os.path.join(a.work, 'collection.json'), encoding='utf-8'))['name']
    if not coll:
        mrow = next(csv.DictReader(open(os.path.join(a.work, 'metadata.csv'), encoding='utf-8-sig')), {})
        coll = mrow.get('소장처') or os.path.basename(os.path.abspath(a.work))
    title = a.title or th['title']
    od = os.path.join(a.work, 'mediate', a.theme); os.makedirs(os.path.join(od, 'cards'), exist_ok=True)
    src_line = f'자료: 한국학중앙연구원 한국고문서자료관 · {coll}'
    ys = [int(s['연도']) for s in sel if s['연도']]
    span = f'{min(ys)}–{max(ys)}' if ys else ''
    unchecked = [s for s in sel if not s.get('검토')]

    # 1) 카드뉴스
    first = os.path.join(ed, sel[0]['이미지'])
    card(first, title, f'{coll} · {span}', a.lead or f'흩어져 있던 집안 문서 {len(sel)}점으로 따라가는 이야기', src_line, os.path.join(od, 'cards', '00_표지.png'),
         ph=(placeholder_img(sel[0]['문서명'], sel[0]['자료ID']) if PH else None))
    for s in sel:
        body = (s['이야기'] or s['캡션'])
        card(os.path.join(ed, s['이미지']), f"{s['연도']} {s['문서유형']}".strip(), s['인물'], body, f"{s['문서명']} · {src_line}", os.path.join(od, 'cards', f"{int(s['순서']):02d}.png"),
             ph=(placeholder_img(s['문서명'], s['자료ID']) if PH else None))
    end = Image.new('RGB', (1080, 1350), (22, 19, 15)); d = ImageDraw.Draw(end)
    d.text((540, 560), '흩어진 기록을,', font=font(72, 'serif'), fill=PAPER, anchor='ms')
    d.text((540, 670), '다시 이야기로.', font=font(72, 'serif'), fill=GOLD, anchor='ms')
    for i, ln in enumerate([src_line, '이미지 이용은 자료관 이용 조건을 따릅니다', '만든 도구: github.com/changgi/archive-tools']):
        d.text((540, 1100 + i * 46), ln, font=font(28), fill=(170, 160, 140), anchor='ms')
    end.save(os.path.join(od, 'cards', '99_마무리.png'))

    # 2) 전시 웹페이지 (단일 HTML, 이미지 포함)
    items = []
    for s in sel:
        items.append(f"""<section class="panel"><div class="yr">{html.escape(str(s['연도']) or '연도 미상')}</div>
<figure>{fig(s)}</figure>
<div class="txt"><h2>{html.escape(s['문서유형'])}{(' · ' + html.escape(s['인물'])) if s['인물'] else ''}</h2>
<p class="cap">{html.escape(s['이야기'] or s['캡션'])}</p>
<p class="meta">{html.escape(s['문서명'])}<br>{html.escape(s['자료ID'])}{(' · <a href="' + html.escape(s['뷰어링크']) + '" target="_blank" rel="noopener">원본 보기 ↗</a>') if s.get('뷰어링크') else ''}</p>{'' if s.get('검토') else '<p class="draft">캡션 초안 — 원문 확인 전</p>'}</div></section>""")
    page = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
body{{margin:0;background:#16130f;color:#efe6d4;font-family:'Noto Serif KR','Batang',serif}}
header{{min-height:70vh;display:flex;flex-direction:column;justify-content:center;padding:8vw;background:radial-gradient(circle at 30% 40%,#3a2e1e,#16130f 70%)}}
header small{{color:#c4964a;letter-spacing:.2em}} header h1{{font-size:clamp(34px,6vw,72px);margin:.3em 0}} header p{{font-size:20px;color:#cfc3ab;max-width:42em;line-height:1.7}}
.line{{position:relative;padding:4vw 6vw}} .line:before{{content:'';position:absolute;left:calc(6vw + 38px);top:0;bottom:0;width:2px;background:#c4964a55}}
.panel{{display:grid;grid-template-columns:90px 1fr 1fr;gap:28px;align-items:center;margin:0 0 9vh}}
.yr{{font-size:26px;color:#c4964a;font-weight:700;background:#16130f;position:relative;z-index:1}}
figure{{margin:0}} figure img{{width:100%;border:8px solid #efe6d4;box-shadow:0 20px 40px #0008}} .meta a{{color:#c4964a}}
.ph{{display:flex;flex-direction:column;gap:10px;justify-content:center;align-items:center;text-align:center;aspect-ratio:4/3;padding:24px;box-sizing:border-box;text-decoration:none;color:#3a2e1e;
background:repeating-linear-gradient(135deg,#ece4d2 0 14px,#e4dbc7 14px 28px);border:8px solid #efe6d4;box-shadow:0 20px 40px #0008}}
.ph span{{font:700 15px sans-serif;letter-spacing:.15em;color:#7a5f37}} .ph b{{font-size:22px}} .ph em{{font:700 15px sans-serif;color:#9a6e2e;font-style:normal}}
h2{{font-size:28px;margin:0 0 .4em}} .cap{{font-size:19px;line-height:1.8}} .meta{{font-size:14px;color:#9d917c;font-family:sans-serif}}
.draft{{display:inline-block;font:13px sans-serif;color:#16130f;background:#c4964a;padding:3px 10px;border-radius:12px}}
footer{{padding:6vw;color:#9d917c;font:15px/1.8 sans-serif;border-top:1px solid #3a3225}}
@media(max-width:800px){{.panel{{grid-template-columns:1fr}} .line:before{{display:none}}}}
@media print{{body{{background:#fff;color:#111}} header{{min-height:auto;background:none}} .panel{{page-break-inside:avoid}}}}
</style></head><body><header><small>{html.escape(coll)} · {span}</small><h1>{html.escape(title)}</h1>
<p>{html.escape(a.lead or f'한국고문서자료관에 흩어져 있던 집안 문서 {len(sel)}점을 시간 순서로 엮었습니다.')}</p></header>
<main class="line">{''.join(items)}</main>
<footer>{html.escape(src_line)}. 이미지의 이용·재배포는 자료관 이용 조건을 따릅니다.<br>문서 유형 풀이는 일반적 설명이며, 개별 문서의 판독·해석은 원문 확인이 필요합니다.<br>제작 도구: aks-archive-harvester (github.com/changgi/archive-tools)</footer></body></html>"""
    open(os.path.join(od, 'exhibit.html'), 'w', encoding='utf-8').write(page)

    # 3) 수업 활동지 (인쇄용 HTML)
    qs = []
    for s in sel:
        qs.append(f"""<div class="q">{fig(s, 900)}<div><h3>{s['순서']}. {html.escape(str(s['연도']))} {html.escape(s['문서유형'])}</h3>
<p><b>어떤 문서?</b> {html.escape(s['유형설명'] or '—')}</p>
<p><b>찾아보기</b> ① 문서를 받은 사람(또는 쓴 사람)의 이름을 찾아 표시해 보세요. ② 날짜가 적힌 곳을 찾아보세요. ③ 도장(인장)이 있나요?</p>
<p><b>생각해 보기</b> 이 문서는 왜 지금까지 집안에 남아 있었을까요?</p></div></div>""")
    hand = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>활동지 — {html.escape(title)}</title><style>
@page{{size:A4;margin:16mm}} body{{font-family:'Malgun Gothic','Noto Sans KR',sans-serif;color:#222;font-size:14px}}
h1{{font-size:24px;margin:0}} .sub{{color:#666;margin:4px 0 16px}} .q{{display:grid;grid-template-columns:42% 1fr;gap:14px;border-top:1px solid #ccc;padding:12px 0;page-break-inside:avoid}}
.q img{{width:100%}} .ph{{display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;aspect-ratio:4/3;border:2px dashed #b89a68;color:#5a4628;text-decoration:none;padding:10px;font-size:13px}} .ph b{{font-size:15px;margin:6px 0}} .ph em{{font-style:normal;color:#9a6e2e}} h3{{margin:0 0 6px}} p{{margin:4px 0;line-height:1.6}} .box{{border:1px dashed #999;height:120px;margin-top:10px;padding:8px;color:#999}}
</style></head><body><h1>고문서로 읽는 이야기: {html.escape(title)}</h1><p class="sub">{html.escape(coll)} · {span} · 이름: ________ </p>{''.join(qs)}
<h3>정리해 보기</h3><div class="box">이 문서들을 시간 순서로 이으면 어떤 이야기가 되나요? 세 문장으로 써 보세요.</div>
<p class="sub">{html.escape(src_line)} · 이미지 이용은 자료관 이용 조건을 따릅니다.</p></body></html>"""
    open(os.path.join(od, 'handout.html'), 'w', encoding='utf-8').write(hand)

    # 4) SNS 글
    tags = ['#고문서', '#한국고문서자료관', '#기록', '#한국사'] + [f"#{s['문서유형']}" for s in sel[:3]]
    sns = [f'{title}', '', a.lead or f'{coll}에 남은 문서 {len(sel)}점으로 따라가는 이야기.', '']
    for s in sel: sns.append(f"· {s['연도']} {s['문서유형']} — {(s['이야기'] or s['캡션'])[:60]}")
    sns += ['', src_line, '이미지 이용은 자료관 이용 조건을 따릅니다.', '', ' '.join(dict.fromkeys(tags))]
    open(os.path.join(od, 'sns.txt'), 'w', encoding='utf-8').write('\n'.join(sns))
    print(f'→ {od}\n  exhibit.html(전시 웹페이지) · cards/ {len(sel)+2}장(카드뉴스) · handout.html(수업 활동지) · sns.txt')
    if unchecked: print(f'  ※ 검토 칸이 비어 있는 캡션 {len(unchecked)}건은 "초안" 표시가 붙습니다.')


# ---------------------------------------------------------------- report (비교 리포트)
def cmd_report(a):
    p = os.path.join(a.root, 'compare_metadata.csv')
    if not os.path.exists(p): sys.exit('compare_metadata.csv가 없습니다. 먼저 harvest.py compare 를 실행하세요.')
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig')))
    cols = list(dict.fromkeys(r['소장처'] for r in rows))
    types = [t for t, _ in Counter(r['문서유형'] for r in rows).most_common(a.top)]
    cents = sorted({r['세기'] for r in rows if r['세기']}, key=lambda c: int(re.sub(r'\D', '', c)))
    pal = ['#c4964a', '#7a9e9f', '#b5655b', '#8e7cc3', '#6aa84f', '#e69138', '#3d85c6', '#a64d79']
    def bars(keys, field, title):
        mx = max([sum(1 for r in rows if r['소장처'] == c and r[field] == k) for k in keys for c in cols] + [1])
        h = 30 + len(keys) * (len(cols) * 18 + 16); y = 20; svg = []
        for k in keys:
            svg.append(f'<text x="0" y="{y+12}" font-size="14">{html.escape(k)}</text>')
            for j, c in enumerate(cols):
                v = sum(1 for r in rows if r['소장처'] == c and r[field] == k); w = 520 * v / mx
                svg.append(f'<rect x="120" y="{y}" width="{w:.1f}" height="14" fill="{pal[j % len(pal)]}"/><text x="{126+w:.1f}" y="{y+12}" font-size="12">{v}</text>'); y += 18
            y += 16
        return f'<h2>{title}</h2><svg width="720" height="{h}" font-family="sans-serif">{"".join(svg)}</svg>'
    legend = ''.join(f'<span style="display:inline-block;margin-right:16px"><i style="display:inline-block;width:12px;height:12px;background:{pal[j % len(pal)]}"></i> {html.escape(c)} ({sum(1 for r in rows if r["소장처"] == c)}건)</span>' for j, c in enumerate(cols))
    page = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>소장처 비교 리포트</title><style>body{{font-family:sans-serif;max-width:860px;margin:40px auto;color:#222}} h1{{margin-bottom:4px}} .n{{color:#777}}</style></head><body>
<h1>소장처 비교 리포트</h1><p class="n">한국고문서자료관 · 소장처 {len(cols)}곳 · 문서 {len(rows)}건 · 연도·유형은 문서명에서 자동 추출한 초안</p><p>{legend}</p>
{bars(types, '문서유형', f'문서 유형 상위 {len(types)}')}{bars(cents, '세기', '세기별 분포')}</body></html>"""
    out = os.path.join(a.root, 'compare_report.html'); open(out, 'w', encoding='utf-8').write(page); print('→', out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    t = sp.add_parser('themes'); t.add_argument('--work', required=True)
    e = sp.add_parser('edit'); e.add_argument('--work', required=True); e.add_argument('--theme'); e.add_argument('--count', type=int, default=9)
    e.add_argument('--person'); e.add_argument('--types'); e.add_argument('--years', help='1650-1700'); e.add_argument('--query'); e.add_argument('--title'); e.add_argument('--id')
    m = sp.add_parser('mediate'); m.add_argument('--work', required=True); m.add_argument('--theme', required=True)
    m.add_argument('--title'); m.add_argument('--lead', help='도입 문장'); m.add_argument('--collection'); m.add_argument('--font', help='한글 글꼴 파일 경로')
    m.add_argument('--placeholder', action='store_true', help='원본 이미지 대신 "뷰어에서 보기" 자리 표시 (이미지 이용 동의 전 공개용)')
    m.add_argument('--img-max', type=int, default=1400, help='웹페이지에 넣는 이미지 최대 픽셀')
    r = sp.add_parser('report'); r.add_argument('--root', required=True); r.add_argument('--top', type=int, default=12)
    a = ap.parse_args()
    if a.cmd == 'edit' and not a.theme and not any([a.person, a.types, a.years, a.query]):
        sys.exit('--theme 또는 --person/--types/--years/--query 중 하나는 필요합니다.')
    {'themes': cmd_themes, 'edit': cmd_edit, 'mediate': cmd_mediate, 'report': cmd_report}[a.cmd](a)


if __name__ == '__main__':
    main()
