#!/usr/bin/env python3
"""
aks-archive-harvester 스튜디오 — 수집한 고문서로 큐레이션 테마 → 에디팅 → 매개 산출물 만들기.
(harvest.py manifest·download·curate 이후에 사용. 이미지 처리는 Pillow만 필요, 네트워크 불필요)

  themes  : metadata.csv에서 큐레이션 테마 후보(인물 생애·생활사·시대·문서유형) 자동 제안 → themes.json
  edit    : 테마의 대표 문서 선별(시기·유형 고르게, 표지 제외) + 캡션·해제 초안 + 이미지·밀착인화
            (selection.csv에 판독·해제·요약 칸 — 이미지를 읽고 채우면 전시·활동지에 「읽기 도움」으로 실림)
            → WORK/edit/<테마>/selection.csv, images/, contact_sheet.jpg
  mediate : selection.csv(사람·Claude가 다듬은 캡션 반영)로
            전시 웹페이지(exhibit.html) · 카드뉴스(cards/*.png, 1080×1350) · 수업 활동지(handout.html) · SNS 글(sns.txt)
  zoom    : 판독용 확대 조각(원본 해상도, 오른쪽부터) → edit/<테마>/zoom/
  promo   : 릴스 홍보 문구 틀(「고문서 한 장」 형식) → mediate/<테마>/promo.md
  report  : compare_metadata.csv → 소장처 비교 리포트(compare_report.html, 막대그래프)
  record  : 기록 꾸러미 — 편마다 record.json(맥락 · 출처 · 파생물 · 검증 · 검토 · 이력) + checksums.sha256, --verify 로 고정값 대조

예)
  python3 studio.py themes  --work W
  python3 studio.py edit    --work W --theme person-1 [--count 9]
  python3 studio.py edit    --work W --person 송준길 --types 고신,교지 --years 1650-1680 --title "송준길의 관직 생애"
  python3 studio.py mediate --work W --theme person-1
  python3 studio.py report  --root ROOT
"""
import argparse, base64, csv, glob, html, io, json, os, re, shutil, sys

for _s in (sys.stdout, sys.stderr):  # Windows에서 출력을 파일·파이프로 보낼 때(cp949) 기호 때문에 멈추지 않게
    try: _s.reconfigure(errors='replace')
    except Exception: pass


def jload(p):
    """UTF-8로 읽고, 예전 버전이 Windows 기본 인코딩(cp949)으로 쓴 파일이면 그것으로 다시 읽는다."""
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except UnicodeDecodeError:
        with open(p) as f: return json.load(f)
from collections import Counter
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
    '상량문': '건물의 마룻대를 올릴 때 공사 내력과 축원을 적은 글', '중창기': '건물을 다시 크게 일으킨 내력을 적은 기록', '중건기': '무너진 건물을 다시 세운 내력을 적은 기록',
    '사적': '절·서원 등의 역사와 내력을 적은 글', '신건문': '건물을 새로 지으며 지은 글', '헌답기': '논을 바친 사람과 내역을 적은 기록', '공덕문': '시주와 공덕을 기린 글',
    '축원문': '소원을 빌며 읽은 글', '전장기': '업무·물품을 넘겨줄 때 적은 인수인계 문서', '중기': '물품을 인수인계하며 적은 장부', '수표': '돈·물건 거래를 증명한 증서', '단자': '사실이나 물목을 적어 올린 문서',
    '윤음': '국왕이 백성에게 내린 말씀을 적은 글', '절목': '지켜야 할 규정·조항을 정리한 문서', '혼례홀기': '혼례 순서를 적은 진행표', '향약문': '마을 사람들이 지키기로 한 약속',
    '호적중초': '호적 장부를 만들기 위한 초안', '외적': '호적에서 따로 적은 명부', '효유책': '백성을 깨우쳐 타이르는 글을 묶은 책', '훈민편': '백성을 가르치는 글',
    '경임안': '서원의 임원을 적은 명부', '부보록': '서원에 재물을 낸 사람들의 기록', '원록': '서원에 출입한 유생 명부', '참제록': '제사에 참여한 사람 명부', '양안': '토지의 위치·면적·소유를 적은 장부',
    '전답양안': '논밭의 위치·면적을 적은 장부', '추수기': '거둔 곡식을 적은 장부', '건치도': '건물 배치를 그린 그림', '연계안': '생원·진사 합격자 명부', '서원지': '서원의 역사를 엮은 책', '소작계약서': '땅을 빌려 짓는 계약 문서',
    '편지': '편지', '등장': '여러 사람이 함께 관에 올린 청원서', '서목': '관에 올린 보고 문서의 요지',
    '제문': '제사 때 읽은 글', '사제문': '국왕이 내린 제문', '간찰': '편지', '서간': '편지', '치부': '재물·출납을 적은 장부',
}


# ---------------------------------------------------------------- 원문 인용 찾기 ("현대어(原文)")
QUOTE_RX = r'"([^"]{2,240}?)"'
_ORIG = re.compile(r'[㐀-䶿一-鿿豈-﫿ᄀ-ᇿꥠ-꥿ힰ-퟿ㆍᆞ]')


def find_quotes(text):
    """이야기 속 "현대어(原文)" 인용 → [(현대어, 원문, 따옴표 안 전체)]. 원문은 한자·옛한글이 든 괄호. "(1646)" 같은 연도 괄호는 빼고 셈.
    원문 괄호가 따옴표 끝이 아니라 가운데 있어도("…하오니(원문), 그 밖에 …"), 원문(현대어) 순서여도 인용으로 본다."""
    out = []
    for m in re.finditer(QUOTE_RX, text or ''):
        inner = m.group(1)
        for p in re.finditer(r'\(([^()]+)\)', inner):
            rest = re.sub(r'\([^()]*\)', '', inner[:p.start()] + inner[p.end():]).strip(' ,.')
            if _ORIG.search(p.group(1)):  # 현대어(原文)
                if len(rest) >= 2: out.append((rest, p.group(1).strip(), inner)); break
            elif _ORIG.search(rest) and re.search('[가-힣]', p.group(1)) and len(p.group(1)) >= 4:  # 原文(현대어) — 옛한글 편지 등
                out.append((p.group(1).strip(), rest, inner)); break
    return out

def _qnorm(t):
    """인용 대조용: 띄어쓰기 · 문장부호 · (?) · 줄바꿈을 빼고 같은 꼴(NFC)로"""
    import unicodedata
    t = unicodedata.normalize('NFC', t or '').replace('(?)', '')
    return re.sub(r'[\s　·,.、。○\-—()（）\[\]「」『』"\'?!:;/]', '', t)


def quote_issues(row):
    """이야기 속 "현대어(原文)"의 原文이 그 문서의 원문 · 판독(또는 문서명)에 그대로 있는지 → [(인용 원문, 무엇이 문제인지)]
    「…」로 나눈 토막마다 대조. 중간 글자를 건너뛰었으면 「…」를 넣으라고, 아예 없으면 원문 확인하라고 알린다."""
    src = _qnorm((row.get('원문') or '') + '|' + (row.get('판독') or '') + '|' + (row.get('문서명') or ''))
    src = src.replace('□', '')
    out = []
    for _, orig, _ in find_quotes(row.get('이야기')):
        for seg in re.split(r'…|\.\.\.', orig):
            g = _qnorm(seg).replace('□', '')
            if len(g) < 2 or g in src: continue
            best = max((L for L in range(len(g), 1, -1) if any(g[i:i + L] in src for i in range(len(g) - L + 1))), default=0)
            out.append((orig, f'「{seg.strip()}」 — 원문 · 판독에 그대로 없음' + (f'(앞뒤 {best}/{len(g)}자만 이어짐: 사이에 빠진 글자가 있으면 「…」로 표시)' if best >= len(g) // 2 else ' — 원문 확인')))
    return out


def persons(row):
    """「인물」 칸에서 사람 이름만(직함 · 관청 · 고을 · 절 · 산 · 성씨만 있는 것은 뺌) — 카드 · 전시 · 홍보 태그용. 기준은 analysis.persons_of"""
    import analysis
    return analysis.persons_of(row)


def glossary(t):
    if t in GLOSSARY: return GLOSSARY[t]
    for k, v in GLOSSARY.items():
        if k in t: return v
    return ''

# 문서 유형별 "읽는 법" — 해제(解題) 초안에 쓰는 일반 서식 설명 (개별 문서의 내용은 원문 판독으로 확인)
READ_GUIDE = [
    ('추증교지', "세상을 떠난 사람(대개 관원의 부모·조상·아내)에게 벼슬이나 작호를 높여 내린 교지입니다. 이름 앞에 '贈'(추증)이 붙고, 아내에게는 '淑夫人→貞夫人' 같은 외명부 작호가 내려집니다. 보통 자손이나 남편의 품계가 오를 때 함께 내려졌습니다."),
    ('증시교지', "세상을 떠난 신하에게 시호(諡號, 생애를 기리는 이름)를 내린 교지입니다. '贈諡○○公'처럼 적고, 시호 글자마다 뜻풀이가 덧붙기도 합니다."),
    ('홍패', "문과·무과 대과 합격 증서입니다. 붉은 종이에 '敎旨' 다음으로 이름, 시험 종류(文科·武科), 등급(甲科·乙科·丙科)과 등수가 적히고, 끝에 연호·날짜와 임금 도장이 찍힙니다."),
    ('백패', "생원·진사시(소과) 합격 증서입니다. 흰 종이에 이름과 등급·등수, 연호·날짜가 적힙니다."),
    ('녹패', "관원에게 녹봉(봉급)을 주라는 증서입니다. 받는 사람의 품계·관직, 녹봉 등급(第○科), 날짜가 적힙니다."),
    ('조사첩', "고려 말~조선 초 관원을 임명할 때 대간(臺諫)의 동의(서경)를 거쳤음을 적어 준 문서입니다. 임명장 서식이 자리 잡기 전 시기의 문서라 남아 있는 예가 드뭅니다."),
    ('고신첩', "여러 장의 고신(임명장)을 한 첩으로 묶은 것입니다. 면마다 다른 시기의 임명장이 붙어 있어, 어느 면이 어느 문서인지는 원문을 보며 확인해야 합니다."),
    ('교지첩', "여러 장의 교지를 한 첩으로 묶은 것입니다. 면마다 시기와 내용이 다릅니다."),
    ('고신', "조선시대 관직 임명장입니다. 첫머리 '敎旨'(임금의 명령) 다음에 받는 사람 이름과 '爲○○者'(○○으로 삼는다)가 오고, 마지막 줄에 연호와 날짜, 그 위에 임금 도장이 찍힙니다. 앞의 '○○大夫·○○郞'은 품계(등급), 뒤의 '行·守 ○○'은 실제로 맡은 자리입니다."),
    ('교지', "임금이 관직·품계·작위·토지 등을 내릴 때 쓴 문서입니다. 첫머리 '敎旨' 다음에 받는 사람과 내용이 오고, 끝에 연호·날짜와 임금 도장이 찍힙니다."),
    ('유지', "승정원 승지가 임금의 뜻을 받들어 특정 관원에게 전한 명령서입니다. '有旨' 뒤에 명령이 오고, 끝에 날짜와 승지의 직함이 적힙니다. 지방에 있는 사람을 부를 때 '乘馹上來'(역마를 타고 올라오라) 같은 표현이 쓰입니다."),
    ('유서', "임금이 관찰사·병사·수령 등 지방관이나 장수에게 직접 내린 명령서입니다. 군사권을 맡길 때 함께 내리기도 했습니다."),
    ('비답', "신하가 올린 상소에 임금이 내린 답입니다. 상소를 받아들이는지, 위로하거나 만류하는지가 짧게 적힙니다."),
    ('정사', "관원이 사직이나 휴가를 청하며 올린 글입니다. 사유와 청하는 내용, 날짜, 올린 사람의 직함과 이름이 적히고, 처리 결과가 덧붙기도 합니다."),
    ('준호구', "호적대장에 올라 있는 내용을 관에서 베껴 확인해 준 호적 증명서입니다. 주소, 호주의 직역·이름·나이·본관, 4조(아버지·할아버지·증조·외할아버지), 아내, 자녀, 노비 순으로 적히고 관인이 찍힙니다."),
    ('호구단자', "호주가 3년마다 식구를 관에 신고한 서류입니다. 주소, 호주, 4조(아버지·할아버지·증조·외할아버지), 아내, 자녀, 노비 순서로 적습니다."),
    ('화회문기', "부모가 세상을 떠난 뒤 자녀들이 모여 의논해 재산을 나눈 문서입니다. 받는 사람별로 노비·논밭이 나열되고, 끝에 형제자매의 이름과 수결(서명)이 있습니다."),
    ('분재기', "재산을 자녀에게 나눠 준 문서입니다. 받는 사람별로 노비·논밭이 나열됩니다."),
    ('명문', "땅·집·노비를 사고판 계약서입니다. '○年 ○月 ○日 ○○前明文'으로 시작해 파는 이유, 대상, 값, 뒷날 문제가 생기면 이 문서로 증명한다는 다짐, 판 사람·증인·쓴 사람(필집)의 이름과 수결이 이어집니다."),
    ('납폐서', "혼인 때 신랑 집에서 예물(폐백)을 보내며 함께 보낸 편지입니다. 혼인을 정중히 청하는 정해진 문구, 날짜, 보내는 사람 이름이 적힙니다."),
    ('허혼', "신랑 집의 청혼에 신부 집이 혼인을 허락한다고 보낸 답장입니다."),
    ('연길단자', "혼례 날짜(길일)를 골라 상대 집에 알린 문서입니다."),
    ('사주단자', "신랑의 생년월일시(사주)를 적어 신부 집에 보낸 문서입니다."),
    ('위장', "상을 당한 사람에게 보낸 위로 편지입니다."),
    ('간찰', "한문 편지입니다. 흘림 글씨(초서)로 써서 판독이 어렵습니다. 대개 안부 → 용건 → 날짜·이름 순서입니다."),
    ('편지', "편지입니다. 한글 편지(언간)는 흘림체로 세로로 쓰고 오른쪽 줄부터 읽습니다. 종이가 모자라면 여백이나 줄 사이에 이어 써서 읽는 순서가 복잡해지기도 합니다. 받는 사람에 대한 높임말과 안부로 시작하는 경우가 많습니다."),
    ('고목', "아전(하급 관리)이나 노비가 상전에게 올린 짧은 보고 편지입니다. '告目'으로 시작하고 상전을 높이는 표현을 씁니다."),
    ('첩정', "하급 관청이 상급 관청에 올린 공식 보고서입니다. 보고 내용 뒤에 날짜와 보고한 관원의 직함, 관인이 있습니다."),
    ('상량문', "건물의 마룻대(상량)를 올릴 때 지은 글입니다. 건물의 내력과 공사 경위를 적고, 동서남북·위아래를 향한 축원('兒郞偉'로 시작하는 노래)이 이어지며, 끝에 날짜와 지은 이가 적힙니다."),
    ('중수기', "낡은 건물을 고친 경위를 적은 글입니다. 공사 시기, 주관한 사람, 비용을 낸 사람 등이 나옵니다."),
    ('중건기', "무너진 건물을 다시 세운 경위를 적은 글입니다. 공사 시기, 주관한 사람, 시주한 사람 등이 나옵니다. 절에서는 나무판에 새겨 걸어 두기도 했습니다."),
    ('신건문', "건물을 새로 지으며 그 내력과 축원을 적은 글입니다."),
    ('공덕문', "시주한 사람들의 공덕을 기린 글입니다. 시주자 이름과 시주 내역이 나열됩니다."),
    ('헌답기', "절에 논(畓)을 바친 사람과 논의 위치·크기를 적은 기록입니다. 바친 사람의 명복이나 제사를 부탁하는 내용이 함께 적히곤 합니다."),
    ('사적', "절이나 서원이 스스로 정리한 역사입니다. 창건 내력, 중건, 주요 인물과 사건을 시대 순으로 적습니다."),
    ('복장기', "불상을 만들 때 불상 안에 넣은 물건(경전·사리·곡식 등)과 조성 경위, 시주자를 적은 기록입니다."),
    ('원문', "부처에게 소원을 빌며 올린 글(願文)입니다. 발원한 사람, 소원, 연호·날짜가 적힙니다."),
    ('기일록', "제사를 지낼 날(돌아가신 날)을 모아 적은 기록입니다."),
    ('전장기', "맡던 일과 물건을 다음 사람에게 넘겨줄 때 목록을 적은 인수인계 문서입니다."),
    ('전여기', "맡던 일과 물건을 다음 사람에게 넘겨줄 때 목록을 적은 인수인계 문서입니다."),
    ('계안', "계(契) 구성원의 명단과 규약을 적은 책입니다."),
    ('절목', "관청이나 마을이 지켜야 할 규정을 조목조목 적은 문서입니다. 앞에 규정을 만든 까닭(서문)이 오고, '一'로 시작하는 조항이 이어지며, 끝에 날짜와 관인·담당자 서명이 있습니다."),
    ('완문', "관청이 특정 기관이나 마을의 권리·면제를 확인해 준 증명서입니다. 서원·향교·마을이 부역이나 침탈을 면제받을 때 받았고, '勿侵'(침범하지 말라) 같은 조항이 나옵니다."),
    ('등장', "여러 사람이 이름을 나란히 적어 관청에 올린 청원서입니다. 사연을 적은 본문 뒤에 청원자 명단이 있고, 문서 왼쪽 아래 여백에 관청의 처분(題辭)이 다른 글씨로 적힙니다."),
    ('소지', "개인이 관청에 올린 청원서입니다. 본문 뒤 여백에 관청의 처분(題辭)이 적힙니다."),
    ('윤음', "임금이 백성이나 관원에게 직접 알리는 말씀을 인쇄해 나눠 준 글입니다. 흉년 구제, 세금 감면, 풍속 교화 등을 다루며, 한문 본문에 한글 번역(언해)이 함께 실리기도 합니다."),
    ('향약', "마을 사람들이 서로 지키기로 한 약속(덕을 권하고 잘못을 바로잡고 어려울 때 돕는 일)을 적은 글입니다."),
    ('홀기', "의식(제례·혼례 등)의 순서를 적은 진행표입니다. 진행자가 소리 내어 읽어 순서를 알렸습니다."),
    ('양안', "토지 대장입니다. 논밭의 위치(자호·지번), 모양, 크기(결부), 등급, 주인이 적힙니다."),
    ('봉안록', "사당·서원에 위패를 모신 일의 경위와 절차, 참여한 사람을 적은 기록입니다."),
    ('노비안', "기관이나 집안에 딸린 노비의 이름·나이·부모 등을 적은 명부입니다."),
    ('변무록', "억울한 비방(무고)을 해명한 글과 관련 문서를 모은 책입니다."),
    ('계첩', "관원들의 모임(계회)을 기념해 그림과 참석자 명단을 함께 엮은 첩입니다."),
    ('원생록', "서원에 드나든 유생들의 이름을 적은 명부입니다."),
    ('임안', "일을 맡은 사람들(임원)의 명단입니다."),
    ('집사록', "의식이나 공사 때 일을 맡은 사람들의 명단입니다."),
    ('경로회', "어른을 공경하는 모임의 참석자 명단입니다."),
    ('상소', "신하나 유생이 임금에게 올린 글입니다. 여러 사람이 함께 올리면 끝에 이름이 길게 이어집니다."),
    ('소문', "임금에게 올린 상소문입니다. 여러 사람이 함께 올리면 끝에 이름이 길게 이어집니다."),
    ('소본', "임금에게 올린 상소의 원고(초본)입니다."),
    ('소축', "두루마리로 만든 상소입니다."),
    ('회통', "여러 사람·마을에 돌려 가며 알린 글입니다."),
    ('고시', "관청이 주민에게 알린 공고문입니다."),
    ('신청', "근대 토지·산림 제도에서 소유권을 신고하거나 증명받으려고 낸 서류입니다. 신청인, 땅의 위치·면적, 근거가 정해진 서식에 맞춰 적힙니다."),
    ('정관', "조합·단체의 규칙입니다. 장(章)과 조(條)로 나뉘어 있습니다."),
    ('환곡', "봄에 곡식을 빌려주고 가을에 돌려받던 환곡의 분배 장부입니다."),
    ('원규', "서원을 운영하는 규칙입니다."),
    ('건치도', "건물의 배치를 그린 그림입니다."),
    ('기사', "있었던 일을 적은 기록입니다."),
]

def read_guide(t):
    for k, v in READ_GUIDE:
        if k in t: return v
    return ''

def draft_haeje(r):
    """해제 초안: 언제·누가·무엇 + 서식 읽는 법 (개별 내용은 원문 확인 후 고칠 것)"""
    who = ', '.join(e.split('(')[0] for e in r['_ents'][:2])
    y = (f"{r['_y']}년" + ('(자료관이 매긴 연대 — 원문 날짜로 확인)' if r.get('연도근거') == '자료ID' else '')) if r['_y'] else '연대 미상'
    head = f"{y}{' ' + who + ' 관련' if who else ''} {r['문서유형']}."
    return (head + ' ' + read_guide(r['문서유형'])).strip()

FAMILY_LIFE = ['납폐서', '허혼서', '허혼답서', '연길단자', '사주단자', '호구단자', '준호구', '분재기']
LETTERS = ['간찰', '서간', '제문', '만사', '고목']
NON_PERSON = {'제신', '호노', '노비', '사노', '승', '현감', '군수', '부사', '목사', '관찰사', '이방', '호장', '유생', '문중', '종중'}
OFFICE = ['고신', '교지', '추증교지', '유서', '유지', '비답', '녹패', '차첩', '백패', '홍패', '시권', '정사', '포폄단자']


def image_groups(work):
    """자료ID → (이미지 묶음 서명, 같은 이미지를 공유하는 문서 수). 첩(帖)에 든 낱장 문서들은 서버가 첩 전체 이미지를 똑같이 준다."""
    p = os.path.join(work, 'docs.json')
    if not os.path.exists(p): return {}
    docs = jload(p)
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


def thin_pages(paths):
    """같은 문서의 다른 면보다 눈에 띄게 작고(면적) 글씨도 적은(바이트/픽셀) 면 — 두루마리 겉면·싸개·표지일 가능성."""
    if len(paths) < 2: return set()
    m = {}
    for p in paths:
        try:
            with Image.open(p) as im: w, h = im.size
            m[p] = (w * h, os.path.getsize(p) / max(1, w * h))
        except Exception: pass
    if len(m) < 2: return set()
    areas = sorted(v[0] for v in m.values()); bpps = sorted(v[1] for v in m.values())
    ma, mb = areas[len(areas) // 2], bpps[len(bpps) // 2]
    return {p for p, (ar, bp) in m.items() if ar < 0.6 * ma and bp < 0.6 * mb}


def best_page(work, r):
    """대표 면: 앞에서부터 보아 표지·빈 면(뒷면)·겉면이 아닌 첫 면. 없으면 글씨가 가장 많은 면."""
    ims = doc_images(work, r)
    thin = thin_pages(ims[:8])
    best, score = None, -1
    for p in ims[:8]:
        if p in thin: continue  # 두루마리 겉면·싸개처럼 작고 글씨가 적은 면
        im = Image.open(p); im.draft('L', (300, 300)); im = im.convert('L'); im.thumbnail((240, 240))
        st = ImageStat.Stat(im)
        if st.mean[0] < 140: continue  # 어두운 표지·장정
        if st.stddev[0] >= 30: return p  # 글씨가 충분한 첫 면
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
        f = {} if a.all else dict(person=a.person, types=a.types.split(',') if a.types else None, years=a.years, query=a.query)
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
                    '대표장': os.path.basename(src), '이미지': f'images/{fn}', '원본경로': os.path.relpath(src, a.work).replace(os.sep, '/'),
                    '캡션': draft_caption(r) + (f' (첩 이미지 {len(doc_images(a.work, r))}면 중 한 면 — 해당 면은 원문 확인 필요)' if shared > 1 else ''),
                    '이야기': '', '판독': '', '원문': '', '번역': '', '해제': draft_haeje(r), '요약': '', '검토': '', '뷰어링크': r.get('뷰어링크', ''), '공유이미지': (f'{shared}건이 같은 첩 이미지를 공유' if shared > 1 else ''), '연도근거': r.get('연도근거', '')})
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
    if not os.path.exists(os.path.join(od, 'curator.md')):
        open(os.path.join(od, 'curator.md'), 'w', encoding='utf-8').write(curator_template(title))
    if not os.path.exists(os.path.join(od, 'delivery.md')):
        open(os.path.join(od, 'delivery.md'), 'w', encoding='utf-8').write(delivery_template(title, delivery_draft(out)))
    print('→', od, '(selection.csv의 캡션·이야기를 다듬고, 이미지를 읽어 판독·해제·요약을 채운 뒤 curator.md(큐레이터 노트)·delivery.md(전달 에디팅)를 다듬고 mediate)')


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

# 목록에 없는 곳(다른 리눅스 배포판 · 사용자 글꼴 폴더)도 찾아봄 — 이름에 이런 말이 든 글꼴
FONT_HINTS = {'regular': ('malgun.ttf', 'AppleSDGothicNeo', 'NotoSansCJK-Regular', 'NotoSansKR-Regular', 'NanumGothic.ttf', 'NanumBarunGothic.ttf', 'NotoSansCJKkr-Regular'),
              'bold': ('malgunbd.ttf', 'NotoSansCJK-Bold', 'NotoSansKR-Bold', 'NanumGothicBold', 'NanumBarunGothicBold', 'NotoSansCJKkr-Bold'),
              'serif': ('batang', 'AppleMyungjo', 'NotoSerifCJK-Bold', 'NotoSerifCJK-Regular', 'NotoSerifKR', 'NanumMyeongjo')}
FONT_DIRS = ['C:/Windows/Fonts', os.path.expanduser('~/AppData/Local/Microsoft/Windows/Fonts'), '/System/Library/Fonts', '/Library/Fonts',
             os.path.expanduser('~/Library/Fonts'), '/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.local/share/fonts'), os.path.expanduser('~/.fonts')]
_FONT_CACHE, _FONT_WARNED = {}, []


def _has_hangul(p):
    """그 글꼴로 '한'을 그렸을 때 빈 네모(글자 없음)와 다른지"""
    try:
        idx = 1 if 'NotoS' in p and p.endswith('.ttc') else 0  # Noto CJK 묶음: KR = 1번
        f = ImageFont.truetype(p, 40, index=idx)
        def ink(t):
            im = Image.new('L', (60, 60)); ImageDraw.Draw(im).text((5, 5), t, font=f, fill=255); return im.tobytes()
        a, b = ink('한'), ink('\uffff')
        return any(a) and a != b
    except Exception:
        return False


def font_path(kind='regular'):
    """한글이 실제로 그려지는 글꼴 파일(없으면 None) — 정해 둔 자리 → 글꼴 폴더 찾기 순"""
    if kind in _FONT_CACHE: return _FONT_CACHE[kind]
    cands = ([FONT_OVERRIDE[kind]] if kind in FONT_OVERRIDE else []) + FONT_CANDIDATES[kind]
    found = None
    for p in cands:
        if p and os.path.exists(p) and _has_hangul(p): found = p; break
    if not found:
        for d in FONT_DIRS:
            if not os.path.isdir(d): continue
            for root, _, files in os.walk(d):
                for fn in sorted(files):
                    if fn.lower().endswith(('.ttf', '.otf', '.ttc')) and any(k.lower() in fn.lower() for k in FONT_HINTS[kind]):
                        p = os.path.join(root, fn)
                        if _has_hangul(p): found = p; break
                if found: break
            if found: break
    if not found and kind != 'regular': found = font_path('regular')
    _FONT_CACHE[kind] = found
    return found


FONT_HELP = ('한글 글꼴을 찾지 못해 카드 · 영상 글자가 네모로 나올 수 있습니다. '
             'Windows: 맑은 고딕(기본 설치) · macOS: Apple SD 산돌고딕(기본) · Ubuntu/Debian: sudo apt install fonts-noto-cjk · '
             'Fedora: sudo dnf install google-noto-sans-cjk-fonts · 또는 --font 글꼴.ttf')


def font(size, kind='regular'):
    p = font_path(kind)
    if p:
        try: return ImageFont.truetype(p, size, index=1 if 'NotoS' in p and p.endswith('.ttc') else 0)
        except Exception: pass
    if not _FONT_WARNED: _FONT_WARNED.append(1); print('⚠ ' + FONT_HELP, file=sys.stderr)
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
    bottom = H - 132  # 아래 구분선(H-120) 위까지만 — 넘치면 글자를 줄이고, 그래도 넘치면 끝을 '…'로
    for fs, lh in ((34, 50), (31, 45), (28, 41)):
        lines = wrap(d, body, font(fs), W - 140)
        if y + 10 + len(lines) * lh <= bottom: break
    keep = max(1, (bottom - y - 10) // lh)
    if len(lines) > keep and find_quotes(body):  # 그래도 넘치면 종이에 적힌 문장을 앞세운다(인용이 잘리지 않게)
        q = find_quotes(body)[0]; lines = wrap(d, f'"{q[0]}({q[1]})" — ' + body, font(fs), W - 140)
    if len(lines) > keep:
        lines = lines[:keep]; ln = lines[-1]
        while d.textlength(ln + '…', font=font(fs)) > W - 140 and len(ln) > 1: ln = ln[:-1]
        lines[-1] = ln + '…'
    for ln in lines:
        d.text((70, y + 10), ln, font=font(fs), fill=(220, 210, 192)); y += lh
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


def has_reading(s):
    """판독 칸에 실제로 읽은 글자가 있는지 (괄호 속 설명만 있으면 False)"""
    t = re.sub(r'\([^)]*\)', '', s.get('판독') or '')
    return len(re.findall(r'[\u4e00-\u9fff\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]', t)) >= 2

# ---------------------------------------------------------------- 한자 독음 (ruby)
try:
    import hanja as _hanja          # pip install hanja (없으면 독음 없이 표시)
except Exception:
    _hanja = None
READ_FIX = {'拾': '십', '什': '십', '參': '삼', '敎': '교', '乙良': '을랑', '是白乎': '이삷온', '爲白乎': '하삷온', '爲只爲': '하기삼', '敎是': '이시',
            '矣身': '의몸', '爲去乎': '하거온', '爲白去乎': '하삷거온', '是乎': '이온', '爲乎': '하온', '段': '단'}
_HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+')

def reading_of(run):
    """한자 연속 구간의 한글 독음 (글자 수와 같은 길이). 이두 관용구는 READ_FIX로 덮어쓴다."""
    if not _hanja: return None
    try: r = list(_hanja.translate(run, 'substitution'))
    except Exception: return None
    if len(r) != len(run): return None
    for k, v in READ_FIX.items():
        i = run.find(k)
        while i >= 0:
            if len(v) == len(k): r[i:i + len(k)] = list(v)
            i = run.find(k, i + 1)
    return r

def ruby_html(text):
    """원문 줄을 한자 위에 한글 독음을 단 HTML로 (줄 바꿈 유지)"""
    out = []
    for line in text.strip().splitlines():
        buf, last = [], 0
        for m in _HAN.finditer(line):
            buf.append(html.escape(line[last:m.start()]))
            rd = reading_of(m.group())
            if rd: buf.append(''.join(f'<ruby>{html.escape(c)}<rt>{r}</rt></ruby>' for c, r in zip(m.group(), rd)))
            else: buf.append(html.escape(m.group()))
            last = m.end()
        buf.append(html.escape(line[last:]))
        out.append(''.join(buf))
    return '<br>'.join(out)

def aid_html(s):
    """해제·원문 읽기·내용 요약 블록 (비어 있으면 생략)"""
    parts = []
    if s.get('해제'): parts.append(f"<p><b>해제</b>{html.escape(s['해제'])}</p>")
    if has_reading(s): parts.append(f"<p><b>원문 읽기</b><span class=\"orig\">{html.escape(s['판독'])}</span></p>")
    if s.get('요약'): parts.append(f"<p><b>내용 요약</b>{html.escape(s['요약'])}</p>")
    if (s.get('원문') or '').strip():
        n = len([l for l in s['원문'].splitlines() if l.strip()])
        tr = f"<div class=\"tr\">{ruby_html(s['원문'])}</div>"
        tl = f"<p class=\"tl\"><b>원문 해석</b>{html.escape(s['번역'])}</p>" if (s.get('번역') or '').strip() else ''
        parts.append(f"<details class=\"full\" open><summary>원문 판독 전문 ({n}줄 · 오른쪽 첫 줄부터 · 한자 위 한글 독음)</summary>{tr}{tl}"
                     "<small>□ 읽지 못한 글자 · (?) 불확실 · (…) 잘림 · [ ] 서식상 확실한 보충 · 독음은 자동(이두·인명은 다를 수 있음)</small></details>")
    if not parts: return ''
    flag = '' if s.get('검토') else '<small>초안 — 문서명·이미지에 근거했으며 원문 판독 확인 전입니다</small>'
    return f'<details class="aid" open><summary>읽기 도움</summary>{"".join(parts)}{flag}</details>'


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
    span = (f'{min(ys)}–{max(ys)}' if min(ys) != max(ys) else f'{min(ys)}') if ys else ''
    unchecked = [s for s in sel if not s.get('검토')]

    # 0) 공유 미리 보기(링크 카드) — 카카오톡 · 페이스북 · X 등에 주소를 붙였을 때 보이는 제목 · 설명 · 그림
    burl = base_url(a.url)
    sdesc = (read_curator(ed).get('message') or a.lead or f'{coll} · {span} · 문서 {len(sel)}점을 원문으로 읽은 이야기')
    share_image(None if PH else os.path.join(ed, sel[0]['이미지']), title, f'{coll} · {span} · 문서 {len(sel)}점', os.path.join(od, 'share.jpg'))
    OHCSS = oldhangul_css(' '.join((x.get('판독') or '') + (x.get('원문') or '') + (x.get('이야기') or '') + (x.get('번역') or '') for x in sel))
    if OHCSS:
        from PIL import features
        if not features.check('raqm'): print('  ※ 옛한글이 있는데 이 Pillow에는 글자 조합(libraqm)이 없어 카드 그림의 옛한글이 풀어져 보일 수 있습니다. 웹페이지는 바르게 보입니다.')
    SM = lambda page_name, t: share_meta(t, sdesc, (burl + 'share.jpg') if burl else '', (burl + page_name) if burl else '')

    # 1) 카드뉴스
    first = os.path.join(ed, sel[0]['이미지'])
    card(first, title, f'{coll} · {span}', a.lead or f'흩어져 있던 집안 문서 {len(sel)}점으로 따라가는 이야기', src_line, os.path.join(od, 'cards', '00_표지.png'),
         ph=(placeholder_img(sel[0]['문서명'], sel[0]['자료ID']) if PH else None))
    for s in sel:
        body = (s['이야기'] or s['캡션'])
        card(os.path.join(ed, s['이미지']), f"{s['연도']} {s['문서유형']}".strip(), ' · '.join(persons(s)), body, f"{s['문서명']} · {src_line}", os.path.join(od, 'cards', f"{int(s['순서']):02d}.png"),
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
<div class="txt"><h2>{html.escape(s['문서유형'])}{(' · ' + html.escape(', '.join(persons(s)))) if persons(s) else ''}</h2>
<p class="cap">{html.escape(s['이야기'] or s['캡션'])}</p>
{aid_html(s)}
<p class="meta">{html.escape(s['문서명'])}<br>{html.escape(s['자료ID'])}{(' · <a href="' + html.escape(s['뷰어링크']) + '" target="_blank" rel="noopener">원본 보기 ↗</a>') if s.get('뷰어링크') else ''}{(' · <a href="' + html.escape(issue_url(a.issues, s, title)) + '" target="_blank" rel="noopener">판독 고침 제보 ↗</a>') if a.issues else ''}</p>{'' if s.get('검토') else '<p class="draft">캡션 초안 — 원문 확인 전</p>'}</div></section>""")
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
h2{{font-size:28px;margin:0 0 .4em}}
.aid{{background:#211b14;border:1px solid #4a3e2c;border-radius:10px;padding:12px 16px;margin:10px 0 14px;font:15.5px/1.75 'Noto Sans KR','Malgun Gothic',sans-serif;color:#e4d9c3}}
.aid summary{{cursor:pointer;color:#c4964a;font-weight:700;letter-spacing:.05em}} .aid p{{margin:.55em 0}}
.aid b{{display:inline-block;min-width:5.2em;color:#c4964a;margin-right:.4em}} .aid .orig{{font-family:'Noto Serif KR','Batang',serif;color:#f3ead8}}
.aid small{{display:block;color:#9d917c;font-size:12.5px;margin-top:6px}}
.aid .full{{margin-top:8px;border-top:1px dashed #4a3e2c;padding-top:6px}} .aid .full summary{{font-weight:600;color:#d9b77a}}
:focus-visible{{outline:2px solid #c4964a;outline-offset:2px}}
.aid .tr{{font:18px/2.5 'Noto Serif KR','Batang',serif;color:#f3ead8;background:#16130f;border-radius:8px;padding:10px 14px;margin:8px 0 4px;max-height:34em;overflow:auto;word-break:keep-all}}
.aid ruby rt{{font:11px 'Noto Sans KR',sans-serif;color:#c4964a;letter-spacing:0}} .aid .tl{{background:#2a2219;border-radius:8px;padding:10px 14px;line-height:1.8}} .cap{{font-size:19px;line-height:1.8}} .meta{{font-size:14px;color:#9d917c;font-family:sans-serif}}
.draft{{display:inline-block;font:13px sans-serif;color:#16130f;background:#c4964a;padding:3px 10px;border-radius:12px}}
footer{{padding:6vw;color:#9d917c;font:15px/1.8 sans-serif;border-top:1px solid #3a3225}}
@media(max-width:800px){{.panel{{grid-template-columns:1fr}} .line:before{{display:none}}}}
@media print{{body{{background:#fff;color:#111}} header{{min-height:auto;background:none}} .panel{{page-break-inside:avoid}}}}
</style></head><body><header><small>{html.escape(coll)} · {span}</small><h1>{html.escape(title)}</h1>
<p>{html.escape(a.lead or f'한국고문서자료관에 흩어져 있던 집안 문서 {len(sel)}점을 시간 순서로 엮었습니다.')}</p></header>
<main class="line">{''.join(items)}</main>
<footer>{html.escape(src_line)}. 이미지의 이용·재배포는 자료관 이용 조건을 따릅니다.<br>「읽기 도움」의 해제·원문 읽기·내용 요약은 문서명과 이미지에 근거한 초안입니다. 판독이 어려운 글자는 □로 표시했으며, 개별 문서의 판독·해석은 원문 확인이 필요합니다.<br>제작 도구: aks-archive-harvester (github.com/changgi/archive-tools)</footer></body></html>"""
    cur = read_curator(ed); facts = curator_facts(sel, a.work)
    if cur: page = page.replace('</p></header>', '</p><p style="font:15px sans-serif"><a href="#curator" style="color:#c4964a">이 전시를 만든 이유 — 큐레이터 노트 ↓</a></p></header>', 1)
    page = put_curator(page, curator_html(cur, facts, 'exhibit') if cur else '', '</main>')
    page = re.sub(r'<!--FIXES-->.*?<!--/FIXES-->', '', page, flags=re.S)
    fx = corrections_html(read_corrections(ed))
    if fx: page = page.replace('</main>', '</main><!--FIXES-->' + fx + '<!--/FIXES-->', 1)
    dv = read_delivery(ed); page = put_delivery(page, delivery_html(dv), '</main>')
    open(os.path.join(od, 'exhibit.html'), 'w', encoding='utf-8').write(put_oldhangul(put_share(page, SM('exhibit.html', title)), OHCSS))

    # 3) 수업 활동지 (인쇄용 HTML)
    qs = []
    for s in sel:
        qs.append(f"""<div class="q">{fig(s, 900)}<div><h2>{s['순서']}. {html.escape(str(s['연도']))} {html.escape(s['문서유형'])}</h2>
<p><b>어떤 문서? (해제)</b> {html.escape(s.get('해제') or s['유형설명'] or '—')}</p>
{('<p><b>무슨 내용? (내용 요약)</b> ' + html.escape(s['요약']) + '</p>') if s.get('요약') else ''}
{('<p class="orig"><b>원문 속 글자</b> ' + html.escape(s['판독']) + '</p>') if has_reading(s) else ''}
{('<p><b>원문 판독</b> (오른쪽 첫 줄부터 · 한자 위 한글 독음 · □ 못 읽은 글자)</p><div class="tr" tabindex="0" role="region" aria-label="원문 판독">' + ruby_html(s['원문']) + '</div>') if (s.get('원문') or '').strip() else ''}
{('<p><b>원문 해석</b> ' + html.escape(s['번역']) + '</p>') if (s.get('번역') or '').strip() else ''}
<p><b>찾아보기</b> {('① 위 「원문 속 글자」를 이미지에서 찾아 동그라미 해 보세요. ' if has_reading(s) else '① 문서를 받은 사람(또는 쓴 사람)의 이름을 찾아 표시해 보세요. ')}② 날짜가 적힌 곳을 찾아보세요. ③ 도장(인장)이 있나요?</p>
<p><b>생각해 보기</b> 이 문서는 왜 지금까지 집안에 남아 있었을까요?</p></div></div>""")
    hand = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>활동지 — {html.escape(title)}</title><style>
@page{{size:A4;margin:16mm}} body{{font-family:'Malgun Gothic','Noto Sans KR',sans-serif;color:#222;font-size:14px}}
h1{{font-size:24px;margin:0}} .sub{{color:#666;margin:4px 0 16px}} .q{{display:grid;grid-template-columns:42% 1fr;gap:14px;border-top:1px solid #ccc;padding:12px 0;page-break-inside:avoid}}
.q img{{width:100%}} .ph{{display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;aspect-ratio:4/3;border:2px dashed #b89a68;color:#5a4628;text-decoration:none;padding:10px;font-size:13px}} .ph b{{font-size:15px;margin:6px 0}} .ph em{{font-style:normal;color:#9a6e2e}} h2,h3{{margin:0 0 6px;font-size:17px}} p{{margin:4px 0;line-height:1.6}} div.tr{{font:13.5px/2.3 'Batang','Noto Serif KR',serif;border-left:3px solid #c9b48a;padding:4px 10px;margin:4px 0;background:#fbf8f1}} ruby rt{{font-size:8.5px;color:#8a6a2e}} .orig{{background:#f6f1e6;padding:4px 8px;border-radius:4px;font-family:'Batang','Noto Serif KR',serif}} .box{{border:1px dashed #999;height:120px;margin-top:10px;padding:8px;color:#666}}
</style></head><body><h1>고문서로 읽는 이야기: {html.escape(title)}</h1><p class="sub">{html.escape(coll)} · {span} · 이름: ________ </p>{''.join(qs)}
<h2>정리해 보기</h2><div class="box">이 문서들을 시간 순서로 이으면 어떤 이야기가 되나요? 세 문장으로 써 보세요.</div>
<p class="sub">{html.escape(src_line)} · 이미지 이용은 자료관 이용 조건을 따릅니다. 해제·요약은 문서명과 이미지에 근거한 초안이며 판독이 어려운 글자는 □로 표시했습니다.</p></body></html>"""
    hand = put_curator(hand, curator_html(cur, None, 'handout') if cur else '', None)  # 활동지 맨 끝(교사용)
    open(os.path.join(od, 'handout.html'), 'w', encoding='utf-8').write(put_oldhangul(put_share(hand, SM('handout.html', '활동지 — ' + title)), OHCSS))

    # 4) SNS 글
    tags = ['#고문서', '#한국고문서자료관', '#기록', '#한국사'] + [f"#{s['문서유형']}" for s in sel[:3]]
    sns = [f'{title}', '', a.lead or f'{coll}에 남은 문서 {len(sel)}점으로 따라가는 이야기.', '']
    for s in sel: sns.append(f"· {s['연도']} {s['문서유형']} — {(s['이야기'] or s['캡션'])[:60]}")
    sns += ['', src_line, '이미지 이용은 자료관 이용 조건을 따릅니다.', '', ' '.join(dict.fromkeys(tags))]
    open(os.path.join(od, 'sns.txt'), 'w', encoding='utf-8').write('\n'.join(sns))

    # 4-2) 2차 홍보: 비하인드 카드 · 채널별 홍보안 (큐레이터 노트가 있으면)
    cur = read_curator(ed); facts = curator_facts(sel, a.work)
    if cur:
        bimg = os.path.join(ed, sel[0]['이미지']) if sel and not PH else None
        bc = behind_cards(cur, facts, title, src_line, bimg, os.path.join(od, 'cards'), ph=(placeholder_img(sel[0]['문서명'], sel[0]['자료ID']) if PH and sel else None))
        qm = next((find_quotes(s.get('이야기'))[0] for s in sel if find_quotes(s.get('이야기'))), None)
        open(os.path.join(od, 'channels.md'), 'w', encoding='utf-8').write(channel_plan(cur, title, coll, a.url or 'exhibit.html', quote=(f'"{qm[0]}({qm[1]})"' if qm else '')))
        print(f'  2차 홍보: 비하인드 카드 {len(bc)}장 · channels.md(채널별 홍보안)')

    # 5) 결과물 한눈에 보기 (첫 페이지) — 처음 온 사람이 무엇이 있는지 바로 알고 열 수 있게
    cardfs = sorted(f for f in os.listdir(os.path.join(od, 'cards')) if f.lower().endswith(('.png', '.jpg')))
    tiles = [('🖼️', '전시 웹페이지', '문서 이미지 · 이야기 · 읽기 도움을 연표로 넘겨 보는 한 장짜리 전시', 'exhibit.html', '열기'),
             ('✏️', '수업 활동지', '인쇄해서 바로 쓰는 A4 활동지 (해제 · 요약 · 찾아보기 · 생각해 보기)', 'handout.html', '열기'),
             ('🗂️', f'카드뉴스 {len(cardfs)}장', '1080×1350 카드 (표지 · 문서별 · 마무리)', 'cards/' + (cardfs[0] if cardfs else ''), '첫 장 보기'),
             ('📣', 'SNS 글', '해시태그를 붙인 게시 글 초안', 'sns.txt', '열기'),
             ('📊', '원문 · 번역 표 (CSV)', '문서명 · 연도 · 판독 · 원문 · 번역 · 해제 · 요약 · 원본 링크', 'selection.csv', '받기')]
    shutil.copy(os.path.join(ed, 'selection.csv'), os.path.join(od, 'selection.csv'))  # mediate 폴더만 올려도 CSV 링크가 살아 있게
    if os.path.exists(os.path.join(od, 'promo.md')): tiles.append(('🎬', '릴스 홍보 문구', '「고문서 한 장」 형식 게시 문구', 'promo.md', '열기'))
    if cur: tiles.insert(0, ('✍️', '큐레이터 노트', cur.get('message') or '이 결과물을 만든 이유와 비하인드', '#curator', '읽기'))
    vd = os.path.join(od, 'video'); vids = []
    for fmt, label in (('reel', '릴스 (세로 9:16)'), ('wide', '가로 (16:9)')):
        c = sorted(glob.glob(os.path.join(vd, f'*_{fmt}_web.mp4'))) or sorted(glob.glob(os.path.join(vd, f'*_{fmt}.mp4')))
        if c:
            base = re.sub(r'_(reel|wide)(_web)?\.mp4$', '', os.path.basename(c[-1]))
            vtt = os.path.join(vd, base + '.ko.vtt')
            vids.append((label, 'video/' + os.path.basename(c[-1]), ('video/' + os.path.basename(vtt)) if os.path.exists(vtt) else '', fmt))
    if vids: tiles.insert(1 if cur else 0, ('🎞️', '영상', ' · '.join(v[0] for v in vids) + ' — 자막 포함', '#video', '보기'))
    if os.path.exists(os.path.join(od, 'channels.md')): tiles.append(('📢', '채널별 홍보안', '인스타 · 유튜브 · 틱톡 · 페이스북 · 스레드 · X · 전시 · 책 · 웹툰 · 영상 — 형식과 바로 쓰는 문구', 'channels.md', '열기'))
    tl = ''.join(f'<a class="t" href="{html.escape(h)}"><span>{i}</span><b>{html.escape(t)}</b><p>{html.escape(d)}</p><em>{b} →</em></a>' for i, t, d, h, b in tiles)
    strip = ''.join(f'<a href="cards/{html.escape(f)}"><img src="cards/{html.escape(f)}" alt="카드 {k+1}" loading="lazy"></a>' for k, f in enumerate(cardfs))
    vsec = ('<h2 id="video">영상</h2><div class="v">' + ''.join(
        f'<figure><video controls preload="metadata" playsinline src="{html.escape(v)}">' + (f'<track kind="subtitles" srclang="ko" label="한국어" src="{html.escape(t)}" default>' if t else '') +
        f'</video><figcaption>{html.escape(l)} · <a href="{html.escape(v)}" download>받기</a></figcaption></figure>' for l, v, t, f in vids) + '</div>') if vids else ''
    srts = sorted(glob.glob(os.path.join(od, 'video', '*.ko.srt')))
    if vids and srts:  # 자막 전문 — 소리 없이 · 화면 읽기 프로그램으로
        lines = [ln for blk in open(srts[0], encoding='utf-8').read().replace('\r', '').split('\n\n') for ln in [' '.join(x for x in blk.split('\n') if x and '-->' not in x and not x.strip().isdigit())] if ln]
        vsec += ('<details style="margin-top:10px"><summary style="cursor:pointer;color:#c4964a">자막 전문 읽기</summary><div tabindex="0" role="region" aria-label="자막 전문" style="max-height:260px;overflow:auto;background:#1f1a14;border-radius:10px;padding:8px 12px;margin-top:6px">'
                 + ''.join(f'<p style="margin:4px 0;font-size:14px">{html.escape(x)}</p>' for x in lines) + '</div></details>')
    idx = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} — 결과물 한눈에 보기</title><style>
body{{margin:0;background:#16130f;color:#f3ead8;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;line-height:1.6}} main{{max-width:1080px;margin:0 auto;padding:40px 6vw 60px}}
h1{{font-family:'Noto Serif KR','Batang',serif;font-size:clamp(24px,4vw,36px);margin:0 0 6px}} .sub{{color:#b9ab90}} h2{{color:#c4964a;font-size:17px;margin:34px 0 10px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}} .t{{display:flex;flex-direction:column;gap:4px;background:#1f1a14;border:1px solid #3a3225;border-radius:14px;padding:16px;color:inherit;text-decoration:none}}
.t:hover{{border-color:#c4964a}} .t span{{font-size:24px}} .t b{{font-size:16px}} .t p{{margin:0;color:#b9ab90;font-size:13.5px;flex:1}} .t em{{font-style:normal;color:#c4964a;font-weight:700;font-size:14px}}
:focus-visible{{outline:2px solid #c4964a;outline-offset:2px}} .s{{display:flex;gap:10px;overflow-x:auto;padding-bottom:8px}} .s img{{height:220px;border-radius:8px;border:1px solid #3a3225}} .v{{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}} .v figure{{margin:0}} .v video{{max-height:520px;max-width:100%;border-radius:10px;background:#000}} .v figcaption{{font-size:13px;color:#b9ab90;margin-top:4px}} .v a{{color:#c4964a}} ol{{padding-left:20px}} li{{margin:3px 0}} .k{{font-size:12.5px;color:#8f826b;margin-top:30px}}
</style></head><body><main><h1>{html.escape(title)}</h1><p class="sub">{html.escape(coll)} · {span} · 문서 {len(sel)}점</p>
<h2>결과물 바로 가기</h2><div class="g">{tl}</div>
{vsec}{curator_html(cur, facts, 'index') if cur else ''}{delivery_html(read_delivery(ed))}<h2>카드뉴스 미리 보기</h2><div class="s" tabindex="0" role="region" aria-label="카드뉴스 미리 보기 — 옆으로 넘겨 보기">{strip}</div>
<h2>담긴 문서</h2><ol>{''.join(f"<li>{'' if str(x['문서명']).startswith(str(x['연도'])) else html.escape(str(x['연도'])) + ' '}{html.escape(x['문서명'])}</li>" for x in sel)}</ol>
<p class="k">{html.escape(src_line)} · 이미지 이용은 자료관 이용 조건을 따릅니다(소장처 동의 필요).</p></main></body></html>"""
    open(os.path.join(od, 'index.html'), 'w', encoding='utf-8').write(put_oldhangul(put_share(idx, SM('index.html', title + ' — 결과물 한눈에 보기')), OHCSS))
    print(f'→ {od}\n  index.html(결과물 한눈에 보기) · exhibit.html(전시 웹페이지) · cards/ {len(cardfs)}장(카드뉴스)' + (f' · 영상 {len(vids)}개' if vids else '') + ' · handout.html(수업 활동지) · sns.txt')
    if unchecked: print(f'  ※ 검토 칸이 비어 있는 캡션 {len(unchecked)}건은 "초안" 표시가 붙습니다.')




def issue_url(base, s, title=''):
    """문서 하나에 대한 '판독 고침 제보' 주소 — GitHub 이슈 새 글(제목·본문 미리 채움) 또는 그 밖의 주소(그대로)"""
    from urllib.parse import quote
    if 'github.com' not in base: return base
    b = base.rstrip('/'); b = b if b.endswith('/issues') else b + '/issues'
    body = (f"문서: {s.get('문서명', '')}\n자료 ID: {s.get('자료ID', '')}\n원본 뷰어: {s.get('뷰어링크', '')}\n시리즈·편: {title}\n\n"
            "고칠 곳(판독 · 번역 · 해제 · 연도 가운데):\n\n바르게 고친 내용:\n\n근거(원본 사진의 줄 · 다른 자료):\n")
    return f"{b}/new?title={quote('[판독 고침] ' + (s.get('문서명') or ''))}&body={quote(body)}&labels={quote('판독 고침')}"


# ---------------------------------------------------------------- 옛한글 글꼴 (아래아 등 조합이 기기마다 다르게 보이지 않게)
OLD_JAMO = re.compile(r'[ᄀ-ᇿꥠ-꥿ힰ-퟿ㆍ〮〯]')
OH_RANGE = 'U+1100-11FF,U+A960-A97F,U+D7B0-D7FF,U+318D,U+302E-302F'
FAMILIES = {"Noto Sans KR": ("Noto Sans KR", "NotoSansKR", "Noto Sans CJK KR", "NotoSansCJKkr"),
            "Noto Serif KR": ("Noto Serif KR", "NotoSerifKR", "Noto Serif CJK KR", "NotoSerifCJKkr")}


def oldhangul_css(text, url=None):
    """글에 옛한글 자모가 있으면, 페이지 글꼴 목록 맨 앞의 'Noto Sans KR' · 'Noto Serif KR' 이름에 옛한글 글꼴 조각을 그 글자 범위로만 덧붙이는 <style>.
    설치된 Noto 글꼴은 local()로 그대로 쓰고, 없으면 옛한글만 조각에서, 나머지 글자는 다음 글꼴(맑은 고딕 · 바탕 등)에서 나온다.
    url을 주면 그 주소의 woff2를, 없으면 플러그인 assets/의 조각을 페이지 안에 넣는다(한 파일 그대로 공유되게). 옛한글이 없으면 ''"""
    if not OLD_JAMO.search(text or ''): return ''
    if not url:
        fp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'oldhangul-sans.woff2')
        if not os.path.exists(fp): return ''
        url = 'data:font/woff2;base64,' + base64.b64encode(open(fp, 'rb').read()).decode()
    rules = []
    for fam, names in FAMILIES.items():
        for w, suf in ((400, ('', ' Regular', '-Regular')), (700, (' Bold', '-Bold'))):
            src = ','.join(f"local('{n}{x}')" for n in names for x in suf)
            rules.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:{src}}}")
        rules.append(f"@font-face{{font-family:'{fam}';src:url({url}) format('woff2');unicode-range:{OH_RANGE}}}")
    return '<style id="oldhangul">' + ''.join(rules) + '</style>'


def put_oldhangul(page, css):
    page = re.sub(r'<style id="oldhangul">.*?</style>', '', page, flags=re.S)
    return put_a11y(page.replace('</head>', css + '</head>', 1) if css else page)


SKIP = ('<!--SKIP--><a class="skip" href="#{t}">본문 바로가기</a><style>.skip{{position:absolute;left:-9999px;top:0;z-index:99;background:#c4964a;color:#16130f;'
        'padding:8px 14px;font:700 15px sans-serif;border-radius:0 0 8px 0;text-decoration:none}}.skip:focus{{left:0}}'
        ':focus-visible{{outline:2px solid #c4964a;outline-offset:2px}}</style><!--/SKIP-->')


def put_a11y(page):
    """모든 웹페이지 공통 접근성 손질 — 다시 실행해도 같은 결과(멱등)
    ① 「본문 바로가기」 링크(키보드 · 화면 낭독기 사용자가 메뉴를 건너뜀) · 초점 테두리
    ② </main> 뒤 · <footer> 앞에 붙은 노트(큐레이터 · 연출 · 고친 곳)를 본문(main) 안으로
    ③ 활동지처럼 main이 없으면 본문 전체를 main으로
    ④ 같은 이름의 영역(원문 판독 · 표)을 「… 1, 2」로 구분, 메뉴(nav)가 여럿이면 이름 붙이기"""
    page = re.sub(r'<!--SKIP-->.*?<!--/SKIP-->', '', page, flags=re.S)
    m = re.search(r'</main>((?:(?!<main)[\s\S])*?)(?=<footer)', page)
    if m and m.group(1).strip(): page = page[:m.start()] + m.group(1) + '</main>' + page[m.end():]
    if '<main' not in page and '<body' in page:
        page = re.sub(r'(<body[^>]*>)', lambda x: x.group(1) + '<main>', page, count=1)
        i = page.rfind('</body>'); page = page[:i] + '</main>' + page[i:]
    for lab in ('원문 판독', '표'):  # 같은 이름의 영역이 여럿이면 번호로 구분
        if len(re.findall(rf'aria-label="{lab}(?: \d+)?"', page)) > 1:
            k = iter(range(1, 10 ** 6))
            page = re.sub(rf'aria-label="{lab}(?: \d+)?"', lambda x: f'aria-label="{lab} {next(k)}"', page)
    if len(re.findall(r'<nav\b', page)) > 1:
        names = iter(['사이트 메뉴', '이 페이지 차례', '다른 메뉴 2', '다른 메뉴 3', '다른 메뉴 4'])
        page = re.sub(r'<nav\b(?![^>]*aria-label)', lambda x: f'<nav aria-label="{next(names)}"', page)
    # 건너뛸 곳: 본문 첫 제목(메뉴 뒤) — 없으면 main
    mi = page.find('<main'); hi = page.find('<h1', mi if mi >= 0 else 0)
    nav_first = mi >= 0 and 0 <= page.find('<nav', mi) < hi
    if nav_first and hi >= 0:
        if not re.match(r'<h1[^>]*\bid=', page[hi:hi + 200]): page = page[:hi] + '<h1 id="content"' + page[hi + 3:]
        t = re.match(r'<h1[^>]*\bid="([^"]+)"', page[hi:hi + 300]).group(1)
    elif mi >= 0:
        if not re.match(r'<main[^>]*\bid=', page[mi:mi + 200]): page = page[:mi] + '<main id="main"' + page[mi + 5:]
        t = re.match(r'<main[^>]*\bid="([^"]+)"', page[mi:mi + 300]).group(1)
    else: return page
    return re.sub(r'(<body[^>]*>)', lambda x: x.group(1) + SKIP.format(t=t), page, count=1)

# ---------------------------------------------------------------- 공유 미리 보기 (카카오톡 · 페이스북 · X 링크 카드)
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%2316130f'/%3E"
           "%3Crect x='14' y='10' width='36' height='44' rx='3' fill='%23efe3c8'/%3E%3Cpath d='M21 20h22M21 28h22M21 36h16' stroke='%23c4964a' stroke-width='4' stroke-linecap='round'/%3E%3C/svg%3E")


def base_url(url):
    """전시 주소(…/exhibit.html) 또는 폴더 주소 → 끝이 / 인 폴더 주소. 없으면 ''"""
    if not url: return ''
    return url if url.endswith('/') else (url.rsplit('/', 1)[0] + '/' if re.search(r'/[^/]+\.[a-z0-9]+$', url) else url + '/')


def share_meta(title, desc, image='', url='', kind='website'):
    e = html.escape; d = re.sub(r'\s+', ' ', desc or '').strip()[:180]
    m = [f'<meta name="description" content="{e(d)}">', f'<link rel="icon" href="{FAVICON}">',
         f'<meta property="og:type" content="{kind}">', f'<meta property="og:title" content="{e(title)}">', f'<meta property="og:description" content="{e(d)}">',
         '<meta property="og:locale" content="ko_KR">', f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">',
         f'<meta name="twitter:title" content="{e(title)}">', f'<meta name="twitter:description" content="{e(d)}">']
    if url: m.append(f'<meta property="og:url" content="{e(url)}">')
    if image and re.match(r'https?://', image):  # 미리 보기 이미지는 절대 주소여야 합니다
        m += [f'<meta property="og:image" content="{e(image)}">', '<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">', f'<meta name="twitter:image" content="{e(image)}">']
    return '<!--SHARE-->' + ''.join(m) + '<!--/SHARE-->'


def put_share(page, meta):
    """<head>에 공유 미리 보기 태그 넣기 — 다시 실행해도 한 번만"""
    page = re.sub(r'<!--SHARE-->.*?<!--/SHARE-->', '', page, flags=re.S)
    m = re.search(r'<meta charset="utf-8">', page)
    return page[:m.end()] + meta + page[m.end():] if m else page.replace('<head>', '<head>' + meta, 1)


def share_image(img, title, sub, out, tag='고문서 한 장'):
    """1200×630 링크 카드 이미지 — 왼쪽 문서 사진, 오른쪽 제목"""
    W, H = 1200, 630; c = Image.new('RGB', (W, H), (22, 19, 15)); d = ImageDraw.Draw(c)
    if img is not None:
        im = img if isinstance(img, Image.Image) else Image.open(img).convert('RGB')
        r = max(560 / im.width, H / im.height); im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))))
        x0 = (im.width - 560) // 2; y0 = min(max(0, (im.height - H) // 3), im.height - H)
        c.paste(im.crop((x0, y0, x0 + 560, y0 + H)), (0, 0))
        g = Image.new('L', (120, 1)); g.putdata([int(255 * k / 119) for k in range(120)])
        c.paste(Image.new('RGB', (120, H), (22, 19, 15)), (440, 0), g.resize((120, H)))
        x = 600
    else: x = 80
    tw = W - x - 60
    d.text((x, 60), tag.upper() if tag.isascii() else tag, font=font(26, 'bold'), fill=(196, 150, 74))
    fb = font(58 if len(title) < 22 else 46, 'serif'); y = 120
    for ln in wrap(d, title, fb, tw)[:4]: d.text((x, y), ln, font=fb, fill=(243, 234, 216)); y += int(fb.size * 1.32)
    fs = font(26); y += 14
    for ln in wrap(d, sub, fs, tw)[:3]: d.text((x, y), ln, font=fs, fill=(185, 171, 144)); y += 38
    d.text((x, H - 60), '한국학중앙연구원 한국고문서자료관 소장·제공', font=font(20), fill=(140, 128, 108))
    c.save(out, quality=85)
    return out

# ---------------------------------------------------------------- originals (원본 묶음: 문서 전체 면 + 원본 영상)
ORIG_NOTE = """원본 자료 묶음 — {title}
소장처: {coll}

■ 기록 사진 (원본 해상도 JPG · 문서마다 폴더)
- 소장·제공: 한국학중앙연구원 한국고문서자료관(archive.aks.ac.kr) · {coll}
- 자료관 안내에 따라 이미지를 다시 쓰려면 소장처 동의가 필요합니다(문의 031-730-8873, 8876).
- 게시·배포할 때는 "이미지: 한국학중앙연구원 한국고문서자료관 소장·제공 · {coll}"를 표기하세요.
- 「출처.csv」: 문서명 · 받은 면 수 / 전체 면 수 · 자료관 원본 뷰어 링크.
- 문제가 있으면 알려 주시면 바로 내리겠습니다.
{video}
※ 판독·해석은 이미지에 근거한 초안이며, 정확한 판독은 원문 확인이 필요합니다.
"""


def cmd_originals(a):
    import subprocess, zipfile
    HV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'harvest.py')
    ed = os.path.join(a.work, 'edit', a.theme)
    sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
    if a.only: sel = [s for s in sel if s['순서'] in a.only.split(',')]
    docs = jload(os.path.join(a.work, 'docs.json'))
    byid = {d['id']: d for d in docs}
    picked = [(s, byid.get(s['자료ID'])) for s in sel]
    rx = '^(' + '|'.join(re.escape(d['name']) for _, d in picked if d) + ')$'
    coll = a.collection or (json.load(open(os.path.join(a.work, 'collection.json'), encoding='utf-8'))['name'] if os.path.exists(os.path.join(a.work, 'collection.json')) else os.path.basename(os.path.abspath(a.work)))
    if a.full:  # 문서 전체 면 받기 — 기본 동시 접속 수 그대로, manifest는 한 번에 하나
        if any(d is not None and not d.get('imgs') for _, d in picked):
            du = a.data_url or json.load(open(os.path.join(a.work, 'collection.json'), encoding='utf-8'))['data_url']
            print('면 목록 수집(manifest --match)…', flush=True)
            subprocess.run([sys.executable, HV, 'manifest', '--work', a.work, '--data-url', du, '--match', rx], check=True)
            docs = jload(os.path.join(a.work, 'docs.json')); byid = {d['id']: d for d in docs}
            picked = [(s, byid.get(s['자료ID'])) for s in sel]
        total = sum(len(d.get('imgs') or []) for _, d in picked if d)
        print(f'선별 문서 {len(picked)}건 · 전체 {total}면' + (' — 미리 보기(--dry-run)라 받지 않음' if a.dry_run else ''))
        for s, d in picked:
            print(f"  {s['순서']:>2}. {s['문서명'][:40]} — {len(d.get('imgs') or []) if d else '?'}면")
        if a.dry_run: return
        for k in range(a.rounds):  # download는 --time마다 끊기므로 DONE까지 이어 받기
            r = subprocess.run([sys.executable, HV, 'download', '--work', a.work, '--match', rx, '--time', str(a.time)], capture_output=True, text=True)
            print(r.stdout.strip().splitlines()[-2] if r.stdout.strip() else r.stderr[-300:], flush=True)
            if 'STATUS: DONE' in r.stdout: break
        else:
            print('※ 아직 남은 면이 있습니다. 같은 명령을 다시 실행하면 이어 받습니다.')
    # 문서별 받은 면 모으기
    items = []
    for s, d in picked:
        dd = os.path.dirname(os.path.join(a.work, s['원본경로']))
        pages = sorted(glob.glob(os.path.join(dd, '*.jpg')))
        nm = re.sub(r'[\\/:*?"<>|]', '_', f"{int(s['순서']):02d}_{s['문서명']}")[:90]
        items.append((nm, pages, [s['순서'], s['문서명'], len(pages), len(d.get('imgs') or []) if d else '', s.get('뷰어링크', '')]))
    vids = []
    if a.videos:
        for v in sorted(glob.glob(os.path.join(a.videos, '*'))):
            if v.lower().endswith(('.mp4', '.mov', '.srt', '.vtt')) and '_web.' not in v: vids.append(v)  # 웹 압축본은 빼고 원본만
    dest = a.dest or os.path.join(a.work, 'originals', a.theme); os.makedirs(dest, exist_ok=True)
    prefix = a.prefix or re.sub(r'\s+', '', coll)[:30]
    vnote = ('\n■ 원본 영상\n- 웹용으로 줄이기 전의 원본 해상도 영상과 자막입니다. 영상 속 문서 이미지에도 위 출처·이용 조건이 적용됩니다.\n' if vids else '')
    note = ORIG_NOTE.format(title=a.title or a.theme, coll=coll, video=vnote)
    srcs = io.StringIO(); w = csv.writer(srcs); w.writerow(['순서', '문서명', '받은 면', '전체 면', '자료관 원본 뷰어']); w.writerows(it[2] for it in items)
    srccsv = '﻿' + srcs.getvalue() + f'\n이미지: 한국학중앙연구원 한국고문서자료관 소장·제공 · {coll}\n'
    lim = a.max_mb * 1024 * 1024
    units = [('사진', nm, [(p, f'기록사진/{nm}/{os.path.basename(p)}') for p in pages]) for nm, pages, _ in items if pages]
    units += [('영상', os.path.basename(v), [(v, f'영상/{os.path.basename(v)}')]) for v in vids]
    parts, cur, sz = [], [], 0
    for u in units:
        n = sum(os.path.getsize(f) for f, _ in u[2])
        if cur and sz + n > lim: parts.append(cur); cur, sz = [], 0
        cur.append(u); sz += n
    if cur: parts.append(cur)
    out = []
    for i, P in enumerate(parts, 1):
        fn = os.path.join(dest, f'{prefix}_원본' + (f'_part{i:02d}of{len(parts):02d}' if len(parts) > 1 else '') + '.zip')
        with zipfile.ZipFile(fn, 'w', zipfile.ZIP_STORED) as z:  # JPG·MP4는 이미 압축됨
            z.writestr('읽어보기_출처와이용조건.txt', note); z.writestr('기록사진/출처.csv', srccsv)
            for u in P:
                for f, arc in u[2]: z.write(f, arc)
        out.append(fn)
        print(f'{os.path.basename(fn)}\t{os.path.getsize(fn) // 2**20}MB')
    got = sum(len(p) for _, p, _ in items); want = sum((it[2][3] or 0) for it in items)
    print(f'→ {dest}  사진 {got}면' + (f' / 전체 {want}면' if want else '') + (f' · 영상 {len(vids)}개' if vids else ''))
    if want and got < want and not a.full:
        print('  ※ 일부 면만 받은 문서가 있습니다. --full 을 붙이면 문서 전체 면을 받아 묶습니다(--dry-run 으로 면 수 먼저 확인).')


# ---------------------------------------------------------------- 큐레이터 노트 (기획 의도 · 비하인드)
CURATOR_KEYS = [('why', '왜 이 문서들인가', '수많은 문서 가운데 이것들을 고른 까닭. 무엇이 눈에 걸렸는지'),
                ('message', '전하고 싶은 것', '보는 사람이 한 가지만 가져간다면 무엇이길 바라는지 (한두 문장)'),
                ('look', '이렇게 보이길 바랐다', '순서·인용·장면을 어떻게 배치했고, 어떤 느낌으로 다가가길 원했는지'),
                ('use', '이렇게 써 주세요', '수업·전시·연구·SNS 등에서 이 결과물을 어떻게 쓰면 좋은지'),
                ('behind', '만들며 있었던 일', '판독이 막힌 곳, 바꾼 결정, 빠진 자료, 확인이 필요한 점 — 있었던 일만'),
                ('question', '남겨 둔 질문', '문서만으로는 답할 수 없어 보는 사람과 나누고 싶은 질문')]


def curator_template(title):
    out = [f'# 큐레이터 노트 — {title}', '', '<!-- 각 칸을 채우세요. 문서와 작업에서 실제로 확인한 것만 씁니다. 빈 칸은 결과물에 나오지 않습니다. -->', '']
    for _, h, g in CURATOR_KEYS: out += [f'## {h}', f'<!-- {g} -->', '', '']
    return '\n'.join(out)


def read_curator(ed):
    p = os.path.join(ed, 'curator.md')
    if not os.path.exists(p): return {}
    t = re.sub(r'<!--.*?-->', '', open(p, encoding='utf-8').read(), flags=re.S)
    rev = {h: k for k, h, _ in CURATOR_KEYS}; c = {}
    for m in re.finditer(r'^##\s*(.+?)\s*\n(.*?)(?=^##\s|\Z)', t, flags=re.S | re.M):
        k = rev.get(m.group(1).strip())
        if k and m.group(2).strip(): c[k] = m.group(2).strip()
    return c


def curator_facts(sel, work=None):
    """제작 기록 — selection.csv와 받은 면에서 자동으로 세는 사실들"""
    got = 0
    for s in sel:
        if work and s.get('원본경로'):
            got += len(glob.glob(os.path.join(os.path.dirname(os.path.join(work, s['원본경로'])), '*.jpg')))
    full = ''.join(s.get('원문') or s.get('판독') or '' for s in sel)
    ys = sorted(int(s['연도']) for s in sel if str(s.get('연도', '')).isdigit())
    f = [f"문서 {len(sel)}건" + (f" · {ys[0]}–{ys[-1]}년" if ys and ys[0] != ys[-1] else (f" · {ys[0]}년" if ys else ''))]
    if got: f.append(f'받은 원본 {got}면')
    f.append(f"원문 판독 {sum(1 for s in sel if (s.get('원문') or '').strip())}건 · 번역 {sum(1 for s in sel if (s.get('번역') or '').strip())}건")
    if full.count('□') or full.count('(?)'): f.append(f"못 읽은 글자 □ {full.count('□')} · 불확실 (?) {full.count('(?)')}")
    chk = sum(1 for s in sel if '확인' in (s.get('해제') or ''))
    if chk: f.append(f'해제에 "확인 필요"를 단 문서 {chk}건')
    return f


def curator_html(c, facts=None, mode='exhibit'):
    """mode: exhibit(전시 웹페이지) · handout(활동지, 교사용) · index(첫 페이지)"""
    if not c and not facts: return ''
    keys = [k for k, _, _ in CURATOR_KEYS]
    if mode == 'handout': keys = ['why', 'message', 'use', 'question']
    lab = {k: h for k, h, _ in CURATOR_KEYS}
    rows = ''.join(f'<div class="cn-i"><b>{lab[k]}</b><p>{html.escape(c[k]).replace(chr(10), "<br>")}</p></div>' for k in keys if c.get(k))
    fx = ('<p class="cn-f"><b>제작 기록</b> ' + ' · '.join(html.escape(x) for x in facts) + '</p>') if facts and mode != 'handout' else ''
    head = {'exhibit': '큐레이터 노트 — 이 전시를 만든 이유', 'handout': '선생님께 — 이 자료를 만든 이유와 쓰는 법', 'index': '큐레이터 노트 — 비하인드'}[mode]
    css = ('<style>.cn{max-width:980px;margin:0 auto 6vh;padding:26px 30px;border:1px solid #4a3e2c;border-radius:16px;background:#1e1912;font:16px/1.8 "Noto Sans KR","Malgun Gothic",sans-serif;color:#e8dcc4}'
           '.cn h2{font:700 24px "Noto Serif KR",serif;color:#f3ead8;margin:0 0 14px}.cn-i{margin:0 0 12px}.cn-i b{color:#c4964a;display:block;font-size:14px;letter-spacing:.04em}.cn-i p{margin:2px 0 0}'
           '.cn-f{border-top:1px dashed #4a3e2c;padding-top:10px;margin:14px 0 0;color:#b9ab90;font-size:14px}.cn-f b{color:#c4964a;margin-right:6px}'
           '.cn.h{background:#faf6ec;color:#222;border-color:#c9b48a;font-size:13.5px;padding:12px 16px;page-break-inside:avoid}.cn.h h2{color:#222;font-size:17px}.cn.h .cn-i b{color:#8a6a2e}'
           '@media print{.cn{background:#fff;color:#111}.cn h2{color:#111}}</style>')
    return f'<!--CURATOR-->{css}<section class="cn{" h" if mode == "handout" else ""}" id="curator"><h2>{head}</h2>{rows}{fx}</section><!--/CURATOR-->'


def put_curator(page, block, where='</main>'):
    """HTML에 큐레이터 노트 넣기(다시 실행해도 하나만)"""
    page = re.sub(r'<!--CURATOR-->.*?<!--/CURATOR-->', '', page, flags=re.S)
    if not block: return page
    i = page.find(where) if where else -1
    return page[:i + len(where)] + block + page[i + len(where):] if i >= 0 else page.replace('</body>', block + '</body>')



# ---------------------------------------------------------------- 2차 홍보: 비하인드 카드 · 채널별 홍보안
def note_card(label, big, blocks, out, img=None, foot='', size=(1080, 1350), big_size=60, ph=None, center=False):
    """글 중심 카드 — label(작은 금색) · big(큰 글씨, 세리프) · blocks[(소제목, 본문)] · 위쪽에 흐린 문서 이미지(꽉 채움)"""
    W, H = size; c = Image.new('RGB', size, (22, 19, 15)); d = ImageDraw.Draw(c)
    src = ph if ph is not None else (Image.open(img).convert('RGB') if img and os.path.exists(img) else None)
    top = 110
    if src is not None:
        bh = 620; r = max(W / src.width, bh / src.height); im = src.resize((int(src.width * r) + 1, int(src.height * r) + 1))
        im = im.crop(((im.width - W) // 2, max(0, int((im.height - bh) * 0.25)), (im.width - W) // 2 + W, max(0, int((im.height - bh) * 0.25)) + bh))
        im = Image.blend(im, Image.new('RGB', im.size, (22, 19, 15)), 0.5)
        mask = Image.linear_gradient('L').resize((W, bh)); c.paste(im, (0, 0)); c.paste(Image.new('RGB', (W, bh), (22, 19, 15)), (0, 0), mask); top = 360
    fb = font(big_size, 'serif'); bl = wrap(d, big, fb, W - 140)[:5]
    body = [(h, wrap(d, b, font(32), W - 140)[:5]) for h, b in blocks if b]
    hgt = 62 + len(bl) * int(big_size * 1.35) + 24 + sum(44 + len(ls) * 46 + 22 for _, ls in body)
    y = max(top, H - 200 - hgt) if src is not None and not center else max(top, (H - 150 - hgt) // 2)  # 이미지가 있으면 글을 아래쪽에(카드), 영상 프레임은 가운데
    d.text((70, y), label, font=font(30, 'bold'), fill=GOLD); y += 62
    for ln in bl: d.text((70, y), ln, font=fb, fill=PAPER); y += int(big_size * 1.35)
    y += 24
    for head, ls in body:
        if y > H - 230: break
        d.text((70, y), head, font=font(28, 'bold'), fill=GOLD); y += 44
        for ln in ls:
            if y > H - 190: break
            d.text((70, y), ln, font=font(32), fill=(220, 210, 192)); y += 46
        y += 22
    d.line((70, H - 130, W - 70, H - 130), fill=(80, 70, 55), width=2); ff = font(24)
    for k, ln in enumerate(wrap(d, foot, ff, W - 140)[:2]):
        d.text((70, H - 108 + k * 36), ln, font=ff, fill=(160, 150, 130))
    c.save(out, quality=92)


def behind_cards(c, facts, title, src_line, img, outdir, ph=None, ext='png'):
    """큐레이터 노트로 비하인드 카드 3장: 전하고 싶은 것 · 만들며 있었던 일 · 남겨 둔 질문"""
    os.makedirs(outdir, exist_ok=True); out = []
    foot = f'{title} · {src_line}'
    if c.get('message'):
        out.append(os.path.join(outdir, f'b1_전하고싶은것.{ext}'))
        note_card('비하인드 ① 이 이야기를 만든 이유', c['message'], [('왜 이 문서들인가', c.get('why', '')), ('이렇게 보이길 바랐다', c.get('look', ''))], out[-1], img=img, foot=foot, ph=ph)
    if c.get('behind') or facts:
        out.append(os.path.join(outdir, f'b2_만들며있었던일.{ext}'))
        note_card('비하인드 ② 만들며 있었던 일', c.get('behind') or '원문을 끝까지 읽고, 읽지 못한 글자는 □로 남겼습니다.', [('제작 기록', ' · '.join(facts or [])), ('이렇게 써 주세요', c.get('use', ''))], out[-1], foot=foot, big_size=46)
    if c.get('question'):
        out.append(os.path.join(outdir, f'b3_남겨둔질문.{ext}'))
        note_card('비하인드 ③ 남겨 둔 질문', c['question'], [('여러분의 생각은?', '댓글로 나눠 주세요. 틀린 판독이나 더 아는 이야기도 환영합니다.')], out[-1], img=img, foot=foot, big_size=58)
    return out


CHANNELS = [  # (채널, 형식·길이, 무엇을 쓰나, 톤·요령)
    ('인스타그램 (피드·릴스)', '카드 4–10장 / 릴스 30–90초', 'cards/ · 비하인드 카드 · 릴스 영상 · promo.md', '첫 장에 원문 한 줄과 질문. 마지막 장에 출처·전시 링크. 해시태그 8–15개'),
    ('유튜브 (쇼츠·롱폼)', '쇼츠 60초 / 가로 3–8분', '가로 영상 · 자막 srt · 원문 판독·번역', '제목에 원문 인용 + 연도. 설명란에 판독·해제 요약과 원본 링크, 챕터'),
    ('틱톡', '15–60초', '릴스 영상(세로) · 비하인드 카드', '첫 2초에 "이 종이에 적힌 말" 자막. 질문형 캡션, 이어 보기 시리즈 태그'),
    ('페이스북', '긴 글 + 카드 묶음', 'promo.md 본문 · 카드 · 전시 웹페이지 링크', '이야기 전체를 들려주는 긴 글. 지역·문중·동문 그룹 공유'),
    ('스레드 (Threads)', '짧은 글 3–5개 연결', '이야기 · 큐레이터 노트 · 남겨 둔 질문', '한 글에 한 장면. 마지막 글에 질문과 링크'),
    ('X (트위터)', '280자 · 타래', '원문 인용 한 줄 · 카드 1장', '"현대어(原文)" 한 줄 + 연도 + 링크. 타래로 문서마다 한 트윗'),
    ('블로그·뉴스레터', '1,500–3,000자', '전시 웹페이지 · 해제 · 큐레이터 노트', '검색 키워드(인물·지역·문서 유형)를 제목에. 원문 이미지 캡션에 출처'),
    ('온라인 전시', '웹페이지 1개', 'exhibit.html · index.html', '그대로 공개(이미지 공개 전엔 --placeholder). 큐레이터 노트를 끝에'),
    ('오프라인 전시', '패널 6–12개 · 영상 1대', '카드(인쇄 300dpi 재출력 권장) · 원본 묶음 · 활동지', '원본 사진을 크게, 판독·번역을 옆에. QR로 전시 웹페이지·영상 연결. 소장처 대여·동의 협의'),
    ('수업·교육', '1–2차시', 'handout.html · 원문 판독·번역 · 큐레이터 노트 「선생님께」', '찾아보기 → 읽기 → 생각하기 순. 남겨 둔 질문으로 토론'),
    ('책·도록', '꼭지당 4–8쪽', '원본 사진(문서 전체) · 판독·번역·해제 · 이야기', '한 꼭지 = 한 편. 원문 전문과 번역을 마주 보게. 출판 전 소장처 이미지 사용 허가'),
    ('소설·논픽션', '단편 1편 / 장편의 한 장', '이야기 · 원문 인용 · 남겨 둔 질문', '문서에 적힌 사실을 뼈대로, 빈 곳은 허구임을 밝히고 상상. 남겨 둔 질문이 좋은 출발점'),
    ('웹툰', '4컷 / 1화 40–60컷', '원본 사진(배경·소품 고증) · 이야기 장면', '문서가 등장하는 장면을 클라이맥스로. 마지막 컷에 실제 문서 사진과 출처'),
    ('영화·드라마', '로그라인 · 시놉시스 · 씬', '이야기 · 인물·연대 · 원문 대사', '원문 한 줄을 대사로. 문서 속 날짜를 사건의 시계로. 사실과 각색 구분'),
    ('광고·CF·브랜드', '15–30초', '원문 한 줄 · 카드 이미지 · 큐레이터 노트의 메시지', '"오래 지켜 온 것"의 가치와 연결(예: 기록·신뢰·가족). 상업 이용은 소장처·제작자 허가'),
    ('팟캐스트·라디오', '10–20분', '이야기 · 판독·번역 낭독 · 비하인드', '원문을 소리 내어 읽고 번역. 만들며 있었던 일로 대화'),
]


def channel_plan(c, title, coll, url, quote='', ep='', tags=''):
    """채널별 홍보안(초안) — 큐레이터 노트·이야기에서 채널마다 바로 쓸 문구"""
    msg = c.get('message', '[전하고 싶은 것]'); q = c.get('question', '[남겨 둔 질문]'); why = c.get('why', '')
    qline = quote or '[원문 한 줄 — 현대어(原文)]'
    L = [f'# 채널별 홍보안 — {title}', '', f'{coll} · 전시: {url}', '', '> 큐레이터 노트와 이야기에서 뽑은 초안입니다. 이미지를 쓰는 채널은 출처 표기(한국학중앙연구원 한국고문서자료관 · ' + coll + ')와 소장처 이용 조건을 지키세요.', '',
         '## 한눈에 — 채널별 형식', '', '| 채널 | 형식·길이 | 쓰는 파일 | 요령 |', '|---|---|---|---|'] + [f'| {a} | {b} | {cc} | {d} |' for a, b, cc, d in CHANNELS] + ['']
    L += ['## 바로 쓰는 문구', '',
          '### X (280자)', '```', f'{qline}', f'{coll}에 남은 종이 한 장. {msg}'[:200], url, '#고문서한장 ' + ' '.join(tags.split()[:3]), '```', '',
          '### 스레드 (3개 연결)', '```', f'① {qline}', '', f'② {why}', '', f'③ {q} 여러분 생각은? {url}', '```', '',
          '### 유튜브', f'- 제목: {title} | 원문으로 읽는 고문서' + (f' (EP.{ep})' if ep else ''), f'- 설명 첫 줄: {msg}', '- 챕터: 00:00 질문 · 00:10 문서 · 원문 판독 · 이야기 · 00:50 비하인드', '',
          '### 틱톡 / 쇼츠 자막 첫 2초', '```', f'이 종이에 적힌 말: {qline}', '```', '',
          '### 페이스북 (긴 글 첫 문단)', '```', f'{why} {msg}', '```', '',
          '### 인스타그램 비하인드 카드 캡션', '```', f'✍️ 비하인드 — {msg}', '', f'💬 {q}', '', f'▶ {url}', '```', '',
          '## 확장 아이디어 (오프라인 · 원천 스토리)', '',
          f'- **오프라인 전시 패널 제목**: {title}',
          f'- **책·도록 꼭지 제목**: {title} — {coll}',
          f'- **소설·웹툰 출발 질문**: {q}',
          f'- **영화·드라마 로그라인(초안)**: {why} 그 종이 한 장에서 시작하는 이야기.',
          f'- **광고·브랜드 메시지**: {msg}', '',
          '## 지켜야 할 것', '', '- 이미지: 소장처 동의 없이 상업적 이용·재배포 금지. 공개 전이면 `mediate --placeholder` 결과물로.', '- 판독·번역은 초안: 인용할 때 "초안 · 원문 확인 필요"를 함께.', '- 각색(소설·웹툰·영상)은 사실과 허구를 구분해 밝히기.', '']
    return '\n'.join(L)


# ---------------------------------------------------------------- 전달 에디팅 (표현 · 방법 · 물질 · 통로 · 매개)
DELIVERY_KEYS = [('emotion', '핵심 정서', '보는 사람 마음에 남길 한 가지 감정 (예: 그리움, 경외, 억울함에서 안도로)'),
                 ('message', '한 문장', '이 묶음이 끝내 전하려는 말'),
                 ('open', '열기', '첫 장면 — 질문이나 낯선 한 줄로 시작'),
                 ('unfold', '펼치기', '문서를 어떤 순서·대비로 보여 줄지'),
                 ('climax', '절정', '가장 힘을 줄 원문 한 줄과 그 순간의 연출'),
                 ('after', '여운', '마지막 장면 — 무엇을 남기고 끝낼지'),
                 ('matter', '감각과 물질', '종이·빛·소리·냄새·크기·손으로 만지는 복제 등 물질과 감각의 장치'),
                 ('path', '통로와 매개', '온라인·오프라인 어떤 통로로, 어떤 순서로 만나게 할지'),
                 ('linger', '여운 장치', '보는 사람이 참여하고 기억하게 하는 장치 (질문, 쓰기, 남기기)'),
                 ('before', '전달 에디팅 전', '기록을 그대로 늘어놓았을 때의 모습'),
                 ('afterd', '전달 에디팅 후', '같은 기록을 설계해 전했을 때의 모습')]
MATTER = [  # 문서 유형 → 물질·감각 제안
    (r'홍패', '붉은 종이를 실물 크기로 복제해 벽에 거는 연출'), (r'백패', '흰 종이 한 장에 조명 하나'),
    (r'고신|교지|칙명|관고|차첩', '어보·관인 탁본 스탬프를 찍어 보는 체험'), (r'유지|유서', '역마 방울·말발굽 소리와 함께 펼치는 두루마리'),
    (r'교서|녹권', '두루마리를 실제 길이로 펼친 복제'), (r'편지|간찰|언간|엽서|어찰', '손바닥 크기 복제를 직접 들고 읽기, 낭독 음성'),
    (r'소지|상서|등장|의송|청원', '연명한 이름을 벽에 길게 나열하고 관아 마당처럼 서서 읽는 동선'), (r'분재기|명문|매매|차용|계약', '값(무명·냥·원)을 오늘의 물건으로 바꿔 옆에 놓기, 수결 따라 그리기'),
    (r'절목|완문|규약|약속|향약|동계', '규약을 판에 새기고 관람객이 자기 규칙을 써 보는 벽'), (r'호적|호구|지패|준호구', '나의 신분증 만들기 체험 카드'),
    (r'홀기', '집례 목소리로 읽고 동작을 따라 하기'), (r'시권', '시험장 책상과 답안지 체험'), (r'제문|만사|치제', '조명을 낮추고 낭독, 촛불'),
    (r'초상|영정', '여러 번 다시 그린 얼굴을 투명 레이어로 겹치기'), (r'사전|물명고|책|첩', '책장을 넘기는 소리, 확대 열람대')]


def delivery_draft(sel, cur=None, hook='', question='', key=''):
    """selection.csv와 큐레이터 노트로 전달 설계 초안 — Claude·사용자가 다듬는 출발점"""
    cur = cur or {}
    qs = [q for s in sel for q in find_quotes(s.get('이야기'))]
    pick = next((q for q in qs if key and key in q[0]), qs[-1] if qs else None)  # key: 강조할 구절(있으면 그 인용)
    climax = f'"{pick[0]}({pick[1]})"' if pick else ''
    types = [s.get('문서유형') or '' for s in sel]
    mats = list(dict.fromkeys(m for t in types for rx, m in MATTER if re.search(rx, t)))[:3]
    ys = sorted(int(s['연도']) for s in sel if str(s.get('연도', '')).isdigit())
    span = f'{ys[0]}–{ys[-1]}년' if len(ys) > 1 and ys[0] != ys[-1] else (f'{ys[0]}년' if ys else '연대 미상')
    return {'message': cur.get('message', ''),
            'open': hook or (f'"{qs[0][0]}" — 이 한 줄로 질문을 연다' if qs else ''),
            'unfold': ' → '.join(dict.fromkeys(re.sub(r'\s+', ' ', re.sub(r'\([^)]*\)|^\d{4}[〜~\d년]*\s*', '', s.get('문서명') or '')).strip()[:18] for s in sel)) + f' ({span}) — ' + (cur.get('look') or '시간 순서와 대비로'),
            'climax': (climax + ' — 화면·공간에서 이 한 줄만 크게, 소리를 줄여 집중') if climax else '',
            'after': ((cur.get('question') or question) + ' — 질문으로 끝내고 답은 보는 사람에게') if (cur.get('question') or question) else '',
            'matter': ' · '.join(mats),
            'path': '온라인: 릴스(열기) → 카드뉴스(펼치기) → 전시 웹페이지(절정·원문) → 비하인드 카드(여운) / 오프라인: 원본 크기 복제·낭독·참여 벽 / 남기기: 활동지·질문 카드',
            'before': f'{len(sel)}건의 문서를 {span} 연대순으로 놓고 문서명 · 유형 · 해설을 붙인다 — 정확하지만, 지나가면 잊힌다.',
            'afterd': ''}


def delivery_template(title, draft=None):
    draft = draft or {}
    out = [f'# 전달 에디팅 — {title}', '', '<!-- 같은 기록도 어떻게 표현하고, 어떤 물질과 통로로 전하느냐에 따라 마음에 남는 정도가 달라집니다. 초안을 다듬으세요. 빈 칸은 결과물에 나오지 않습니다. -->', '']
    for k, h, g in DELIVERY_KEYS: out += [f'## {h}', f'<!-- {g} -->', draft.get(k, ''), '']
    return '\n'.join(out)


def read_delivery(ed):
    p = os.path.join(ed, 'delivery.md')
    if not os.path.exists(p): return {}
    t = re.sub(r'<!--.*?-->', '', open(p, encoding='utf-8').read(), flags=re.S)
    rev = {h: k for k, h, _ in DELIVERY_KEYS}; c = {}
    for m in re.finditer(r'^##\s*(.+?)\s*\n(.*?)(?=^##\s|\Z)', t, flags=re.S | re.M):
        k = rev.get(m.group(1).strip())
        if k and m.group(2).strip(): c[k] = m.group(2).strip()
    return c


def delivery_html(dv, mode='exhibit'):
    if not dv: return ''
    lab = {k: h for k, h, _ in DELIVERY_KEYS}; e = html.escape
    flow = ''.join(f'<div class="dv-s"><b>{lab[k]}</b><p>{e(dv[k])}</p></div>' for k in ('open', 'unfold', 'climax', 'after') if dv.get(k))
    side = ''.join(f'<div class="dv-i"><b>{lab[k]}</b><p>{e(dv[k])}</p></div>' for k in ('matter', 'path', 'linger') if dv.get(k))
    ba = (f'<div class="dv-ba"><div><b>{lab["before"]}</b><p>{e(dv.get("before", ""))}</p></div><div><b>{lab["afterd"]}</b><p>{e(dv.get("afterd", ""))}</p></div></div>' if dv.get('before') or dv.get('afterd') else '')
    css = ('<style>.dv{max-width:980px;margin:0 auto 6vh;padding:26px 30px;border:1px solid #4a3e2c;border-radius:16px;background:#191510;font:16px/1.75 "Noto Sans KR","Malgun Gothic",sans-serif;color:#e8dcc4}'
           '.dv h2{font:700 24px "Noto Serif KR",serif;color:#f3ead8;margin:0 0 6px}.dv .em{color:#c4964a;font-weight:700}.dv-flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:14px 0}'
           '.dv-s{background:#231d15;border-radius:12px;padding:10px 12px;border-top:3px solid #c4964a}.dv-s b,.dv-i b,.dv-ba b{color:#c4964a;font-size:13.5px}.dv-s p,.dv-i p,.dv-ba p{margin:3px 0 0;font-size:14.5px}'
           '.dv-i{margin:8px 0}.dv-ba{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}.dv-ba>div{background:#231d15;border-radius:12px;padding:10px 12px}.dv-ba>div:first-child{border:1px dashed #4a3e2c;background:#1c1712}'
           '@media(max-width:700px){.dv-ba{grid-template-columns:1fr}}</style>')
    head = f'<h2>연출 노트 — 이 기록을 이렇게 전합니다</h2><p>{("핵심 정서 <span class=em>" + e(dv["emotion"]) + "</span>") if dv.get("emotion") else ""}{(" · " + e(dv["message"])) if dv.get("message") else ""}</p>'
    return f'<!--DELIVERY-->{css}<section class="dv" id="delivery">{head}<div class="dv-flow">{flow}</div>{side}{ba}</section><!--/DELIVERY-->'


def put_delivery(page, block, where='</main>'):
    page = re.sub(r'<!--DELIVERY-->.*?<!--/DELIVERY-->', '', page, flags=re.S)
    if not block: return page
    i = page.find(where)
    return page[:i + len(where)] + block + page[i + len(where):] if i >= 0 else page.replace('</body>', block + '</body>')


def cmd_delivery(a):
    """문구 에디팅을 마친 뒤 전달 에디팅 초안을 다시 만들기 (절정 원문 후보·여운 질문이 채워짐)"""
    ed = os.path.join(a.work, 'edit', a.theme)
    sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
    th = json.load(open(os.path.join(ed, 'theme.json'), encoding='utf-8')) if os.path.exists(os.path.join(ed, 'theme.json')) else {}
    p = os.path.join(ed, 'delivery.md'); old = read_delivery(ed)
    filled = {k for k in old if k in ('emotion', 'linger', 'afterd')}  # 사람이 쓰는 칸이 차 있으면 보호
    if filled and not a.force:
        sys.exit(f'delivery.md에 이미 쓴 칸이 있습니다({", ".join(sorted(filled))}). 덮어쓰려면 --force (기존 파일은 delivery.bak.md로 보관)')
    if os.path.exists(p): shutil.copy(p, os.path.join(ed, 'delivery.bak.md'))
    dr = delivery_draft(sel, read_curator(ed), key=a.key or '')
    open(p, 'w', encoding='utf-8').write(delivery_template(th.get('title') or a.theme, dr))
    print('→', p); [print(f'  {h}: {dr.get(k, "")[:70]}') for k, h, _ in DELIVERY_KEYS if dr.get(k)]


FIELDS = ('판독', '원문', '번역', '해제', '요약', '이야기', '캡션', '연도', '문서유형', '인물', '검토')
CORR_COLS = ['날짜', '순서', '자료ID', '문서명', '칸', '이전', '이후', '근거', '제보']


def read_corrections(ed):
    p = os.path.join(ed, 'corrections.csv')
    return list(csv.DictReader(open(p, encoding='utf-8-sig'))) if os.path.exists(p) else []


def parse_issue(body):
    """「판독 고침 제보」 양식 → {자료ID, 문서, 칸, 내용, 근거}"""
    b = (body or '').replace('\r', '')
    if re.search(r'^###\s', b, re.M):  # GitHub 이슈 양식(.github/ISSUE_TEMPLATE/correction.yml)으로 쓴 글
        sec = {m.group(1).strip(): m.group(2).strip() for m in re.finditer(r'^###\s*(.+?)\s*\n(.*?)(?=^###\s|\Z)', b, re.S | re.M)}
        val = lambda k: '' if sec.get(k, '') in ('_No response_', '') else sec[k]
        where = val('고칠 곳')
        return {'자료ID': val('자료 ID'), '문서': val('문서'), '칸': next((f for f in FIELDS if f == where or f in where), ''), '고칠 곳': where, '내용': val('바르게 고친 내용'), '근거': val('근거')}
    get = lambda k: (re.search(rf'^{k}\s*:\s*(.*)$', b, re.M) or [None, ''])[1].strip()
    sec = lambda head, nxt: (re.search(rf'{head}[^\n]*:\s*\n(.*?)(?=\n\s*{nxt}|\Z)', b, re.S) or [None, ''])[1].strip()
    where = sec('고칠 곳', '바르게 고친 내용')
    field = next((f for f in FIELDS if f in where), '')
    return {'자료ID': get('자료 ID'), '문서': get('문서'), '칸': field, '고칠 곳': where, '내용': sec('바르게 고친 내용', '근거'), '근거': sec('근거', '$^')}


def cmd_fix(a):
    """판독 고침 반영 — selection.csv의 한 칸을 고치고 corrections.csv에 이전·이후·근거를 남긴다"""
    import datetime
    if a.from_:
        return fix_from(a.from_, a.in_ or ([os.path.join(a.work, 'edit', a.theme)] if a.work and a.theme else ['.']), apply=a.apply)
    if not (a.work and a.theme): sys.exit('--work · --theme (또는 --from 편집기.json --in 폴더)을 주세요.')
    ed = os.path.join(a.work, 'edit', a.theme); p = os.path.join(ed, 'selection.csv')
    if not os.path.exists(p): sys.exit(f'{p}이(가) 없습니다.')
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig'))); cols = list(rows[0].keys()) if rows else []
    log = read_corrections(ed)
    if a.list:
        if not log: print('고친 기록이 없습니다.'); return
        for c in log:
            o, n = c['이전'], c['이후']; k = next((i for i, (x, y) in enumerate(zip(o, n)) if x != y), min(len(o), len(n)))
            st = max(0, k - 12); print(f"{c['날짜']} · {c['순서']}. {c['문서명'][:24]} · {c['칸']} · …{o[st:k + 24]!r} → …{n[st:k + 24]!r}" + (f" · {c['제보']}" if c.get('제보') else ''))
        return
    issue = {}
    if a.issue:
        if not a.repo: sys.exit('--issue 와 함께 --repo 아이디/저장소 를 주세요.')
        import urllib.request
        req = urllib.request.Request(f'https://api.github.com/repos/{a.repo}/issues/{a.issue}', headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'aks-archive-harvester'})
        try: data = json.load(urllib.request.urlopen(req, timeout=20))
        except Exception as e: sys.exit(f'제보를 읽지 못했습니다({type(e).__name__}): 저장소 · 번호 · 인터넷 연결을 확인하세요.')
        issue = parse_issue(data.get('body')); issue['url'] = data.get('html_url', '')
        print(f"제보 #{a.issue}: {data.get('title', '')}\n  문서: {issue['문서']}  ({issue['자료ID']})\n  고칠 곳: {issue['고칠 곳'] or '(비어 있음)'}\n  고친 내용: {issue['내용'] or '(비어 있음)'}\n  근거: {issue['근거'] or '(비어 있음)'}")
    # 문서 찾기
    tgt = None
    if a.n: tgt = next((r for r in rows if str(r.get('순서')) == str(a.n)), None)
    elif issue.get('자료ID'): tgt = next((r for r in rows if r.get('자료ID') == issue['자료ID']), None)
    if not tgt and issue.get('문서'):  # 자료 ID가 없으면 문서명으로
        nm = issue['문서'].strip(); tgt = next((r for r in rows if r.get('문서명') == nm), None) or next((r for r in rows if nm and (nm in r.get('문서명', '') or r.get('문서명', '') in nm)), None)
    if not tgt: sys.exit('고칠 문서를 찾지 못했습니다 — --n 순서 를 주세요.' if not issue else f"이 테마에 자료 ID {issue.get('자료ID')} 문서가 없습니다 — 다른 --theme 이거나 --n 으로 지정하세요.")
    field = a.field or issue.get('칸')
    if field not in FIELDS: sys.exit(f'고칠 칸(--field)을 정하세요: {" · ".join(FIELDS)}')
    text = a.text if a.text is not None else issue.get('내용', '')
    if a.text is None and not a.replace_part and '→' in text and text.count('→') == 1:  # 제보가 "이전 → 이후" 꼴이면 그 구절만
        a.replace_part, text = [x.strip() for x in text.split('→')]
        print(f'  제보의 「{a.replace_part} → {text}」 꼴을 구절 바꾸기로 읽었습니다.')
    if not text: sys.exit('바꿀 내용(--text)이 없습니다.')
    if a.replace_part:  # 칸 전체가 아니라 일부만: --replace-part "이전 구절"
        if a.replace_part not in (tgt.get(field) or ''): sys.exit(f'「{a.replace_part}」를 {field} 칸에서 찾지 못했습니다.')
        new = tgt[field].replace(a.replace_part, text, 1)
    else: new = text
    old = tgt.get(field) or ''
    print(f"\n{tgt['순서']}. {tgt['문서명']} — {field}\n  이전: {old[:200]}\n  이후: {new[:200]}")
    if not a.replace_part and old and len(new) < len(old) * 0.5:
        print('  ※ 칸 전체가 이 내용으로 바뀝니다. 일부 구절만 고치려면 --replace-part "이전 구절" 을 함께 주세요.')
    if not a.apply: print('\n(미리 보기입니다. 반영하려면 --apply)'); return
    tgt[field] = new
    with open(p, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    log.append({'날짜': datetime.date.today().isoformat(), '순서': tgt['순서'], '자료ID': tgt.get('자료ID', ''), '문서명': tgt['문서명'], '칸': field, '이전': old, '이후': new,
                '근거': a.note or issue.get('근거', ''), '제보': issue.get('url') or (f'#{a.issue}' if a.issue else '')})
    with open(os.path.join(ed, 'corrections.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=CORR_COLS); w.writeheader(); w.writerows(log)
    print(f'\n→ 반영했습니다. 고친 기록 {len(log)}건: {ed}/corrections.csv · 결과물에 넣으려면 mediate(· promo · video)를 다시 실행하세요.')


def fix_from(path, roots, apply=False, by=None):
    """원문 대조 편집기에서 내보낸 corrections JSON → 자료ID로 맞춰 roots 아래 selection.csv에 한꺼번에 반영.
    칸마다 corrections.csv에 이전 · 이후 · 근거 · 제보(검토자)를 남기고, 줄맞춤은 align.json에, 검토 표시는 검토자가 직접 한 것만 옮긴다.
    이전 값이 지금 selection.csv와 다르면(그사이 다른 고침이 있었으면) 덮어쓰지 않고 건너뛴다."""
    import datetime
    j = json.load(open(path, encoding='utf-8'))
    items, align, revs = j.get('고침') or [], j.get('줄맞춤') or {}, j.get('검토') or []
    if not (items or align or revs): sys.exit(f'{path}에 고친 내용이 없습니다.')
    files = sorted({f for root in roots for f in ([root] if root.endswith('.csv') else glob.glob(os.path.join(root, '**', 'selection.csv'), recursive=True))})
    where = {}  # 자료ID → [(파일, 순서)]
    for f in files:
        for r in csv.DictReader(open(f, encoding='utf-8-sig')):
            if r.get('자료ID'): where.setdefault(r['자료ID'].strip(), []).append((f, str(r.get('순서'))))
    def locate(it):
        hits = where.get((it.get('자료ID') or '').strip(), [])
        if len(hits) > 1 and it.get('편'): hits = [h for h in hits if os.path.basename(os.path.dirname(h[0])) == it['편']] or hits
        if not hits and it.get('편'):  # 자료ID가 없으면 편 폴더 이름 + 순서
            hits = [(f, str(it.get('순서'))) for f in files if os.path.basename(os.path.dirname(f)) == it['편']]
        return hits
    plan, skip = {}, []
    for it in items:
        if it.get('칸') not in FIELDS or it.get('칸') == '검토': skip.append((it, '고칠 수 없는 칸')); continue
        hits = locate(it)
        if not hits: skip.append((it, '그 자료ID · 편을 찾지 못함')); continue
        for f, n in hits: plan.setdefault(f, []).append((n, it))
    total = 0
    for f, lst in plan.items():
        rows = list(csv.DictReader(open(f, encoding='utf-8-sig'))); cols = list(rows[0].keys()); ed = os.path.dirname(f)
        log = read_corrections(ed); hit = 0
        for n, it in lst:
            r = next((x for x in rows if str(x.get('순서')) == n), None)
            if r is None: skip.append((it, f'{f}에 순서 {n} 없음')); continue
            fld, old, newv = it['칸'], r.get(it['칸']) or '', it.get('이후') or ''
            if old == newv: continue
            if (it.get('이전') or '') != old: skip.append((it, f'{os.path.basename(ed)} {n}번 {fld}: 내보낸 뒤 selection.csv가 바뀜 — 편집기에서 다시 열어 고치세요')); continue
            k = next((i for i, (x, y) in enumerate(zip(old, newv)) if x != y), min(len(old), len(newv))); st = max(0, k - 10)
            print(f"  {os.path.basename(ed)} · {n}. {r.get('문서명', '')[:20]} · {fld}: …{old[st:k + 16]!r} → …{newv[st:k + 16]!r}")
            r[fld] = newv; hit += 1
            log.append({'날짜': datetime.date.today().isoformat(), '순서': n, '자료ID': r.get('자료ID', ''), '문서명': r.get('문서명', ''), '칸': fld, '이전': old, '이후': newv,
                        '근거': it.get('근거') or '', '제보': '대조 편집기' + (f" · {it.get('검토자') or by}" if (it.get('검토자') or by) else '')})
        total += hit
        if hit and apply:
            with open(f, 'w', newline='', encoding='utf-8-sig') as fh:
                w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
            with open(os.path.join(ed, 'corrections.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
                w = csv.DictWriter(fh, fieldnames=CORR_COLS); w.writeheader(); w.writerows(log)
    nal = 0
    for key, a in align.items():
        hits = locate({'자료ID': key if '#' not in key else '', '편': a.get('편'), '순서': a.get('순서')})
        for f, n in hits:
            ap = os.path.join(os.path.dirname(f), 'align.json')
            cur = json.load(open(ap, encoding='utf-8')) if os.path.exists(ap) else {}
            cur[key if '#' not in key else n] = {'방향': a.get('방향', 'v'), '줄자리': a.get('줄자리', []), '짝': a.get('짝', {})}; nal += 1
            if apply: json.dump(cur, open(ap, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    nrev = 0
    if revs:
        rec = {}
        for r in revs:
            if r.get('검토자'): rec[(r.get('자료ID') or '').strip()] = f"{r['검토자']} {r.get('날짜', '')}".strip()
        for f in files:
            rows = list(csv.DictReader(open(f, encoding='utf-8-sig'))); hit = 0
            for r in rows:
                st = rec.get((r.get('자료ID') or '').strip())
                if st and r.get('검토') != st: r['검토'] = st; hit += 1; print(f"  {os.path.basename(os.path.dirname(f))} · {r['순서']}. {r['문서명'][:20]} → 검토: {st}")
            nrev += hit
            if hit and apply:
                with open(f, 'w', newline='', encoding='utf-8-sig') as fh:
                    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    for it, why in skip: print(f"  ⚠ 건너뜀 — {it.get('편', '')} {it.get('순서', '')} {it.get('칸', '')}: {why}")
    print(f"\n{'반영했습니다' if apply else '(미리 보기 — 반영하려면 --apply)'}: 고친 칸 {total} · 줄맞춤 {nal} · 검토 표시 {nrev} · 건너뜀 {len(skip)}"
          + (' · 결과물(전시 웹페이지 · 손에 드는 판 · 검토지)에 넣으려면 mediate(· promo · proof)를 다시 실행하세요.' if apply and total else ''))


COMPARE_FIELDS = ('판독', '원문', '번역', '해제', '요약', '이야기', '캡션', '연도', '문서유형', '인물')


def compare_page(mode, data=None, font_url=None, font=False):
    """원문 대조 편집기 페이지(assets/compare.html)를 채움. mode: embedded(사진까지 한 파일) · folder(편 폴더를 열어 씀) · site(공유판)"""
    fp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'compare.html')
    page = open(fp, encoding='utf-8').read().replace('__MODE__', mode)
    if data is not None:
        page = page.replace('<script id="data" type="application/json">null</script>',
                            '<script id="data" type="application/json">' + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + '</script>')
    css = oldhangul_css('\u1100\u119e' if font or data is None else json.dumps(data, ensure_ascii=False), font_url)  # 옛한글이 있으면 글꼴 조각(편을 열어 쓰는 판은 늘)
    return page.replace('<!--OLDHANGUL-->', css)


def compare_doc(r, img='', align=None):
    al = (align or {}).get(r.get('자료ID') or '\0') or (align or {}).get(str(r.get('순서')))
    return {'align': al} | {'n': str(r.get('순서')), 'id': r.get('자료ID', ''), 'name': r.get('문서명', ''), 'year': r.get('연도', ''), 'viewer': r.get('뷰어링크', ''),
            'review': r.get('검토', ''), 'f': {k: r.get(k) or '' for k in COMPARE_FIELDS}, 'img': img}


def cmd_compare(a):
    """원문 대조 편집기 — 원본 사진 옆에 판독을 한 줄씩 짝지어 보고 고치는 페이지. 고친 내용은 JSON으로 내보내 fix --from 으로 반영"""
    if a.folder_page:
        root = os.path.dirname(os.path.abspath(a.folder_page)); idx = []
        for sp_ in sorted(glob.glob(os.path.join(root, '*', 'selection.csv'))):
            d = os.path.dirname(sp_); key = os.path.basename(d); t, ep = key, ''
            if os.path.exists(os.path.join(d, 'theme.json')): t = json.load(open(os.path.join(d, 'theme.json'), encoding='utf-8')).get('title', key)
            if os.path.exists(os.path.join(d, 'record.json')): ep = json.load(open(os.path.join(d, 'record.json'), encoding='utf-8')).get('episode', '')
            idx.append({'key': key, 'title': t, 'ep': ep})
        num = lambda x: int(re.sub(r'\D', '', x['ep']) or 9999)
        idx.sort(key=lambda x: (num(x), x['key']))
        page = compare_page('folder', {'index': idx}, font=True)
        open(a.folder_page, 'w', encoding='utf-8').write(page)
        print(f'  편 목록 {len(idx)}편 (웹에서 열면 고르기만 하면 됨 · 주소 끝 #폴더이름 으로 바로 열기)')
        print(f'→ {a.folder_page}  (편 폴더를 열어 쓰는 대조 편집기 · 사진은 그 편의 exhibit.html에서 읽음)'); return
    if a.example:
        ed = a.example.rstrip('/'); sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
        ex = open(os.path.join(ed, 'exhibit.html'), encoding='utf-8').read() if os.path.exists(os.path.join(ed, 'exhibit.html')) else ''
        imgs = [(re.search(r'src="(data:image/[a-z]+;base64,[^"]+)"', seg) or [None, ''])[1] for seg in ex.split('<section class="panel">')[1:]]
        key = os.path.basename(ed); out = a.out or f'compare-{key}.html'
    else:
        if not (a.work and a.theme): sys.exit('--work · --theme (또는 --example 편폴더 · --folder-page 파일)을 주세요.')
        ed = os.path.join(a.work, 'edit', a.theme); sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
        imgs = []
        for r in sel:
            orig = os.path.join(a.work, r.get('원본경로') or '')
            src = orig if r.get('원본경로') and os.path.exists(orig) else os.path.join(ed, r.get('이미지') or '')
            imgs.append(b64(src, a.max_px) if (r.get('원본경로') or r.get('이미지')) and os.path.exists(src) else '')
        key = a.theme; out = a.out or os.path.join(ed, 'compare.html')
    title = key
    tj = os.path.join(ed, 'theme.json')
    if os.path.exists(tj): title = json.load(open(tj, encoding='utf-8')).get('title', key)
    apath = os.path.join(ed, 'align.json'); al = json.load(open(apath, encoding='utf-8')) if os.path.exists(apath) else {}
    docs = [compare_doc(r, imgs[i] if i < len(imgs) else '', al) for i, r in enumerate(sel)]
    if imgs and len(imgs) != len(sel): print(f'  ※ 사진 {len(imgs)}장 · 문서 {len(sel)}건 — 짝이 맞지 않습니다.')
    open(out, 'w', encoding='utf-8').write(compare_page('embedded', {'key': key, 'title': title, 'docs': docs}))
    print(f'→ {out}  문서 {len(docs)}건 · 사진 {sum(1 for x in imgs if x)}장 (한 파일 · 인터넷 없이 열림)\n'
          f'  고친 뒤 「고친 내용 내보내기」로 받은 JSON을: studio.py fix --from 그파일.json --in {os.path.dirname(ed) or "."} --apply')


def corrections_html(log):
    if not log: return ''
    e = html.escape
    items = ''.join(f"<li><b>{e(c['날짜'])}</b> {e(c['문서명'])} — {e(c['칸'])}: <s>{e(c['이전'][:60])}</s> → {e(c['이후'][:60])}"
                    + (f" <small>(근거: {e(c['근거'][:80])})</small>" if c.get('근거') else '') + (f" <a href=\"{e(c['제보'])}\" target=\"_blank\" rel=\"noopener\">제보 ↗</a>" if c.get('제보', '').startswith('http') else '') + '</li>' for c in log)
    return (f'<section id="fixes" style="max-width:1100px;margin:40px auto;padding:0 6vw"><h2 style="font-size:20px">함께 고친 곳 — {len(log)}건</h2>'
            f'<p style="font-size:14px;opacity:.8">보는 분들의 제보와 다시 읽기로 고친 판독 · 번역 기록입니다. 고칠 곳을 보시면 「판독 고침 제보」로 알려 주세요.</p><ul style="font-size:14.5px;line-height:1.8">{items}</ul></section>')



def proof_html(todo, title, img, scope='(검토 칸이 빈 문서)'):
    """검토지 HTML — img(r): 문서 하나의 사진 <img> 태그"""
    e = html.escape
    unk = lambda t: (t or '').count('□') + (t or '').count('(?)')
    pages = ''.join(f"""<section class="sheet"><header><b>{e(r['순서'])}. {e(r['문서명'])}</b><span>{e(r.get('자료ID', ''))}{(' · □ · (?) ' + str(unk(r.get('판독')))) if unk(r.get('판독')) else ''}</span></header>
<div class="cols"><div class="pic">{img(r)}{('<p class="v">원본 뷰어: ' + e(r['뷰어링크']) + '</p>') if r.get('뷰어링크') else ''}</div>
<div class="txt"><h3>판독</h3><pre>{e(r.get('원문') or r.get('판독') or '(비어 있음)')}</pre><h3>번역</h3><p>{e(r.get('번역') or '(비어 있음)')}</p>
<h3>이야기 속 인용</h3><p>{e(' / '.join(f'"{q[0]}({q[1]})"' for q in find_quotes(r.get('이야기'))) or '—')}</p>
<h3>날짜 맞춤</h3><p>{e(' / '.join(f'⚠ {f}: {m}' for f, m in date_issues(r)) or '연호 · 왕대 · 간지 · 서기가 서로 맞습니다(자동 확인)')}</p>
<h3>인용 대조</h3><p>{e(' / '.join(f'⚠ {m}' for _, m in quote_issues(r)) or ('인용한 원문이 판독에 그대로 있습니다(자동 확인)' if find_quotes(r.get('이야기')) else '—'))}</p></div></div>
<div class="chk"><span>☐ 판독 대조</span><span>☐ 번역 대조</span><span>☐ 연도 · 인물</span><span>☐ 인용 원문 일치</span><span>검토자 ______ 날짜 ______</span></div>
<div class="memo">고칠 곳 (줄 · 이전 → 이후 · 근거)</div></section>""" for r in todo)
    page = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>검토지 — {e(title)}</title><style>
body{{font-family:'Noto Sans KR','Malgun Gothic',sans-serif;color:#111;margin:0;background:#eee}}.intro{{max-width:900px;margin:20px auto;padding:0 16px;font-size:14px}}
.sheet{{background:#fff;max-width:900px;margin:16px auto;padding:14mm 12mm;box-shadow:0 1px 4px #0002;page-break-after:always;break-after:page}}
header{{display:flex;justify-content:space-between;gap:12px;border-bottom:2px solid #111;padding-bottom:6px;margin-bottom:10px}}header span{{font-size:12px;color:#555}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.pic img{{width:100%;border:1px solid #ccc}}.noimg{{border:1px dashed #999;padding:40px;text-align:center;color:#777}}.v{{font-size:10px;color:#666;word-break:break-all}}
h3{{font-size:13px;margin:8px 0 4px;color:#7a5a24}}pre{{white-space:pre-wrap;font:15px/2 'Noto Serif KR','Batang',serif;margin:0}}.txt p{{font-size:13.5px;line-height:1.7;margin:0}}
.chk{{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:12px;font-size:13px}}.memo{{border:1px solid #999;height:38mm;margin-top:8px;padding:6px;font-size:12px;color:#666}}
@media print{{body{{background:#fff}}.intro{{display:none}}.sheet{{box-shadow:none;margin:0;max-width:none}}}}@page{{size:A4;margin:0}}</style></head><body>
<div class="intro"><b>검토지 — {e(title)}</b> · 문서 {len(todo)}건{scope} · 인쇄하면 한 장에 한 문서. 사진과 판독 · 번역을 대조해 표시한 뒤, 고칠 곳은 <code>studio.py fix</code>로, 확인을 마친 문서는 <code>studio.py review --n 번호 --by 이름</code>으로 표시하세요.</div>
{pages}</body></html>"""
    return put_oldhangul(page, oldhangul_css(page))


def cmd_proof(a):
    """검토지 — 사진 옆에 판독 · 번역을 놓고 사람이 대조해 표시하는 인쇄용 A4 (검토 칸이 빈 문서부터)"""
    ed = os.path.join(a.work, 'edit', a.theme); p = os.path.join(ed, 'selection.csv')
    if not os.path.exists(p): sys.exit(f'{p}이(가) 없습니다.')
    sel = list(csv.DictReader(open(p, encoding='utf-8-sig')))
    todo = sel if a.all else [r for r in sel if not r.get('검토')]
    if not todo: print('검토할 문서가 없습니다(모두 검토 표시됨). 모두 다시 보려면 --all'); return
    e = html.escape
    def img(r):
        if a.link:  # 사진을 페이지에 넣지 않고 edit/<테마>/images/ 를 가리킴(가볍게)
            return f'<img src="{e(r.get("이미지") or "")}" alt="{e(r["문서명"])}">' if r.get('이미지') else '<div class="noimg">사진 없음</div>'
        orig = os.path.join(a.work, r.get('원본경로') or '')
        src = orig if r.get('원본경로') and os.path.exists(orig) else os.path.join(ed, r.get('이미지') or '')
        return f'<img src="{b64(src, 1500)}" alt="{e(r["문서명"])}">' if os.path.exists(src) else '<div class="noimg">사진 없음</div>'
    title = json.load(open(os.path.join(ed, 'theme.json'), encoding='utf-8')).get('title', a.theme) if os.path.exists(os.path.join(ed, 'theme.json')) else a.theme
    out = os.path.join(ed, 'proof.html')
    open(out, 'w', encoding='utf-8').write(proof_html(todo, title, img, '' if a.all else '(검토 칸이 빈 문서)'))
    print(f'→ {out}  검토할 문서 {len(todo)}건 (인쇄용 A4, 한 장에 한 문서)')


def review_from(path, roots, dry=False):
    """reviews.csv(검토 현황 페이지에서 내려받은 것: 자료ID · 검토자 · 날짜) → roots 아래 모든 selection.csv의 같은 자료ID 문서에 「이름 날짜」"""
    recs = {}
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        i = (r.get('자료ID') or '').strip(); who = (r.get('검토자') or '').strip(); d = (r.get('날짜') or '').strip()
        if i and who: recs[i] = f'{who} {d}'.strip()
    if not recs: sys.exit(f'{path}에 자료ID · 검토자가 있는 줄이 없습니다.')
    files = sorted({f for root in roots for f in ([root] if root.endswith('.csv') else glob.glob(os.path.join(root, '**', 'selection.csv'), recursive=True))})
    seen, changed = set(), 0
    for f in files:
        rows = list(csv.DictReader(open(f, encoding='utf-8-sig')))
        if not rows: continue
        cols = list(rows[0].keys()); hit = 0
        for r in rows:
            st = recs.get((r.get('자료ID') or '').strip())
            if st:
                seen.add(r['자료ID'].strip())
                if r.get('검토') != st: r['검토'] = st; hit += 1
        if hit:
            changed += hit; print(f'  {f}: {hit}건')
            if not dry:
                with open(f, 'w', newline='', encoding='utf-8-sig') as fh:
                    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    miss = [i for i in recs if i not in seen]
    print(f'검토 기록 {len(recs)}건 → 반영 {changed}곳' + (' (미리 보기 — 쓰지 않음)' if dry else '') + (f' · 찾지 못한 자료ID {len(miss)}건: ' + ', '.join(miss[:3]) if miss else ''))
    print('결과물에 반영하려면 mediate(· series)를 다시 실행하세요.')


def cmd_review(a):
    """검토 표시 — 사람이 원문과 대조를 마친 문서의 검토 칸에 '이름 날짜'. 결과물의 '초안' 딱지가 빠진다"""
    import datetime
    if a.from_:
        return review_from(a.from_, a.in_ or ([a.work] if a.work else ['.']), dry=a.dry_run)
    if not (a.work and a.theme and a.n): sys.exit('--work · --theme · --n (또는 --from reviews.csv --in 폴더)을 주세요.')
    ed = os.path.join(a.work, 'edit', a.theme); p = os.path.join(ed, 'selection.csv')
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig'))); cols = list(rows[0].keys())
    want = {x.strip() for x in a.n.split(',') if x.strip()}
    stamp = '' if a.undo else f"{a.by} {datetime.date.today().isoformat()}"
    hit = [r for r in rows if str(r.get('순서')) in want]
    if not hit: sys.exit('그 순서의 문서가 없습니다.')
    for r in hit: r['검토'] = stamp; print(f"{r['순서']}. {r['문서명']} → 검토: {stamp or '(지움)'}")
    with open(p, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    left = sum(1 for r in rows if not r.get('검토'))
    print(f'남은 검토 {left}건 · 결과물에 반영하려면 mediate(· promo)를 다시 실행하세요.')


def cmd_page(a):
    """대표 면 바꾸기 — 두루마리 겉면·표지 대신 글이 있는 면을 카드·전시·영상에 쓰기"""
    ed = os.path.join(a.work, 'edit', a.theme); p = os.path.join(ed, 'selection.csv')
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig'))); cols = list(rows[0].keys()); done = 0
    for r in rows:
        if r['순서'] == str(a.n):
            src = os.path.join(a.work, os.path.dirname(r['원본경로']), a.page)
            if not os.path.exists(src): sys.exit(f'면이 없습니다: {src} (download로 그 면을 먼저 받으세요)')
            r['대표장'] = a.page; r['원본경로'] = os.path.relpath(src, a.work).replace(os.sep, '/')
            im = Image.open(src).convert('RGB'); im.thumbnail((1600, 1600)); im.save(os.path.join(ed, r['이미지']), quality=90); done = 1
    if not done: sys.exit(f'selection.csv에 {a.n}번 문서가 없습니다 (순서 칸 확인)')
    with open(p, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f'순서 {a.n} 대표 면 → {a.page} (mediate · video를 다시 실행하세요)')

# ---------------------------------------------------------------- report (비교 리포트)
# ---------------------------------------------------------------- 날짜 맞춤(연호 · 왕대 · 간지 · 서기)
STEMS, BRANCHES = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'
KSTEMS, KBRANCHES = '갑을병정무기경신임계', '자축인묘진사오미신유술해'
# 중국 · 대한제국 · 일본 연호: 원년(1년)의 서기. 한글 이름도 함께
ERAS = {'洪武': 1368, '永樂': 1403, '宣德': 1426, '正統': 1436, '景泰': 1450, '天順': 1457, '成化': 1465, '弘治': 1488, '正德': 1506, '嘉靖': 1522,
        '隆慶': 1567, '萬曆': 1573, '天啓': 1621, '崇禎': 1628, '順治': 1644, '康熙': 1662, '雍正': 1723, '乾隆': 1736, '嘉慶': 1796, '道光': 1821,
        '咸豐': 1851, '同治': 1862, '光緖': 1875, '光緒': 1875, '開國': 1392, '建陽': 1896, '光武': 1897, '隆熙': 1907, '明治': 1868, '大正': 1912, '昭和': 1926,
        '홍무': 1368, '영락': 1403, '선덕': 1426, '정통': 1436, '경태': 1450, '천순': 1457, '성화': 1465, '홍치': 1488, '정덕': 1506, '가정': 1522, '융경': 1567,
        '만력': 1573, '천계': 1621, '숭정': 1628, '순치': 1644, '강희': 1662, '옹정': 1723, '건륭': 1736, '가경': 1796, '도광': 1821, '함풍': 1851, '동치': 1862,
        '광서': 1875, '개국': 1392, '건양': 1896, '광무': 1897, '융희': 1907, '메이지': 1868, '다이쇼': 1912, '쇼와': 1926}
# 조선 왕대: 1년의 서기(실록 · 연표의 관례)
KINGS = {'태조': 1392, '정종': 1399, '태종': 1401, '세종': 1419, '문종': 1451, '단종': 1453, '세조': 1455, '예종': 1469, '성종': 1470, '연산군': 1495,
         '중종': 1506, '인종': 1545, '명종': 1546, '선조': 1568, '광해군': 1609, '인조': 1623, '효종': 1650, '현종': 1660, '숙종': 1675, '경종': 1721,
         '영조': 1725, '정조': 1777, '순조': 1801, '헌종': 1835, '철종': 1850, '고종': 1864, '순종': 1907}
_CD = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
_GZ = '[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
_KGZ = '[갑을병정무기경신임계][자축인묘진사오미신유술해]'


def ganzhi(y, korean=False):
    """서기 → 그해 간지(예: 1808 → 戊辰 / 무진)"""
    return (KSTEMS if korean else STEMS)[(y - 4) % 10] + (KBRANCHES if korean else BRANCHES)[(y - 4) % 12]


def han_num(t):
    """한자 수 → 정수: 元 · 正 = 1, 二十八, 卄八, 一百十九 …(못 읽으면 None)"""
    t = t.replace('廿', '二十').replace('卄', '二十').replace('卅', '三十')
    if t in ('元', '正'): return 1
    n = 0
    for unit, v in (('百', 100), ('十', 10)):
        if unit in t:
            a, _, t = t.partition(unit); n += (_CD.get(a, 1) if a else 1) * v
    if t: n += _CD.get(t, -10 ** 6) if len(t) == 1 else -10 ** 6
    return n if n > 0 else None


def date_mentions(text):
    """글 속 날짜 표현 → [(원문 조각, 서기, 함께 적힌 간지 또는 '')]"""
    out = []
    era = '|'.join(sorted(ERAS, key=len, reverse=True)); king = '|'.join(sorted(KINGS, key=len, reverse=True))
    for m in re.finditer(rf'({era})\s*(?:紀元後|기원후)?\s*([元正一二三四五六七八九十百廿卄卅]{{1,6}})\s*年\s*(?:歲次\s*)?({_GZ})?', text):
        n = han_num(m.group(2))
        if n: out.append((m.group(0), ERAS[m.group(1)] + n - 1, m.group(3) or ''))
    for m in re.finditer(rf'(?<![가-힣])({era}|{king})\s*(?:기원후\s*)?(\d{{1,3}})(?:\s*년)?(?:\s*(?:세차\s*)?({_KGZ}|{_GZ})(?:년)?)?', text):
        base = ERAS.get(m.group(1)) or KINGS.get(m.group(1))
        out.append((m.group(0), base + int(m.group(2)) - 1, m.group(3) or ''))
    return out


def date_issues(row):
    """한 문서의 날짜가 서로 맞는지 → [(칸, 무엇이 어긋나는지)]
    ① 연호 · 왕대 N년과 바로 붙은 간지 ② 「1808년(순조 8, 戊辰)」처럼 서기 뒤 괄호 속 왕대 · 연호 · 간지
    ③ 「순치 12년 을미(1655)」처럼 날짜 뒤 괄호 속 서기 ④ 연도 칸이 문서 속 어느 날짜와도 맞지 않음(경고)"""
    out, years, spans = [], set(), []
    for f in ('원문', '판독', '번역', '해제', '요약', '캡션', '이야기'):
        t = row.get(f) or ''
        for frag, y, g in date_mentions(t):
            years.add(y)
            if g and g not in (ganzhi(y), ganzhi(y, True)): out.append((f, f'「{frag}」 — {y}년의 간지는 {ganzhi(y)}({ganzhi(y, True)})'))
        for m in re.finditer(rf'(\S{{1,4}}\s*\d{{1,3}}년?\s*(?:{_KGZ}|{_GZ})?(?:년)?)\s*\((\d{{4}})\)', t):
            for frag, y, _ in date_mentions(m.group(1)):
                if y != int(m.group(2)): out.append((f, f'「{m.group(0)}」 — {frag.strip()} = {y}년'))
        for m in re.finditer(r'(\d{4})년\s*\(([^)]{1,40})\)', t):
            yy = int(m.group(1)); years.add(yy)
            for frag, y, _ in date_mentions(m.group(2)):
                if y != yy: out.append((f, f'「{m.group(0)}」 — {frag.strip()} = {y}년'))
            for g in re.findall(rf'(?<![가-힣])({_KGZ}|{_GZ})(?![가-힣])', m.group(2)):
                if g not in (ganzhi(yy), ganzhi(yy, True)): out.append((f, f'「{m.group(0)}」 — {yy}년의 간지는 {ganzhi(yy)}({ganzhi(yy, True)})'))
        years.update(int(x) for x in re.findall(r'(?<!\d)(1[3-9]\d\d)(?=년|\))', t))
        spans += [(int(x), int(z)) for x, z in re.findall(r'(?<!\d)(1[3-9]\d\d)\s*[~〜–-]\s*(1[3-9]\d\d)(?!\d)', t)]  # 「1955~1962년 사이」
    y0 = str(row.get('연도') or '').strip()
    if y0.isdigit() and years and not any(abs(int(y0) - y) <= 1 for y in years) and not any(lo <= int(y0) <= hi for lo, hi in spans):
        out.append(('연도', f'연도 칸 {y0}이 문서 속 날짜({", ".join(str(y) for y in sorted(years)[:4])})와 다릅니다'))
    return list(dict.fromkeys(out))


def id_year(row):
    """자료ID의 연대(자료관이 매긴 것, 예: …KSM-XA.1607.1111-… → 1607). 0000 · 9999는 미상 → None"""
    m = re.search(r'KSM-\w+\.(\d{4})\.', row.get('자료ID') or '')
    return int(m.group(1)) if m and m.group(1) not in ('0000', '9999') else None


def year_suggest(row):
    """빈 연도 칸에 넣을 값과 근거 → (연도, 근거) 또는 (None, 왜 못 정했는지)
    ① 원문 · 번역 속 날짜(연호 · 왕대 · 간지)가 한 해로 모이면 ② 해제 첫머리의 서기(「1808년(…)」 · 「…년(1849년으로 보임)」) ③ 자료ID의 연대 — 앞의 근거와 어긋나지 않을 때만.
    날짜가 서로 어긋나는 문서(date_issues)는 제안하지 않음"""
    if date_issues(row): return None, '날짜 어긋남 — 원본 확인'
    a = sorted({y for k in ('원문', '판독', '번역') for _, y, _ in date_mentions(row.get(k) or '')})
    hj = (row.get('해제') or '').strip()
    m = re.match(r'(1[3-9]\d\d)년', hj) or re.search(r'\((1[3-9]\d\d)년으로 보임\)', hj[:40])  # 「1808년(순조 8) …」 · 「기유년(1849년으로 보임) …」
    b = int(m.group(1)) if m else None
    c = id_year(row)
    if len(a) == 1: return a[0], '문서 속 날짜'
    if b and (not a or any(abs(b - y) <= 1 for y in a)): return b, '해제'
    if c and (not a or any(abs(c - y) <= 1 for y in a)) and not (b and abs(b - c) > 1):
        return c, '자료ID(자료관 연대)'
    if len(a) > 1: return None, '문서 속 날짜가 여럿(' + ', '.join(map(str, a[:4])) + ')'
    return None, '근거 없음'


def cmd_years(a):
    """연도 칸 점검 — 빈 칸에는 근거와 함께 제안, 채운 칸은 자료관 연대와 비교. --apply면 제안을 채움"""
    ed = os.path.join(a.work, 'edit', a.theme); p = os.path.join(ed, 'selection.csv')
    if not os.path.exists(p): sys.exit(f'{p}이(가) 없습니다. 먼저 studio.py edit 를 실행하세요.')
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig'))); cols = list(rows[0].keys()) if rows else []
    if '연도근거' not in cols: cols.append('연도근거')
    filled = 0
    print(f'■ 연도 점검: {a.work}/{a.theme} — 문서 {len(rows)}건')
    for r in rows:
        n = r.get('순서') or '?'; name = (r.get('문서명') or '')[:26]; y = str(r.get('연도') or '').strip()
        if y.isdigit():
            c = id_year(r); di = date_issues(r)
            note = []
            if c and abs(c - int(y)) > 1: note.append(f'자료관 연대 {c}와 다름(문서 속 날짜를 따랐다면 그대로 두어도 됩니다)')
            if di: note.append('날짜 어긋남 ' + ' / '.join(m for _, m in di[:2]))
            print(f'  {n:>2}. {y} {name}' + (' — ' + ' · '.join(note) if note else ' ✓'))
            continue
        v, why = year_suggest(r)
        if v:
            print(f'  {n:>2}. (빈 칸) {name} → {v} · 근거: {why}' + (' — 채움' if a.apply else ''))
            if a.apply: r['연도'] = str(v); r['연도근거'] = why; filled += 1
        else: print(f'  {n:>2}. (빈 칸) {name} — 그대로 둠: {why}')
    if a.apply and filled:
        with open(p, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows([{k: r.get(k, '') for k in cols} for r in rows])
        print(f'\n{filled}건 채움(selection.csv 「연도」, 근거는 「연도근거」) → mediate · series를 다시 실행하세요')
    elif not a.apply: print('\n제안을 채우려면 --apply (근거가 「자료ID」인 값은 자료관이 매긴 연대 — 원문에 날짜가 보이면 그쪽을 따르세요)')


def cmd_audit(a):
    """여러 편을 한꺼번에 점검 — 폴더 아래 모든 selection.csv(작업 폴더 edit/*/ 또는 예시 사이트 편 폴더)를 표 하나로"""
    files = sorted({f for root in a.in_ for f in ([root] if root.endswith('.csv') else glob.glob(os.path.join(root, '**', 'selection.csv'), recursive=True))
                    if '/mediate/' not in f.replace(os.sep, '/') and '/eps/' not in f.replace(os.sep, '/')
                    and not any(x in f.replace(os.sep, '/') for x in (a.exclude or []))})  # 결과물 쪽 사본은 빼고 원본 선별표만
    if not files: sys.exit('selection.csv를 찾지 못했습니다(--in 폴더 확인).')
    cols = ['편', '문서', '빈 칸', '□·(?)', '날짜', '인용', '연도 빈 칸', '검토']
    rows, tot = [], Counter()
    for f in files:
        sel = list(csv.DictReader(open(f, encoding='utf-8-sig')))
        name = os.path.relpath(os.path.dirname(f), a.in_[0] if os.path.isdir(a.in_[0]) else '.').replace(os.sep, '/')
        c = Counter(docs=len(sel))
        for s in sel:
            c['empty'] += sum(1 for k in ('판독', '번역', '해제', '요약', '이야기') if not (s.get(k) or '').strip())
            c['unk'] += (s.get('판독') or '').count('□') + (s.get('판독') or '').count('(?)')
            noted = '어긋' in ''.join(s.get(k) or '' for k in ('원문', '번역', '해제'))
            c['date'] += 0 if noted else len(date_issues(s))
            c['quote'] += len(quote_issues(s))
            c['noyear'] += 0 if str(s.get('연도') or '').strip().isdigit() else 1
            c['rev'] += 1 if (s.get('검토') or '').strip() else 0
        tot.update(c)
        rows.append([name, c['docs'], c['empty'], c['unk'], c['date'], c['quote'], c['noyear'], f"{c['rev']}/{c['docs']}"])
    rows.sort(key=lambda r: (-(r[4] + r[5]), -r[2], r[0]))  # 고칠 것이 많은 편 먼저
    w = [max(len(str(x)) for x in col) for col in zip(cols, *rows)]
    line = lambda r: '  ' + ' | '.join(str(x).ljust(n) for x, n in zip(r, w))
    print(f'■ 점검: 편 {len(rows)}개 · 문서 {tot["docs"]}건\n' + line(cols) + '\n  ' + '-+-'.join('-' * n for n in w))
    for r in rows[: a.top or len(rows)]: print(line(r))
    if a.top and len(rows) > a.top: print(f'  … 외 {len(rows) - a.top}편')
    print(f'\n합계 — 빈 칸 {tot["empty"]} · □·(?) {tot["unk"]} · 날짜 어긋남 {tot["date"]} · 인용 불일치 {tot["quote"]} · 연도 빈 칸 {tot["noyear"]} · 검토 {tot["rev"]}/{tot["docs"]}')
    if tot['date'] or tot['quote']: print('→ 날짜 · 인용은 편마다 studio.py check 로 자세히(어느 문서 · 어느 칸)')
    if tot['noyear']: print('→ 연도 빈 칸: studio.py years (근거와 함께 제안)')
    if a.csv:
        with open(a.csv, 'w', newline='', encoding='utf-8-sig') as fh:
            wr = csv.writer(fh); wr.writerow(cols); wr.writerows(rows)
        print(f'표 → {a.csv}')
    keys = {'empty': '빈 칸', 'date': '날짜 어긋남', 'quote': '인용 불일치', 'year': '연도 빈 칸', 'unk': '□·(?)'}
    fail = [k for k in ((a.fail_on or '').split(',') if a.fail_on else (['empty', 'date', 'quote'] if a.strict else [])) if k.strip()]
    bad = [keys.get(k.strip(), k) for k in fail if tot['noyear' if k.strip() == 'year' else k.strip()]]
    if bad: print('실패: ' + ' · '.join(bad)); sys.exit(1)


def cmd_check(a):
    """공개 전 점검 — 칸이 비었거나 결과물이 원본보다 오래된 곳을 찾아 다음 할 일을 알려 준다."""
    ed = os.path.join(a.work, 'edit', a.theme); md = os.path.join(a.work, 'mediate', a.theme)
    sp_ = os.path.join(ed, 'selection.csv')
    if not os.path.exists(sp_): sys.exit(f'{sp_}이(가) 없습니다. 먼저 studio.py edit 를 실행하세요.')
    sel = list(csv.DictReader(open(sp_, encoding='utf-8-sig')))
    todo = []
    print(f'■ 점검: {a.work}/{a.theme} — 문서 {len(sel)}건')
    print('\n[문구 에디팅]')
    for s in sel:
        n = s.get('순서') or '?'; name = (s.get('문서명') or '')[:28]
        miss = [k for k in ('판독', '번역', '해제', '요약', '이야기') if not (s.get(k) or '').strip()]
        story = s.get('이야기') or ''
        q = len(find_quotes(story)); unk = (s.get('판독') or '').count('□'); unsure = (s.get('판독') or '').count('(?)')
        img = os.path.join(ed, s.get('이미지') or '')
        orig = os.path.join(a.work, s.get('원본경로') or '')
        sib = sorted(glob.glob(os.path.join(os.path.dirname(orig), '*.jpg'))) if s.get('원본경로') else []
        dark = (bool(s.get('이미지')) and os.path.exists(img) and is_cover(img)) or (orig in thin_pages(sib[:8]))
        marks = []
        if miss: marks.append('빈 칸: ' + '·'.join(miss))
        if story and not q: marks.append('이야기에 "현대어(原文)" 인용 없음')
        if unk or unsure: marks.append(f'판독 □ {unk} · (?) {unsure}')
        if not s.get('검토'): marks.append('검토 칸 비어 있음 → "초안" 표시')
        if dark: marks.append('대표 면이 표지·겉면 같습니다(어둡거나 다른 면보다 작고 글씨가 적음) → studio.py page')
        di = date_issues(s)
        qi = quote_issues(s)
        if qi: marks.append('인용 원문 불일치 ' + str(len(qi)) + ': ' + qi[0][1][:60])
        if not str(s.get('연도') or '').strip().isdigit():
            ys_, why_ = year_suggest(s)
            marks.append(f'연도 빈 칸 → 제안 {ys_}({why_}) · studio.py years' if ys_ else f'연도 빈 칸({why_})')
        if di: marks.append('날짜 어긋남 ' + str(len(di)) + ': ' + ' / '.join(f'{f} {m}' for f, m in di[:2]) + (' (문서에 이미 적어 둠)' if '어긋' in ''.join(s.get(k) or '' for k in ('원문', '번역', '해제')) else ''))
        print(f'  {n:>2}. {name} — ' + ('✓' if not marks else ' / '.join(marks)))
        if miss or (story and not q): todo.append(f'{n}번 문서의 문구 에디팅(판독·번역·해제·요약·이야기)')
        if dark: todo.append(f'{n}번 대표 면 확인: studio.py page --work {a.work} --theme {a.theme} --n {n} --page 002.jpg')
        if qi: todo.append(f'{n}번 이야기 인용 — 원문 · 판독과 글자 그대로 맞추기(건너뛴 곳은 「…」)')
        noted = '어긋' in ''.join(s.get(k) or '' for k in ('원문', '번역', '해제'))  # 원문 자체가 어긋나 이미 적어 둔 경우
        if di and not noted: todo.append(f'{n}번 날짜 확인 — 연호 · 왕대 · 간지 · 서기가 서로 맞는지 원본과 대조(간지는 60년마다 돌아옵니다)')
    print('\n[큐레이터 노트]')
    c = read_curator(ed)
    if not os.path.exists(os.path.join(ed, 'curator.md')): print('  curator.md 없음'); todo.append('curator.md 쓰기(edit가 틀을 만듭니다)')
    else:
        empty = [h for k, h, _ in CURATOR_KEYS if not c.get(k)]
        print('  ' + ('✓ 6칸 모두 채움' if not empty else '빈 칸: ' + ' · '.join(empty)))
        if 'message' in [k for k, h, _ in CURATOR_KEYS if not c.get(k)]: todo.append('큐레이터 노트 「전하고 싶은 것」 — 비하인드 카드·영상·홍보 글에 쓰입니다')
    print('\n[전달 에디팅]')
    dv = read_delivery(ed)
    if not dv: print('  delivery.md 없음'); todo.append(f'studio.py delivery --work {a.work} --theme {a.theme}')
    else:
        empty = [h for k, h, _ in DELIVERY_KEYS if not dv.get(k)]
        print('  ' + ('✓ 11칸 모두 채움' if not empty else '빈 칸: ' + ' · '.join(empty)))
        if not dv.get('climax') and any(find_quotes(s.get('이야기')) for s in sel):
            todo.append(f'절정이 비었습니다 → studio.py delivery --work {a.work} --theme {a.theme} (문구 에디팅 뒤 다시 쓰기)')
        for k in ('emotion', 'linger', 'afterd'):
            if not dv.get(k): todo.append(f'전달 에디팅 「{dict((k2, h) for k2, h, _ in DELIVERY_KEYS)[k]}」 — 사람이 정할 칸')
    nfix = len(read_corrections(ed))
    if nfix: print(f'\n[함께 고친 곳] {nfix}건 (corrections.csv · 전시 웹페이지 「함께 고친 곳」)')
    print('\n[결과물]')
    src_t = max([os.path.getmtime(os.path.join(ed, f)) for f in ('selection.csv', 'curator.md', 'delivery.md', 'theme.json', 'corrections.csv') if os.path.exists(os.path.join(ed, f))])
    def st(path, label, cmd):
        if not os.path.exists(path): print(f'  {label}: 없음'); todo.append(cmd); return
        old = os.path.getmtime(path) < src_t
        print(f'  {label}: ' + ('있음 — 하지만 노트·CSV보다 오래됨' if old else '✓'))
        if old: todo.append(cmd + '  (다시 실행해 최신 내용 반영)')
    st(os.path.join(md, 'promo.md'), '홍보 글 promo.md', f'studio.py promo --work {a.work} --theme {a.theme} --ep N --url <전시 주소>')
    st(os.path.join(md, 'exhibit.html'), '전시·카드·활동지 (mediate)', f'studio.py mediate --work {a.work} --theme {a.theme} --url <전시 주소>')
    vids = glob.glob(os.path.join(md, 'video', '*_reel.mp4')) + glob.glob(os.path.join(md, 'video', '*_wide.mp4'))
    if vids: st(max(vids, key=os.path.getmtime), '영상 (video.py)', f'video.py --work {a.work} --theme {a.theme} --ep N --url <전시 주소> --web')
    else: print('  영상 (video.py): 없음 (선택)')
    ix = os.path.join(md, 'index.html')
    if vids and os.path.exists(ix) and max(os.path.getmtime(v) for v in vids) > os.path.getmtime(ix):
        todo.append(f'영상을 mediate 뒤에 만들었습니다 → studio.py mediate --work {a.work} --theme {a.theme} 다시(첫 페이지 영상 칸)')
    if os.path.exists(os.path.join(md, 'exhibit.html')) and os.path.exists(os.path.join(md, 'promo.md')) and os.path.getmtime(os.path.join(md, 'promo.md')) > os.path.getmtime(os.path.join(md, 'index.html') if os.path.exists(os.path.join(md, 'index.html')) else os.path.join(md, 'exhibit.html')):
        todo.append('promo.md가 mediate 뒤에 바뀌었습니다 → mediate 다시(첫 페이지 「홍보 글」 타일)')
    drafts = sum(1 for s in sel if not s.get('검토'))
    note = f" 다만 {drafts}건은 '초안' 표시가 남습니다 — studio.py proof 로 검토지를 뽑아 대조한 뒤 studio.py review --n 번호 --by 이름." if drafts else ''
    print('\n[다음 할 일]' if todo else f'\n✓ 공개 준비 완료 — 이미지 공개 전 소장처 동의(자료관 031-730-8873, 8876)를 확인하세요.{note}')
    for i, t in enumerate(dict.fromkeys(todo), 1): print(f'  {i}. {t}')
    if a.strict and todo: sys.exit(1)


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
    page = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>소장처 비교 리포트</title><style>body{{font-family:sans-serif;max-width:860px;margin:40px auto;color:#222}} h1{{margin-bottom:4px}} .n{{color:#777}}</style></head><body>
<h1>소장처 비교 리포트</h1><p class="n">한국고문서자료관 · 소장처 {len(cols)}곳 · 문서 {len(rows)}건 · 연도·유형은 문서명에서 자동 추출한 초안</p><p>{legend}</p>
{bars(types, '문서유형', f'문서 유형 상위 {len(types)}')}{bars(cents, '세기', '세기별 분포')}</body></html>"""
    out = os.path.join(a.root, 'compare_report.html'); open(out, 'w', encoding='utf-8').write(page); print('→', out)

# ---------------------------------------------------------------- zoom (판독용 확대 조각)
def cmd_zoom(a):
    """대표 이미지의 원본(최대 해상도)을 겹치게 잘라 판독용 조각을 만든다. 세로쓰기라 오른쪽 위 조각이 c1."""
    ed = os.path.join(a.work, 'edit', a.theme)
    sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
    od = os.path.join(ed, 'zoom'); os.makedirs(od, exist_ok=True)
    only = {int(x) for x in a.only.split(',')} if a.only else None
    for s in sel:
        n = int(s['순서'])
        if only and n not in only: continue
        src = os.path.join(a.work, s['원본경로']) if s.get('원본경로') and os.path.exists(os.path.join(a.work, s['원본경로'])) else os.path.join(ed, s['이미지'])
        pages = sorted(glob.glob(os.path.join(os.path.dirname(src), '*.jpg'))) if a.all_pages else [src]
        for pi, src in enumerate(pages, 1):
            zoom_one(a, od, n, s, src, pi if a.all_pages else 0)
    print('→', od, '(c1이 오른쪽 — 세로쓰기는 c1 → c2 … 순서로 읽기)')

def zoom_one(a, od, n, s, src, pi):
        im = Image.open(src).convert('RGB'); W, H = im.size
        cols = a.cols or max(1, round(W / a.tile)); rows = a.rows or max(1, round(H / a.tile))
        tw, th = W / cols, H / rows; ov = a.overlap
        made = []
        for r in range(rows):
            for c in range(cols):
                x1 = W - (c + 1) * tw; y0 = r * th          # 오른쪽부터
                box = (int(max(0, x1 - ov * tw)), int(max(0, y0 - ov * th)), int(min(W, x1 + tw + ov * tw)), int(min(H, y0 + th + ov * th)))
                t = im.crop(box); t.thumbnail((a.max, a.max))
                fn = f"{n:02d}{f'_p{pi}' if pi else ''}_r{r+1}c{c+1}.jpg"; t.save(os.path.join(od, fn), quality=90); made.append(fn)
        print(f"{n:02d}{f' p{pi}' if pi else ''} {s['문서명'][:30]} ({W}×{H}) → {len(made)}조각: {', '.join(made)}")

# ---------------------------------------------------------------- promo (릴스 홍보 문구)
PROMO_TEMPLATE = """📜 {series} EP.{ep} 〈{title}〉

{hook}

{body}

{note}{follow} 이 기록을 바탕으로 Claude 플러그인 aks-archive-harvester로 전시 웹페이지, 카드뉴스, 수업 활동지, SNS 게시글을 만들었습니다.
※ 설명은 문서명과 이미지를 바탕으로 만든 초안입니다. 정확한 판독은 원문 확인이 필요합니다.

{question} 댓글로 남겨주세요.

▶ {label}
{url}

▶ GitHub · 설치 안내 · 무료 오픈소스(MIT)
https://github.com/changgi/archive-tools

이미지 소장·제공 · 한국학중앙연구원 한국고문서자료관 · {collection}

{tags}"""

def cmd_promo(a):
    ed = os.path.join(a.work, 'edit', a.theme)
    sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
    th = json.load(open(os.path.join(ed, 'theme.json'), encoding='utf-8'))
    coll = a.collection or (json.load(open(os.path.join(a.work, 'collection.json'), encoding='utf-8'))['name'] if os.path.exists(os.path.join(a.work, 'collection.json')) else os.path.basename(os.path.abspath(a.work)))
    title = a.title or th['title']
    ys = sorted(int(s['연도']) for s in sel if s['연도'])
    people = list(dict.fromkeys(p for s in sel for p in persons(s)))[:4]
    kinds = list(dict.fromkeys(s['문서유형'] for s in sel))[:4]
    tags = ['#' + a.series.replace(' ', '')] + ['#' + t.replace(' ', '') for t in (people + [coll.split()[-1]] + kinds)] + ['#고문서', '#한국고문서자료관', '#디지털인문학', '#Claude', '#오픈소스']
    first, last = (sel[0], sel[-1]) if sel else ({}, {})
    fill = dict(series=a.series, ep=f'{a.ep:02d}', title=title, collection=coll, url=a.url or '[전시 웹페이지 주소]',
                hook='[이모지 1개 + 궁금증을 여는 질문 한 문장]',
                body=f"[{coll}에 무엇이 남아 있는지 → 문서를 시간 순서로 2~4문장 ({ys[0] if ys else '?'}–{ys[-1] if ys else '?'}). 문서명·이미지·판독에서 확인한 사실만]",
                follow='[이번 릴스에서는 ○○을 따라가 봅니다.]',
                question=f"[여러분이라면 {(first.get('연도') + '년 ') if first.get('연도') else ''}{first.get('문서유형','A')}와 {(last.get('연도') + '년 ') if last.get('연도') else ''}{last.get('문서유형','B')} 중 어느 쪽을 먼저 펼쳐보고 싶으세요?]",
                label=f'[{title} 온라인 전시 보기]', tags=' '.join(dict.fromkeys(tags)),
                note=(f"✍️ 큐레이터 노트 — {read_curator(ed)['message']}\n\n" if read_curator(ed).get('message') else ''))
    out = os.path.join(a.work, 'mediate', a.theme); os.makedirs(out, exist_ok=True)
    txt = PROMO_TEMPLATE.format(**fill)
    open(os.path.join(out, 'promo.md'), 'w', encoding='utf-8').write(
        f"# 릴스 홍보 문구 — {title}\n\n[대괄호] 칸을 selection.csv의 이야기·해제·요약에 근거해 채우세요. 나머지 줄은 그대로 둡니다.\n\n```\n{txt}\n```\n")
    print(txt); print('→', os.path.join(out, 'promo.md'))


# ── 기록 꾸러미(record) ─ 편마다 맥락 · 출처 · 파생물 · 고정값 · 검증 · 검토 · 작업 이력을 한 파일로 ──
REC_ROLE = [(r'^selection\.csv$', '판독번역표', 'data', 'text/csv'), (r'^README\.md$', '편 설명(판독 · 번역 · 해제 전문)', 'text', 'text/markdown'),
            (r'^exhibit\.html$', '온라인 전시', 'exhibit', 'text/html'), (r'^handout\.html$', '수업 활동지', 'education', 'text/html'),
            (r'^proof\.html$', '검토지(원본 대조용)', 'review', 'text/html'), (r'^index\.html$', '편 안내 페이지', 'web', 'text/html'),
            (r'^cards/.*\.(png|jpe?g)$', '카드뉴스', 'card', 'image/jpeg'), (r'^behind/.*\.(png|jpe?g)$', '비하인드 카드', 'card', 'image/jpeg'),
            (r'^images/.*\.(png|jpe?g)$', '선별 이미지(웹용)', 'image', 'image/jpeg'), (r'^curator\.md$', '큐레이터 노트', 'note', 'text/markdown'),
            (r'^delivery\.md$', '전달 에디팅', 'note', 'text/markdown'), (r'^promo\.md$', '홍보 글', 'promotion', 'text/markdown'),
            (r'^channels\.md$', '채널별 홍보안', 'promotion', 'text/markdown'), (r'^sns\.txt$', 'SNS 글', 'promotion', 'text/plain'),
            (r'^corrections\.csv$', '판독 고침 이력', 'audit-trail', 'text/csv'), (r'^theme\.json$', '테마 정보', 'data', 'application/json'),
            (r'_reel\.mp4$', '릴스 영상(9:16)', 'video', 'video/mp4'), (r'_wide\.mp4$', '가로 영상(16:9)', 'video', 'video/mp4'),
            (r'\.srt$', '자막(SRT)', 'caption', 'application/x-subrip'), (r'\.vtt$', '자막(WebVTT)', 'caption', 'text/vtt'),
            (r'-poster\.jpe?g$', '영상 포스터', 'image', 'image/jpeg')]
REC_SKIP = ('record.json', 'checksums.sha256')


def _sha256(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def _rec_files(d, media=None):
    """편 폴더의 파일 + (--media가 있으면) 그 편 이름이 붙은 영상 · 자막 · 포스터 → [(기록 속 경로, 실제 경로)]"""
    out = []
    for root, _, fs in os.walk(d):
        for f in fs:
            full = os.path.join(root, f); rel = os.path.relpath(full, d).replace(os.sep, '/')
            if rel in REC_SKIP or '/__pycache__/' in '/' + rel or f.startswith('.'): continue
            out.append((rel, full))
    rx = re.compile(r'^ep\d+-' + re.escape(os.path.basename(os.path.normpath(d))) + r'[._]')
    if media and os.path.isdir(media):
        for f in sorted(os.listdir(media)):
            if rx.match(f): out.append((os.path.relpath(os.path.join(media, f), d).replace(os.sep, '/'), os.path.join(media, f)))
    for rdir, url in REC_REMOTE:  # 다른 저장소로 옮긴 파일(예: 영상) — 기록 속 경로는 공개 주소
        if os.path.isdir(rdir):
            for f in sorted(os.listdir(rdir)):
                if rx.match(f): out.append((url.rstrip('/') + '/' + f, os.path.join(rdir, f)))
    return sorted(out)

REC_REMOTE = []  # [(폴더, 공개 주소)] — record --media-remote


def _rec_role(rel):
    b = rel.split('/')[-1]
    for rx, lab, kind, mime in REC_ROLE:
        if re.search(rx, rel) or re.search(rx, b): return lab, kind, mime
    return '기타', 'other', 'application/octet-stream'


def _plugin_version():
    try: return jload(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.claude-plugin', 'plugin.json')).get('version', '')
    except Exception: return ''


def build_record(d, media=None, meta=None, agent=None, creator=None, license_text=None, rights_images=None, today=None):
    """편 폴더 하나의 기록 꾸러미 → (record dict, checksums 줄 목록). 이전 record.json이 있으면 작성일과 작업 이력을 이어받는다."""
    import datetime
    today = today or datetime.date.today().isoformat()
    meta = meta or {}
    sel = list(csv.DictReader(open(os.path.join(d, 'selection.csv'), encoding='utf-8-sig')))
    old = jload(os.path.join(d, 'record.json')) if os.path.exists(os.path.join(d, 'record.json')) else {}
    title = meta.get('title') or ''
    if not title and os.path.exists(os.path.join(d, 'theme.json')): title = (jload(os.path.join(d, 'theme.json')) or {}).get('title', '')
    if not title and os.path.exists(os.path.join(d, 'exhibit.html')):
        m = re.search(r'<title>([^<]*)', open(os.path.join(d, 'exhibit.html'), encoding='utf-8').read()); title = html.unescape(m.group(1)).strip() if m else ''
    files = _rec_files(d, media)
    derivs, sums = [], []
    for rel, full in files:
        h = _sha256(full); lab, kind, mime = _rec_role(rel)
        derivs.append(dict(path=rel, role=lab, kind=kind, format=mime, bytes=os.path.getsize(full), sha256=h)); sums.append(f'{h}  {rel}')
    docs, val, tot = [], [], Counter()
    for s in sel:
        di, qi = date_issues(s), quote_issues(s)
        noted = '어긋' in ''.join(s.get(k) or '' for k in ('원문', '번역', '해제'))
        unk = (s.get('판독') or '').count('□') + (s.get('판독') or '').count('(?)')
        rv = (s.get('검토') or '').strip()
        tot.update(docs=1, unk=unk, date=0 if noted else len(di), noted=1 if (noted and di) else 0, quote=len(qi), reviewed=1 if rv else 0,
                   quotes=len(find_quotes(s.get('이야기'))), noyear=0 if str(s.get('연도') or '').strip().isdigit() else 1)
        docs.append({k: v for k, v in dict(order=s.get('순서'), identifier=s.get('자료ID'), title=s.get('문서명'), date=s.get('연도'),
                                           date_basis=s.get('연도근거') or ('자료관 목록' if s.get('연도') else ''), type=s.get('문서유형'),
                                           persons=s.get('인물'), page=s.get('대표장'), source_url=s.get('뷰어링크'),
                                           review=rv or '미검토').items() if v})
        for f_, why in di: val.append(dict(doc=s.get('순서'), field=f_, issue=why, acknowledged=noted))
        for q, why in qi: val.append(dict(doc=s.get('순서'), quote=q, issue=why))
    ver = _plugin_version()
    rec = {'schema': 'aks-record/1.0',
           'identifier': meta.get('identifier') or os.path.basename(os.path.normpath(d)),
           'title': title, 'episode': meta.get('episode'), 'language': 'ko',
           'context': {k: v for k, v in dict(series=meta.get('series'), collection=meta.get('collection'), holder=meta.get('holder'),
                                             source_archive=meta.get('source_archive', '한국학중앙연구원 한국고문서자료관 (archive.aks.ac.kr)'),
                                             purpose=meta.get('purpose'), process=['수집', '선별', '판독 · 번역 · 해제', '문구 에디팅', '전달 에디팅', '산출물', '검증', '사람 검토']).items() if v},
           'agents': [x for x in [dict(name=creator, role='기획 · 책임 편집', type='person') if creator else None,
                                  dict(name=agent, role='판독 · 번역 · 해제 초안, 편집 보조', type='software') if agent else None,
                                  dict(name=f'aks-archive-harvester {ver}'.strip(), role='수집 · 산출물 생성 · 검증 도구', type='software')] if x],
           'sources': docs,
           'derivatives': derivs,
           'validation': {'tool': f'studio.py record (aks-archive-harvester {ver})'.strip(), 'documents': tot['docs'], 'quotes': tot['quotes'],
                          'uncertain_marks': tot['unk'], 'date_issues': tot['date'], 'date_issues_acknowledged': tot['noted'], 'quote_issues': tot['quote'],
                          'undated': tot['noyear'], 'details': val},
           'review': {'reviewed': tot['reviewed'], 'total': tot['docs'],
                      'status': '검토 완료' if tot['docs'] and tot['reviewed'] == tot['docs'] else ('일부 검토' if tot['reviewed'] else '미검토 (판독 · 번역은 초안)'),
                      'rule': '원본과 대조한 사람만 검토 칸을 채운다 — 도구와 AI는 검토를 표시하지 않는다'},
           'rights': {k: v for k, v in dict(images=rights_images, text=license_text).items() if v},
           'relations': {k: v for k, v in dict(is_part_of=meta.get('series'), previous=meta.get('previous'), next=meta.get('next'),
                                               derived_from=sorted({x['source_url'] for x in docs if x.get('source_url')})).items() if v}}
    rec = {k: v for k, v in rec.items() if v not in (None, '', {}, [])}
    # 작업 이력(PREMIS 사건처럼): 무엇이 바뀌었을 때만 한 줄씩 쌓는다 — 다시 돌려도 같은 내용이면 이력이 늘지 않는다
    ev = list(old.get('events') or [])
    oh = {x['path']: x['sha256'] for x in old.get('derivatives', [])}
    nh = {x['path']: x['sha256'] for x in derivs}
    if not old:
        ev.append(dict(date=today, type='creation', agent=', '.join(a_['name'] for a_ in rec['agents']), detail=f'기록 꾸러미 생성 — 문서 {tot["docs"]}건 · 파생물 {len(derivs)}개'))
    else:
        add = sorted(set(nh) - set(oh)); gone = sorted(set(oh) - set(nh)); chg = sorted(k for k in nh if k in oh and nh[k] != oh[k])
        og = {oh[k]: k for k in gone}; mv = [(og[nh[k]], k) for k in add if nh[k] in og]  # 내용(고정값)이 같은 채 자리만 옮긴 파일
        add = [k for k in add if k not in {b for _, b in mv}]; gone = [k for k in gone if k not in {a for a, _ in mv}]
        if mv:
            ev.append(dict(date=today, type='migration', agent=rec['agents'][-1]['name'],
                           detail=f'파생물 {len(mv)}개를 내용 그대로 옮김(고정값 같음)', moved=[f'{a} → {b}' for a, b in mv][:40]))
        if add or gone or chg:
            ev.append(dict(date=today, type='modification', agent=rec['agents'][-1]['name'],
                           detail=f'파생물 바뀜 {len(chg)} · 새로 {len(add)} · 빠짐 {len(gone)}', changed=(chg + add + gone)[:40]))
        orv = (old.get('review') or {}).get('reviewed', 0)
        if tot['reviewed'] != orv:
            ev.append(dict(date=today, type='review', agent=', '.join(sorted({x['review'] for x in docs if x.get('review') != '미검토'})) or '—',
                           detail=f'검토 {orv} → {tot["reviewed"]}/{tot["docs"]}'))
    ov = old.get('validation') or {}
    if not old or any(ov.get(k) != rec['validation'][k] for k in ('date_issues', 'quote_issues', 'uncertain_marks', 'undated')):
        ev.append(dict(date=today, type='validation', agent=rec['validation']['tool'],
                       detail=f'날짜 어긋남 {tot["date"]} · 인용 불일치 {tot["quote"]} · □·(?) {tot["unk"]} · 연도 빈 칸 {tot["noyear"]}'))
    if old and ev == list(old.get('events') or []):  # 바뀐 것이 없으면 도구 버전도 그대로 — 버전만 올라 기록이 모두 고쳐지지 않게
        oldtool = {a_['name'] for a_ in old.get('agents', []) if a_['name'].startswith('aks-archive-harvester')}
        if oldtool:
            for a_ in rec.get('agents', []):
                if a_['name'].startswith('aks-archive-harvester'): a_['name'] = next(iter(oldtool))
            if (old.get('validation') or {}).get('tool'): rec['validation']['tool'] = old['validation']['tool']
    rec['created'] = old.get('created') or today
    rec['modified'] = today if (not old or ev != list(old.get('events') or [])) else old.get('modified', today)
    rec['events'] = ev
    return rec, sums


def record_dc(rec):
    """기록 꾸러미 → Dublin Core 한 줄(다른 기록관리 · 목록 시스템으로 옮길 때)"""
    ctx = rec.get('context', {})
    return {'dc:identifier': rec['identifier'], 'dc:title': rec.get('title', ''), 'dc:creator': '; '.join(a['name'] for a in rec.get('agents', [])),
            'dc:subject': '; '.join(sorted({x.get('type', '') for x in rec.get('sources', []) if x.get('type')})),
            'dc:description': ctx.get('purpose', ''), 'dc:source': '; '.join(x.get('identifier', '') for x in rec.get('sources', [])),
            'dc:coverage': '; '.join(x.get('date', '') for x in rec.get('sources', []) if x.get('date')),
            'dc:relation': ctx.get('collection', ''), 'dc:rights': ' / '.join(rec.get('rights', {}).values()),
            'dc:date': rec.get('modified', ''), 'dc:language': rec.get('language', 'ko'), 'dc:type': 'Collection; Text; Image; MovingImage',
            'dc:format': '; '.join(sorted({x['format'] for x in rec.get('derivatives', [])})), 'review': rec.get('review', {}).get('status', '')}


def cmd_record(a):
    """편 폴더마다 record.json(맥락 · 출처 · 파생물 · 검증 · 검토 · 이력) + checksums.sha256 — --verify 는 고정값 대조만"""
    import datetime
    dirs = sorted({os.path.dirname(f) for root in a.in_ for f in ([root] if root.endswith('.csv') else glob.glob(os.path.join(root, '**', 'selection.csv'), recursive=True))
                   if not any(x in f.replace(os.sep, '/') for x in (a.exclude or []))})  # 결과물 폴더(mediate · eps · 예시 편)가 기록 대상
    if not dirs: sys.exit('selection.csv가 있는 폴더를 찾지 못했습니다(--in 확인).')
    REC_REMOTE[:] = [(r[0], r[1]) for r in (a.media_remote or [])]
    if a.verify:
        bad = 0; n = 0
        for d in dirs:
            cp = os.path.join(d, 'checksums.sha256')
            if not os.path.exists(cp): print(f'  ✗ {d}: checksums.sha256 없음 — studio.py record 로 만드세요'); bad += 1; continue
            want = dict(reversed(l.rstrip('\n').split('  ', 1)) for l in open(cp, encoding='utf-8') if l.strip())
            have = dict((rel, full) for rel, full in _rec_files(d, a.media))
            miss = sorted(set(want) - set(have)); extra = sorted(set(have) - set(want))
            diff = sorted(r for r in want if r in have and _sha256(have[r]) != want[r]); n += len(want)
            if miss or extra or diff:
                bad += 1; print(f'  ✗ {os.path.relpath(d, a.in_[0]) if os.path.isdir(a.in_[0]) else d}: 바뀜 {len(diff)} · 없어짐 {len(miss)} · 기록 안 된 파일 {len(extra)}  ' + ', '.join((diff + miss + extra)[:5]))
        print(f'■ 고정값 대조: 편 {len(dirs)}개 · 파일 {n}개 · 어긋난 편 {bad}개')
        if bad: print('→ 바뀐 결과물이 기록되지 않았습니다. 확인 뒤 studio.py record 로 다시 기록하세요.'); sys.exit(1)
        return
    metas = jload(a.meta) if a.meta else {}
    today = a.date or datetime.date.today().isoformat()
    recs = []
    for d in dirs:
        key = os.path.basename(os.path.normpath(d))
        rec, sums = build_record(d, a.media, metas.get(key, {}), a.agent, a.creator, a.license, a.rights_images, today)
        with open(os.path.join(d, 'record.json'), 'w', encoding='utf-8') as fh: json.dump(rec, fh, ensure_ascii=False, indent=1); fh.write('\n')
        with open(os.path.join(d, 'checksums.sha256'), 'w', encoding='utf-8', newline='\n') as fh: fh.write('\n'.join(sums) + '\n')
        recs.append(rec)
    if a.index:
        with open(a.index + '.jsonl', 'w', encoding='utf-8') as fh:
            for r in recs: fh.write(json.dumps({k: v for k, v in r.items() if k != 'derivatives'}, ensure_ascii=False) + '\n')
        rows = [record_dc(r) for r in recs]
        with open(a.index + '-dc.csv', 'w', newline='', encoding='utf-8-sig') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    t = Counter()
    for r in recs: t.update(docs=r['review']['total'], rev=r['review']['reviewed'], files=len(r.get('derivatives', [])), bad=r['validation']['date_issues'] + r['validation']['quote_issues'])
    print(f'■ 기록 꾸러미: 편 {len(recs)}개 · 문서 {t["docs"]}건 · 파생물 {t["files"]}개 · 날짜 · 인용 어긋남 {t["bad"]} · 검토 {t["rev"]}/{t["docs"]}'
          + (f'\n  목록 → {a.index}.jsonl · {a.index}-dc.csv' if a.index else ''))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    t = sp.add_parser('themes'); t.add_argument('--work', required=True)
    e = sp.add_parser('edit'); e.add_argument('--work', required=True); e.add_argument('--theme'); e.add_argument('--count', type=int, default=9)
    e.add_argument('--all', action='store_true', help='이미지를 받은 문서 전체에서 선별 (download --match 와 함께)'); e.add_argument('--person'); e.add_argument('--types'); e.add_argument('--years', help='1650-1700'); e.add_argument('--query'); e.add_argument('--title'); e.add_argument('--id')
    m = sp.add_parser('mediate'); m.add_argument('--work', required=True); m.add_argument('--theme', required=True)
    m.add_argument('--title'); m.add_argument('--lead', help='도입 문장'); m.add_argument('--collection'); m.add_argument('--font', help='한글 글꼴 파일 경로')
    m.add_argument('--placeholder', action='store_true', help='원본 이미지 대신 "뷰어에서 보기" 자리 표시 (이미지 이용 동의 전 공개용)')
    m.add_argument('--img-max', type=int, default=1400, help='웹페이지에 넣는 이미지 최대 픽셀')
    m.add_argument('--url', help='공개할 전시 웹페이지 주소(채널별 홍보안에 넣음)')
    m.add_argument('--issues', help='판독 고침 제보 받을 곳(GitHub 저장소 주소 또는 이슈 주소, 또는 설문·메일 주소) — 문서마다 「판독 고침 제보」 링크')
    z = sp.add_parser('zoom', help='판독용 확대 조각 → edit/<테마>/zoom/'); z.add_argument('--work', required=True); z.add_argument('--theme', required=True)
    z.add_argument('--only', help='순서 번호 (예: 2,5)'); z.add_argument('--all-pages', action='store_true', help='대표 면만이 아니라 받은 모든 면'); z.add_argument('--rows', type=int); z.add_argument('--cols', type=int)
    z.add_argument('--tile', type=int, default=1100, help='조각 하나의 원본 픽셀 크기(자동 분할 기준)'); z.add_argument('--overlap', type=float, default=0.08); z.add_argument('--max', type=int, default=1400)
    pr = sp.add_parser('promo', help='릴스 홍보 문구 틀(「고문서 한 장」 형식) → mediate/<테마>/promo.md'); pr.add_argument('--work', required=True); pr.add_argument('--theme', required=True)
    pr.add_argument('--ep', type=int, default=1); pr.add_argument('--series', default='고문서 한 장'); pr.add_argument('--title'); pr.add_argument('--collection'); pr.add_argument('--url', help='전시 웹페이지 주소')
    r = sp.add_parser('report'); r.add_argument('--root', required=True); r.add_argument('--top', type=int, default=12)
    pg = sp.add_parser('page', help='대표 면 바꾸기 (예: 두루마리 겉면 → 002.jpg)'); pg.add_argument('--work', required=True); pg.add_argument('--theme', required=True); pg.add_argument('--n', type=int, required=True); pg.add_argument('--page', required=True)
    dl = sp.add_parser('delivery', help='전달 에디팅 초안 다시 만들기(문구 에디팅 뒤) → edit/<테마>/delivery.md'); dl.add_argument('--work', required=True); dl.add_argument('--theme', required=True)
    dl.add_argument('--key', help='절정으로 쓸 구절(이야기 속 인용 가운데 이 말이 든 것)'); dl.add_argument('--force', action='store_true')
    fx = sp.add_parser('fix', help='판독 고침 반영: selection.csv 한 칸을 고치고 corrections.csv에 이전·이후·근거 기록 (GitHub 제보 읽기 가능)')
    fx.add_argument('--work'); fx.add_argument('--theme'); fx.add_argument('--n', help='문서 순서')
    fx.add_argument('--from', dest='from_', help='원문 대조 편집기에서 내보낸 JSON — 자료ID로 맞춰 여러 칸 · 여러 편을 한꺼번에'); fx.add_argument('--in', dest='in_', nargs='+', help='--from: selection.csv를 찾을 폴더(들)')
    fx.add_argument('--field', help='고칠 칸: ' + ' · '.join(FIELDS)); fx.add_argument('--text', help='새 내용(칸 전체, 또는 --replace-part 와 함께 바꿀 구절)')
    fx.add_argument('--replace-part', help='칸 전체가 아니라 이 구절만 --text 로 바꾸기'); fx.add_argument('--note', help='근거 · 메모')
    fx.add_argument('--issue', type=int, help='GitHub 이슈 번호(「판독 고침 제보」 양식을 읽음)'); fx.add_argument('--repo', help='아이디/저장소')
    fx.add_argument('--apply', action='store_true', help='실제로 반영(없으면 미리 보기)'); fx.add_argument('--list', action='store_true', help='고친 기록 보기')
    cp = sp.add_parser('compare', help='원문 대조 편집기: 원본 사진 옆에 판독을 한 줄씩 짝지어 보고 고침 → edit/<테마>/compare.html (고친 내용은 JSON → fix --from)')
    cp.add_argument('--work'); cp.add_argument('--theme'); cp.add_argument('--example', help='이미 낸 편 폴더(selection.csv · exhibit.html)로 만들기')
    cp.add_argument('--folder-page', help='편 폴더를 열어 쓰는 편집기 한 장(사진을 넣지 않음)을 이 경로에')
    cp.add_argument('--out'); cp.add_argument('--max-px', type=int, default=1400, help='사진 긴 변 최대(기본 1400, 상한 IMG_MAX)')
    pf = sp.add_parser('proof', help='검토지(인쇄용): 사진 옆에 판독 · 번역 · 인용을 놓고 대조 표시 → edit/<테마>/proof.html')
    pf.add_argument('--work', required=True); pf.add_argument('--theme', required=True); pf.add_argument('--all', action='store_true', help='검토 표시된 문서까지 모두'); pf.add_argument('--link', action='store_true', help='사진을 페이지에 넣지 않고 images/를 가리킴(가볍게 · 같은 폴더에서 열기)')
    rv = sp.add_parser('review', help='검토 표시: 원문 대조를 마친 문서의 검토 칸에 이름 · 날짜')
    rv.add_argument('--work'); rv.add_argument('--theme'); rv.add_argument('--n', help='순서 번호(예: 1,3,4)')
    rv.add_argument('--from', dest='from_', help='검토 현황 페이지에서 내려받은 reviews.csv — 자료ID로 맞춰 한꺼번에'); rv.add_argument('--in', dest='in_', nargs='+', help='selection.csv를 찾을 폴더(들) · 파일(기본: --work 또는 지금 폴더)')
    rv.add_argument('--dry-run', action='store_true', help='--from: 어디에 반영될지 보기만')
    rv.add_argument('--by', default='검토자', help='검토한 사람 이름'); rv.add_argument('--undo', action='store_true', help='검토 표시 지우기')
    au = sp.add_parser('audit', help='여러 편 한꺼번에 점검: 빈 칸 · □·(?) · 날짜 어긋남 · 인용 불일치 · 연도 빈 칸 · 검토 진행을 편마다 한 줄로')
    au.add_argument('--in', dest='in_', nargs='+', required=True, help='selection.csv를 찾을 폴더(들)'); au.add_argument('--csv', help='표를 CSV로'); au.add_argument('--exclude', nargs='+', help='경로에 이 말이 든 곳은 빼기(예: tutorial)'); au.add_argument('--top', type=int, default=0, help='고칠 것이 많은 편 N개만')
    au.add_argument('--strict', action='store_true', help='날짜 · 인용 · 빈 칸이 있으면 종료 코드 1')
    au.add_argument('--fail-on', help='이것이 하나라도 있으면 종료 코드 1 — empty,date,quote,year,unk 중 쉼표로(CI용, 예: date,quote)')
    yr = sp.add_parser('years', help='연도 칸 점검: 빈 칸에 근거(문서 속 날짜 · 해제 · 자료ID)와 함께 제안, --apply로 채움'); yr.add_argument('--work', required=True); yr.add_argument('--theme', required=True); yr.add_argument('--apply', action='store_true')
    ck = sp.add_parser('check', help='공개 전 점검: 빈 칸 · 인용 · 대표 면 · 오래된 결과물 → 다음 할 일'); ck.add_argument('--work', required=True); ck.add_argument('--theme', required=True)
    ck.add_argument('--strict', action='store_true', help='할 일이 남아 있으면 종료 코드 1')
    rc = sp.add_parser('record', help='기록 꾸러미: 편마다 record.json(맥락 · 출처 · 파생물 · 검증 · 검토 · 작업 이력) + checksums.sha256(SHA-256 고정값), --verify 로 대조')
    rc.add_argument('--in', dest='in_', nargs='+', required=True, help='selection.csv를 찾을 폴더(들)'); rc.add_argument('--exclude', nargs='+', help='경로에 이 말이 든 곳은 빼기'); rc.add_argument('--media-remote', nargs=2, action='append', metavar=('DIR', 'URL'), help='다른 저장소로 옮긴 영상 폴더와 그 공개 주소(여러 번 가능) — 기록에는 주소로 남고 고정값은 그 폴더 파일로 대조')
    rc.add_argument('--media', help='편 이름이 붙은 영상 · 자막 · 포스터가 든 폴더(예: examples/media)'); rc.add_argument('--meta', help='폴더 이름 → {title, episode, series, collection, holder, purpose, previous, next} JSON')
    rc.add_argument('--agent', help='판독 · 번역 초안을 만든 AI 또는 도구 이름(예: "Claude (Anthropic)")'); rc.add_argument('--creator', help='책임 편집자 이름')
    rc.add_argument('--license', help='텍스트 이용 조건(직접 정한 것만, 예: CC BY 4.0)'); rc.add_argument('--rights-images', help='이미지 이용 조건 문구')
    rc.add_argument('--index', help='모든 편 목록을 PATH.jsonl · PATH-dc.csv(Dublin Core)로'); rc.add_argument('--date', help='기록 날짜(기본: 오늘)')
    rc.add_argument('--verify', action='store_true', help='만들지 않고 checksums.sha256과 실제 파일만 대조(바뀐 것이 있으면 종료 코드 1, CI용)')
    og = sp.add_parser('originals', help='원본 묶음: 선별 문서의 원본 해상도 사진(--full 이면 문서 전체 면) + 원본 영상 → 분할 ZIP')
    og.add_argument('--work', required=True); og.add_argument('--theme', required=True)
    og.add_argument('--full', action='store_true', help='선별 문서의 모든 면을 받아서 묶기 (이미 받은 면은 건너뜀)')
    og.add_argument('--dry-run', action='store_true', help='--full 과 함께: 받지 않고 문서별 전체 면 수만 보기')
    og.add_argument('--only', help='순서 번호만 (예: 1,3)'); og.add_argument('--videos', help='원본 영상·자막 폴더 (mp4/srt/vtt)')
    og.add_argument('--dest'); og.add_argument('--prefix'); og.add_argument('--title'); og.add_argument('--collection'); og.add_argument('--data-url')
    og.add_argument('--max-mb', type=int, default=380, help='ZIP 하나의 최대 크기(MB)'); og.add_argument('--time', type=float, default=540); og.add_argument('--rounds', type=int, default=20)
    a = ap.parse_args()
    if a.cmd == 'edit' and not a.theme and not a.all and not any([a.person, a.types, a.years, a.query]):
        sys.exit('--theme 또는 --person/--types/--years/--query 중 하나는 필요합니다.')
    {'themes': cmd_themes, 'edit': cmd_edit, 'mediate': cmd_mediate, 'promo': cmd_promo, 'zoom': cmd_zoom, 'report': cmd_report, 'originals': cmd_originals, 'delivery': cmd_delivery, 'page': cmd_page, 'check': cmd_check, 'years': cmd_years, 'audit': cmd_audit, 'fix': cmd_fix, 'compare': cmd_compare, 'proof': cmd_proof, 'review': cmd_review, 'record': cmd_record}[a.cmd](a)


if __name__ == '__main__':
    main()
