# archive-tools

기록·고문서 아카이브 조사와 수집을 위한 Claude 플러그인 모음입니다.

| 플러그인 | 하는 일 |
|---|---|
| [aks-archive-harvester](plugins/aks-archive-harvester) | 한국고문서자료관 고문서 ① 수집 ② 큐레이션 ③ 에디팅 ④ 매개(전시 웹페이지·카드뉴스·수업 활동지) ⑤ 연구 패키지·여러 문중 비교 연구 |

## 예시 보기

▶ **https://changgi.github.io/archive-tools/examples/** — 실제로 만든 전시 웹페이지·카드뉴스·수업 활동지·비교 리포트

| 혼인과 호적 (에디팅 후) | 송준길의 생애 (에디팅 전) | 땅과 관청 사이 (다른 소장처) |
|---|---|---|
| [![](examples/dongchundang-marriage/cards/00_표지.jpg)](examples/dongchundang-marriage/) | [![](examples/dongchundang-songjungil/cards/00_표지.jpg)](examples/dongchundang-songjungil/) | [![](examples/yuhoedang-land/cards/00_표지.jpg)](examples/yuhoedang-land/) |

| 절을 짓고 다시 세운 기록 (사찰) | 섬마을에 내려온 약속 (마을) | 서원을 지키고 꾸린 기록 (서원) | 왕비의 편지 (박물관) |
|---|---|---|---|
| [![](examples/jikjisa-temple/cards/00_표지.jpg)](examples/jikjisa-temple/) | [![](examples/susanri-village/cards/00_표지.jpg)](examples/susanri-village/) | [![](examples/namgye-seowon/cards/00_표지.jpg)](examples/namgye-seowon/) | [![](examples/myeongseong-letters/cards/00_표지.jpg)](examples/myeongseong-letters/) |

🔎 **읽기 도움:** 옛 한자·이두·흘림 글씨·한글 편지를 현대인이 읽을 수 있게, 문서마다 **원문 전문 판독(한자 위 한글 독음) · 원문 해석 · 해제 · 내용 요약**을 전시 웹페이지와 수업 활동지에 넣습니다.

📜 **원문으로 읽는 이야기 10편 (EP.17–EP.26):** 회재 이언적 · 류성룡의 비답 · 양동 손소 공신교서 · 임청각과 정약용 편지 · 학봉 종가 한글 편지 · 서계 박세당 · 우복 정경세 · 황윤석 집안의 흉년 문서 · 거창향교 · 명성황후의 꽃 편지지 — 원문 전문 판독 + 해석 + 원문 인용 스토리텔링 → [보기](https://changgi.github.io/archive-tools/examples/)

📜 **원문으로 읽는 이야기 24편 더 (EP.27–EP.50):** 강릉 선교장 · 점필재 · 여헌 장현광 · 하회 소년의 경성 유학 엽서 · 박의장 · 진주 사창 사건 · 수당 이남규 · 옥천사 · 제주 해녀 절목 · 최진립 · 김홍욱 · 오윤겸 · 과거 시험지 · 일주일 뒤의 부름 · 숙종이 보낸 숯 · 하위지의 조카 · 기러기와 장터 · 덕남서원 소나무 · 굶주림의 명문 · 큰물과 투장 · 김해 향안 · "술은 석 잔까지" · 효종의 답장 · 송규렴의 한글 편지 → [보기](https://changgi.github.io/archive-tools/examples/)

📜 **원문으로 읽는 이야기 50편 더 (EP.51–EP.100):** 귀화 일본 장수 사여모 · 유희의 『물명고』 · 제주의 종이 신분증 지패 · 공명첩 · 사또의 성적표 포폄 · 밀부 제34부 · 험천의 김홍익 · 1919년 만일계 · 1592년 안동 의병 일지 · 이완용 서명의 관고 · 농암 이현보의 양로연 · 류성룡 증손녀의 호적 · 몰래 무덤 산송 · 1904년 향교 완문 · 하홍도의 여름 편지 외 — 문중 · 서원 · 향교 · 사찰 · 제주 문서까지 → [보기](https://changgi.github.io/archive-tools/examples/) · 첫 화면 「결과물 한눈에 보기」에서 영상 · 전시 · 활동지 · 카드뉴스 · CSV · 홍보 글로 바로 가기

✍️ **큐레이터 노트 · 기획 노트:** 편마다 왜 골랐고 무엇을 전하려 했는지, 만들며 있었던 일까지 — [기획 노트](https://changgi.github.io/archive-tools/examples/about.html) · 갤러리 각 편 「비하인드」 탭

📢 **2차 홍보 · 채널 · 활용:** [시리즈 비하인드 릴스·카드](https://changgi.github.io/archive-tools/examples/#series) · [채널별 홍보 가이드](https://changgi.github.io/archive-tools/examples/promote.html) · [패키지 활용 가이드](https://changgi.github.io/archive-tools/examples/use.html)

🎭 **문구 에디팅 + 전달 에디팅:** 무엇을 말할지에 더해, 고른 기록을 어떤 정서 · 장면 · 물질 · 통로 · 매개로 전할지 — 갤러리 각 편 「전달 에디팅」 탭 · [기획 노트](https://changgi.github.io/archive-tools/examples/about.html#delivery)

📖 **이야기가 있는 기록 10편 (EP.7–EP.16):** 왕실 가족의 편지 · 운조루의 시간 · 되찾은 제사 땅 · 섬마을의 호소 · 윤음에서 금융조합까지 · 기도와 살림의 기록 · 200년의 상소 · 나아가지 않은 선비 · 서원을 움직인 사람들 · 학자의 벼슬길 → [보기](https://changgi.github.io/archive-tools/examples/)

명령을 하나씩 따라 하는 예제는 [`examples/README.md`](examples/README.md)에 있습니다.

🎬 **홍보 영상:** [EP.1 흩어진 기록을, 다시 이야기로(83초)](https://changgi.github.io/archive-tools/examples/media/promo-reel.mp4) · [EP.2 만든 것 보기(48초)](https://changgi.github.io/archive-tools/examples/media/promo-reel-ep2.mp4) · EP.3–EP.6 예시 세트 영상은 [예시 README](examples/README.md#예시-세트-영상-ep3ep6) · 이미지 출처: 한국학중앙연구원 한국고문서자료관(이미지 재사용은 자료관 문의, 소장처 동의 필요)

## 설치

### Claude Code / Cowork (권장, 업데이트 자동 반영)

```
/plugin marketplace add changgi/archive-tools
/plugin install aks-archive-harvester@changgi-archive-tools
```

새 버전이 나오면:

```
/plugin marketplace update changgi-archive-tools
```

### 파일로 설치

[Releases](../../releases) 또는 `dist/`에서 받으세요.

- `aks-archive-harvester.plugin`: Claude Cowork에 올려 설치
- `aks-archive-harvester-skill.zip`: claude.ai 스킬 설정에서 업로드

### 파이썬만 쓰기

```bash
pip install requests pillow
python3 plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/harvest.py --help
python3 plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/studio.py --help
```

## 사용 예

> 한국고문서자료관에서 동춘당 송준길 후손가 문서 전부 받아줘
>
> 혼인과 호적 테마로 전시 웹페이지랑 카드뉴스 만들어줘
>
> 충청도 문중들을 비교 연구할 수 있게 패키지로 묶어줘

## 이용 시 유의

- 공공 연구기관 서버입니다. 기본 동시 요청 수(타일 16개, 페이지 2장)를 올리지 마세요.
- 수집한 이미지의 이용·재배포는 한국고문서자료관 이용 조건을 따르세요. 대량 이용은 기관(031-779-2791)에 원본 제공을 요청하는 것이 확실합니다.
- 이 도구는 한국학중앙연구원과 관계없는 개인 제작물입니다.

## 만든 사람

Song Chang-gi · chgsong@naver.com · https://github.com/changgi
