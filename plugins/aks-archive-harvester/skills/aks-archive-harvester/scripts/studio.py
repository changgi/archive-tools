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
  promo   : 릴스 홍보 문구 틀(「고문서 한 장」 형식) → mediate/<테마>/promo.md
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
    y = f"{r['_y']}년" if r['_y'] else '연대 미상'
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
    """대표 면: 앞에서부터 보아 표지·빈 면(뒷면)이 아닌 첫 면. 없으면 글씨가 가장 많은 면."""
    ims = doc_images(work, r)
    best, score = None, -1
    for p in ims[:8]:
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
                    '대표장': os.path.basename(src), '이미지': f'images/{fn}', '원본경로': os.path.relpath(src, a.work),
                    '캡션': draft_caption(r) + (f' (첩 이미지 {len(doc_images(a.work, r))}면 중 한 면 — 해당 면은 원문 확인 필요)' if shared > 1 else ''),
                    '이야기': '', '판독': '', '해제': draft_haeje(r), '요약': '', '검토': '', '뷰어링크': r.get('뷰어링크', ''), '공유이미지': (f'{shared}건이 같은 첩 이미지를 공유' if shared > 1 else '')})
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
    print('→', od, '(selection.csv의 캡션·이야기를 다듬고, 이미지를 읽어 판독·해제·요약을 채운 뒤 mediate)')


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


def has_reading(s):
    """판독 칸에 실제로 읽은 글자가 있는지 (괄호 속 설명만 있으면 False)"""
    t = re.sub(r'\([^)]*\)', '', s.get('판독') or '')
    return len(re.findall(r'[\u4e00-\u9fff\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]', t)) >= 2

def aid_html(s):
    """해제·원문 읽기·내용 요약 블록 (비어 있으면 생략)"""
    parts = []
    if s.get('해제'): parts.append(f"<p><b>해제</b>{html.escape(s['해제'])}</p>")
    if has_reading(s): parts.append(f"<p><b>원문 읽기</b><span class=\"orig\">{html.escape(s['판독'])}</span></p>")
    if s.get('요약'): parts.append(f"<p><b>내용 요약</b>{html.escape(s['요약'])}</p>")
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
{aid_html(s)}
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
h2{{font-size:28px;margin:0 0 .4em}}
.aid{{background:#211b14;border:1px solid #4a3e2c;border-radius:10px;padding:12px 16px;margin:10px 0 14px;font:15.5px/1.75 'Noto Sans KR','Malgun Gothic',sans-serif;color:#e4d9c3}}
.aid summary{{cursor:pointer;color:#c4964a;font-weight:700;letter-spacing:.05em}} .aid p{{margin:.55em 0}}
.aid b{{display:inline-block;min-width:5.2em;color:#c4964a;margin-right:.4em}} .aid .orig{{font-family:'Noto Serif KR','Batang',serif;color:#f3ead8}}
.aid small{{display:block;color:#9d917c;font-size:12.5px;margin-top:6px}} .cap{{font-size:19px;line-height:1.8}} .meta{{font-size:14px;color:#9d917c;font-family:sans-serif}}
.draft{{display:inline-block;font:13px sans-serif;color:#16130f;background:#c4964a;padding:3px 10px;border-radius:12px}}
footer{{padding:6vw;color:#9d917c;font:15px/1.8 sans-serif;border-top:1px solid #3a3225}}
@media(max-width:800px){{.panel{{grid-template-columns:1fr}} .line:before{{display:none}}}}
@media print{{body{{background:#fff;color:#111}} header{{min-height:auto;background:none}} .panel{{page-break-inside:avoid}}}}
</style></head><body><header><small>{html.escape(coll)} · {span}</small><h1>{html.escape(title)}</h1>
<p>{html.escape(a.lead or f'한국고문서자료관에 흩어져 있던 집안 문서 {len(sel)}점을 시간 순서로 엮었습니다.')}</p></header>
<main class="line">{''.join(items)}</main>
<footer>{html.escape(src_line)}. 이미지의 이용·재배포는 자료관 이용 조건을 따릅니다.<br>「읽기 도움」의 해제·원문 읽기·내용 요약은 문서명과 이미지에 근거한 초안입니다. 판독이 어려운 글자는 □로 표시했으며, 개별 문서의 판독·해석은 원문 확인이 필요합니다.<br>제작 도구: aks-archive-harvester (github.com/changgi/archive-tools)</footer></body></html>"""
    open(os.path.join(od, 'exhibit.html'), 'w', encoding='utf-8').write(page)

    # 3) 수업 활동지 (인쇄용 HTML)
    qs = []
    for s in sel:
        qs.append(f"""<div class="q">{fig(s, 900)}<div><h3>{s['순서']}. {html.escape(str(s['연도']))} {html.escape(s['문서유형'])}</h3>
<p><b>어떤 문서? (해제)</b> {html.escape(s.get('해제') or s['유형설명'] or '—')}</p>
{('<p><b>무슨 내용? (내용 요약)</b> ' + html.escape(s['요약']) + '</p>') if s.get('요약') else ''}
{('<p class="orig"><b>원문 속 글자</b> ' + html.escape(s['판독']) + '</p>') if has_reading(s) else ''}
<p><b>찾아보기</b> {('① 위 「원문 속 글자」를 이미지에서 찾아 동그라미 해 보세요. ' if has_reading(s) else '① 문서를 받은 사람(또는 쓴 사람)의 이름을 찾아 표시해 보세요. ')}② 날짜가 적힌 곳을 찾아보세요. ③ 도장(인장)이 있나요?</p>
<p><b>생각해 보기</b> 이 문서는 왜 지금까지 집안에 남아 있었을까요?</p></div></div>""")
    hand = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>활동지 — {html.escape(title)}</title><style>
@page{{size:A4;margin:16mm}} body{{font-family:'Malgun Gothic','Noto Sans KR',sans-serif;color:#222;font-size:14px}}
h1{{font-size:24px;margin:0}} .sub{{color:#666;margin:4px 0 16px}} .q{{display:grid;grid-template-columns:42% 1fr;gap:14px;border-top:1px solid #ccc;padding:12px 0;page-break-inside:avoid}}
.q img{{width:100%}} .ph{{display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;aspect-ratio:4/3;border:2px dashed #b89a68;color:#5a4628;text-decoration:none;padding:10px;font-size:13px}} .ph b{{font-size:15px;margin:6px 0}} .ph em{{font-style:normal;color:#9a6e2e}} h3{{margin:0 0 6px}} p{{margin:4px 0;line-height:1.6}} .orig{{background:#f6f1e6;padding:4px 8px;border-radius:4px;font-family:'Batang','Noto Serif KR',serif}} .box{{border:1px dashed #999;height:120px;margin-top:10px;padding:8px;color:#999}}
</style></head><body><h1>고문서로 읽는 이야기: {html.escape(title)}</h1><p class="sub">{html.escape(coll)} · {span} · 이름: ________ </p>{''.join(qs)}
<h3>정리해 보기</h3><div class="box">이 문서들을 시간 순서로 이으면 어떤 이야기가 되나요? 세 문장으로 써 보세요.</div>
<p class="sub">{html.escape(src_line)} · 이미지 이용은 자료관 이용 조건을 따릅니다. 해제·요약은 문서명과 이미지에 근거한 초안이며 판독이 어려운 글자는 □로 표시했습니다.</p></body></html>"""
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

# ---------------------------------------------------------------- promo (릴스 홍보 문구)
PROMO_TEMPLATE = """📜 {series} EP.{ep} 〈{title}〉

{hook}

{body}

{follow} 이 기록을 바탕으로 Claude 플러그인 aks-archive-harvester로 전시 웹페이지, 카드뉴스, 수업 활동지, SNS 게시글을 만들었습니다.
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
    people = [p for p in dict.fromkeys(x.strip() for s in sel for x in s['인물'].split(';')) if p][:4]
    kinds = list(dict.fromkeys(s['문서유형'] for s in sel))[:4]
    tags = ['#' + a.series.replace(' ', '')] + ['#' + t.replace(' ', '') for t in (people + [coll.split()[-1]] + kinds)] + ['#고문서', '#한국고문서자료관', '#디지털인문학', '#Claude', '#오픈소스']
    first, last = (sel[0], sel[-1]) if sel else ({}, {})
    fill = dict(series=a.series, ep=f'{a.ep:02d}', title=title, collection=coll, url=a.url or '[전시 웹페이지 주소]',
                hook='[이모지 1개 + 궁금증을 여는 질문 한 문장]',
                body=f"[{coll}에 무엇이 남아 있는지 → 문서를 시간 순서로 2~4문장 ({ys[0] if ys else '?'}–{ys[-1] if ys else '?'}). 문서명·이미지·판독에서 확인한 사실만]",
                follow='[이번 릴스에서는 ○○을 따라가 봅니다.]',
                question=f"[여러분이라면 {(first.get('연도') + '년 ') if first.get('연도') else ''}{first.get('문서유형','A')}와 {(last.get('연도') + '년 ') if last.get('연도') else ''}{last.get('문서유형','B')} 중 어느 쪽을 먼저 펼쳐보고 싶으세요?]",
                label=f'[{title} 온라인 전시 보기]', tags=' '.join(dict.fromkeys(tags)))
    out = os.path.join(a.work, 'mediate', a.theme); os.makedirs(out, exist_ok=True)
    txt = PROMO_TEMPLATE.format(**fill)
    open(os.path.join(out, 'promo.md'), 'w', encoding='utf-8').write(
        f"# 릴스 홍보 문구 — {title}\n\n[대괄호] 칸을 selection.csv의 이야기·해제·요약에 근거해 채우세요. 나머지 줄은 그대로 둡니다.\n\n```\n{txt}\n```\n")
    print(txt); print('→', os.path.join(out, 'promo.md'))


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
    pr = sp.add_parser('promo', help='릴스 홍보 문구 틀(「고문서 한 장」 형식) → mediate/<테마>/promo.md'); pr.add_argument('--work', required=True); pr.add_argument('--theme', required=True)
    pr.add_argument('--ep', type=int, default=1); pr.add_argument('--series', default='고문서 한 장'); pr.add_argument('--title'); pr.add_argument('--collection'); pr.add_argument('--url', help='전시 웹페이지 주소')
    r = sp.add_parser('report'); r.add_argument('--root', required=True); r.add_argument('--top', type=int, default=12)
    a = ap.parse_args()
    if a.cmd == 'edit' and not a.theme and not a.all and not any([a.person, a.types, a.years, a.query]):
        sys.exit('--theme 또는 --person/--types/--years/--query 중 하나는 필요합니다.')
    {'themes': cmd_themes, 'edit': cmd_edit, 'mediate': cmd_mediate, 'promo': cmd_promo, 'report': cmd_report}[a.cmd](a)


if __name__ == '__main__':
    main()
