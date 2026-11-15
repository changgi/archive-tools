# aks-archive-harvester

한국학중앙연구원 **한국고문서자료관**(archive.aks.ac.kr)의 고문서를 모아서 이야기로 만들고, 연구 자료로 묶는 Claude 플러그인입니다.

| 단계 | 하는 일 | 명령 |
|---|---|---|
| ① 수집 | 이름으로 소장처 찾기 → 확대 조각(DZI)을 이어 원본 해상도 JPG로. 이어받기 지원 | `harvest.py find` · `manifest` · `download` |
| ② 큐레이션 | 문서명에서 연도·문서유형·인물 자동 정리, 분포·인물 연표, 테마 후보 제안 | `harvest.py curate` · `studio.py themes` |
| ③ 에디팅 | 테마에 맞는 대표 문서 선별(시기·유형 고르게, 표지 제외), 캡션 초안·밀착인화 → Claude와 다듬기, **큐레이터 노트**(`curator.md`), **전달 에디팅**(`delivery.md`: 정서 · 열기→펼치기→절정→여운 · 물질과 감각 · 통로와 매개 · 여운 장치) | `studio.py edit` |
| ④ 매개 | 결과물 첫 페이지(index.html) · 전시 웹페이지 · 카드뉴스(1080×1350) · 수업 활동지(A4) · SNS 글 · 릴스 문구 | `studio.py mediate` · `promo` |
| 2차 홍보 | 비하인드 카드 3장 · 채널별 홍보안(`channels.md`: 인스타·유튜브·틱톡·페이스북·스레드·X·전시·책·웹툰·영상·광고) · 활용 안내(`references/package-uses.md`) | `studio.py mediate` (큐레이터 노트가 있을 때) |
| 원본 묶음 | 선별 문서의 **문서 전체 면**(원본 해상도) + 원본 영상 + 출처.csv → 400MB 이하 분할 ZIP | `studio.py originals --full` |
| ⑤ 패키징 | 연구 패키지(메타데이터·수집현황·인용·datapackage.json·이미지), 여러 문중 일괄 수집·비교표·그래프 | `harvest.py bundle` · `catalog` · `batch` · `compare` · `studio.py report` |

## 사용 예 (Claude에게)

> 한국고문서자료관에서 동춘당 송준길 후손가 문서 전부 받아줘
> 혼인과 호적 테마로 전시 웹페이지랑 카드뉴스 만들어줘
> 충청도 문중들을 비교 연구할 수 있게 패키지로 묶어줘
> 이 전시를 왜 이렇게 만들었는지 큐레이터 노트도 붙여줘
> 비하인드 카드랑 채널별 홍보안도 만들어줘
> 이 전시에 쓴 문서들 원본 사진을 문서 전체로 받아서 묶어줘 (영상 원본도 같이)

## 직접 실행

```bash
pip install requests pillow
S=skills/aks-archive-harvester/scripts
python3 $S/harvest.py find "동춘당 송준길" --manifest W         # ① 찾기 + 목록
python3 $S/harvest.py download --work W --time 540              #    STATUS: DONE까지 반복
python3 $S/harvest.py curate --work W --collection "동춘당 송준길 후손가"   # ②
python3 $S/studio.py themes --work W
python3 $S/studio.py edit --work W --theme life-1               # ③ selection.csv 다듬기
python3 $S/studio.py mediate --work W --theme life-1            # ④
python3 $S/studio.py originals --work W --theme life-1 --full --dry-run   # 문서별 전체 면 수 확인
python3 $S/studio.py originals --work W --theme life-1 --full [--videos 영상폴더]  # 원본 묶음 ZIP
python3 $S/harvest.py bundle --work W --dest pkg --prefix 동춘당  # ⑤

# 여러 소장처
python3 $S/harvest.py catalog --group 문중 --region 충청 --tsv list.tsv
python3 $S/harvest.py batch --list list.tsv --root R --step manifest   # download, curate도 같은 방식
python3 $S/harvest.py compare --list list.tsv --root R && python3 $S/studio.py report --root R
```

## 이용 시 유의

- 공공 연구기관 서버입니다. 기본 동시 요청 수(타일 16개, 페이지 2장)를 올리지 마세요.
- 수집한 이미지의 이용·재배포는 한국고문서자료관 이용 조건을 따르세요. 대량 이용이나 재배포가 목적이면 기관(031-779-2791)에 원본 제공을 요청하는 편이 확실합니다.
- 연도·유형·인물은 문서명에서 자동 추출한 초안이고, 캡션은 검토 전까지 "초안"으로 표시됩니다. 판독·해석은 원문으로 확인하세요.
- 한국학중앙연구원과 관계없는 개인 제작물입니다.

제작: Song Chang-gi · chgsong@naver.com · https://github.com/changgi
