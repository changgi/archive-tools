# aks-archive-harvester

한국학중앙연구원 **한국고문서자료관**(archive.aks.ac.kr)의 고문서를 모아서 이야기로 만들고, 연구 자료로 묶는 Claude 플러그인입니다.

| 단계 | 하는 일 | 명령 |
|---|---|---|
| ① 수집 | 이름으로 소장처 찾기 → 확대 조각(DZI)을 이어 원본 해상도 JPG로. 이어받기 지원 | `harvest.py find` · `manifest` · `download` |
| ② 큐레이션 | 문서명에서 연도·문서유형·인물 자동 정리, 분포·인물 연표, 테마 후보 제안 | `harvest.py curate` · `studio.py themes` |
| ③ 에디팅 | 테마에 맞는 대표 문서 선별(시기·유형 고르게, 표지 제외), 캡션 초안·밀착인화 → Claude와 다듬기, **큐레이터 노트**(`curator.md`), **전달 에디팅**(`delivery.md`: 정서 · 열기→펼치기→절정→여운 · 물질과 감각 · 통로와 매개 · 여운 장치) | `studio.py edit` |
| ④ 매개 | 결과물 첫 페이지(index.html) · 전시 웹페이지 · 카드뉴스(1080×1350) · 수업 활동지(A4) · SNS 글 · 릴스 문구 | `studio.py mediate` · `promo` |
| 2차 홍보 | 비하인드 카드 3장 · 채널별 홍보안(`channels.md`: 인스타·유튜브·틱톡·페이스북·스레드·X·전시·책·웹툰·영상·광고) · 활용 안내(`references/package-uses.md`) | `studio.py mediate` (큐레이터 노트가 있을 때) |
| 공개 전 점검 | 빈 칸 · 인용 없는 이야기 · 표지 같은 대표 면 · 노트보다 오래된 결과물을 찾아 다음 할 일을 번호로 | `studio.py check` |
| 전달 에디팅 다시 | 문구 에디팅 뒤 절정(원문 한 줄)·여운 질문을 채운 초안으로 다시 쓰기(사람이 쓴 칸은 보존) · 대표 면 바꾸기 | `studio.py delivery` · `page` |
| 영상 | 릴스(9:16)·가로(16:9) 영상 + 자막(.srt), 내레이션(edge-tts 선택), 웹용 540p | `video.py` |
| 시리즈 | 여러 편을 한 사이트로: 갤러리(「이 사이트에 있는 것」 · 자동 요약) · 기획 노트 · 홍보 가이드 · 활용 가이드 · 통합 분석 · 시리즈 카드 | `series.py` |
| 데이터 묶음 | 편별 판독 · 번역 · 해제 · 노트 · 고친 기록 · 분석 집계를 한 ZIP으로(이미지 없음, 읽어보기 포함) | `series.py` → `data.zip` |
| 모아 보기 | 전체 검색(판독 · 번역 · 해제 · 이야기 전문) · 문서 유형 사전(읽는 법 · 건수 · 시대 · 예) · 종이에 적힌 문장 전체(찾기) · 전체 연표(원본 링크) · 남겨 둔 질문 카드(인쇄용) | `analysis.py` · `series.py` |
| 제보 반영 | 제보(GitHub 이슈)를 읽어 문서 · 칸을 찾고, 미리 본 뒤 `selection.csv`에 반영 + 고친 기록 `corrections.csv` → 전시에 「함께 고친 곳」 | `studio.py fix` |
| 옛한글 | 아래아 등 옛한글이 어느 기기에서나 같게 보이도록 그 글자만 담은 글꼴 조각을 필요할 때만 넣음 | 자동 |
| 판독 고침 제보 | 문서마다 「판독 고침 제보」 — GitHub 이슈에 문서명 · 자료 ID · 원본 링크 · 고칠 곳 양식을 채워 열기 | `mediate --issues <저장소 주소>` |
| 링크 미리 보기 · 검색 | 페이지마다 공유 태그(제목 · 설명 · 1200×630 `share.jpg`) — 카카오톡 · 페이스북 · X에 주소를 붙이면 카드로. 시리즈는 `sitemap.xml`(검색 엔진 등록용)도 | `mediate --url` · `series.py --site-url` |
| 접근성 | 키보드로 움직일 수 있는 스크롤 영역 · 눈에 보이는 초점 · 그림 대체 글 · 도표 설명 — 자동 점검(WCAG 2 A/AA) 통과 | 모든 페이지 |
| 설치 확인 | 인터넷 없이 가짜 문서 3건으로 전 과정을 돌려 통과 · 실패 표 | `selftest.py [--video]` |
| 통합 분석 | 전체 편의 시대 · 문서 유형 · 유형×세기 · 소장처 종류 · 지역(막대 · 시·도 타일 지도) · 핵심 정서 · 판독 난도 · 원문 인용 · 인물 · 남겨 둔 질문 · 편별 표 + 자동 요약 | `analysis.py` (series.py가 함께 만듦) |
| 원본 묶음 | 선별 문서의 **문서 전체 면**(원본 해상도) + 원본 영상 + 출처.csv → 400MB 이하 분할 ZIP | `studio.py originals --full` |
| ⑤ 패키징 | 연구 패키지(메타데이터·수집현황·인용·datapackage.json·이미지), 여러 문중 일괄 수집·비교표·그래프 | `harvest.py bundle` · `catalog` · `batch` · `compare` · `studio.py report` |

## 따라하기 예제

처음부터 끝까지 실제로 돌린 예제 — 자동 초안과 다듬은 결과를 단계마다 나란히 보여 줍니다:
[examples/tutorial](../../examples/tutorial/README.md) · [완성된 시리즈 사이트](https://changgi.github.io/archive-tools/examples/tutorial/site/index.html)

## 사용 예 (Claude에게)

> 한국고문서자료관에서 동춘당 송준길 후손가 문서 전부 받아줘
> 혼인과 호적 테마로 전시 웹페이지랑 카드뉴스 만들어줘
> 충청도 문중들을 비교 연구할 수 있게 패키지로 묶어줘
> 이 전시를 왜 이렇게 만들었는지 큐레이터 노트도 붙여줘
> 비하인드 카드랑 채널별 홍보안도 만들어줘
> 완석정 유지로 전시·카드·영상까지 처음부터 끝까지 만들어줘
> 이 편 릴스 영상이랑 가로 영상도 만들어줘
> 세 편을 묶어서 시리즈 사이트로 만들어줘
> 전체를 통합 분석해서 한눈에 보여줘
> 인용 문장이랑 연표, 질문 카드도 모아 줘
> 12번 제보 반영해줘 (판독 고쳐줘)
> 공개해도 되는지 점검해줘
> 첫 면이 두루마리 겉이니 대표 면을 2면으로 바꿔줘
> 이 전시에 쓴 문서들 원본 사진을 문서 전체로 받아서 묶어줘 (영상 원본도 같이)

## 직접 실행

```bash
pip install requests pillow
S=skills/aks-archive-harvester/scripts
python3 $S/selftest.py                                           # 설치 확인(인터넷 불필요)
python3 $S/harvest.py find "동춘당 송준길" --manifest W         # ① 찾기 + 목록
python3 $S/harvest.py download --work W --time 540              #    STATUS: DONE까지 반복
python3 $S/harvest.py curate --work W --collection "동춘당 송준길 후손가"   # ②
python3 $S/studio.py themes --work W
python3 $S/studio.py edit --work W --theme life-1               # ③ selection.csv 다듬기
python3 $S/studio.py delivery --work W --theme life-1           #    문구 에디팅 뒤 전달 에디팅 초안 다시
python3 $S/studio.py check --work W --theme life-1              #    공개 전 점검 → 다음 할 일
python3 $S/studio.py promo --work W --theme life-1 --ep 1 --url <전시 주소>
python3 $S/studio.py mediate --work W --theme life-1 --url <전시 주소>   # ④
python3 $S/video.py --work W --theme life-1 --ep 1 --web         # 영상 (ffmpeg, 선택: pip install edge-tts)
python3 $S/studio.py originals --work W --theme life-1 --full --dry-run   # 문서별 전체 면 수 확인
python3 $S/studio.py originals --work W --theme life-1 --full [--videos 영상폴더]  # 원본 묶음 ZIP
python3 $S/harvest.py bundle --work W --dest pkg --prefix 동춘당  # ⑤

# 여러 편 → 시리즈 사이트 (series.tsv: 편<TAB>작업폴더<TAB>테마)
python3 $S/series.py --list series.tsv --note series.md --out site   # analysis.html(통합 분석)도 함께
python3 $S/analysis.py --list series.tsv --out 분석.html             # 통합 분석만 따로

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
