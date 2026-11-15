# 따라하기 — 「임금이 보낸 종이 세 장」 처음부터 끝까지

aks-archive-harvester의 **모든 단계**를 실제로 돌려 만든 예제입니다. 소장처 세 곳에서 문서 네 건을 골라, 수집 → 큐레이션 → 문구 에디팅 → 큐레이터 노트 → 전달 에디팅 → 매개(전시·카드·활동지·비하인드·채널) → 영상 → 원본 묶음 → 시리즈 사이트까지 갔습니다. 각 단계에서 **기계가 만든 초안**과 **사람(또는 Claude)이 다듬은 결과**를 함께 남겨 두었습니다.

- 완성된 시리즈 사이트: [site/index.html](https://changgi.github.io/archive-tools/examples/tutorial/site/index.html)
- 단계별 파일: [`steps/`](steps/) — W1(완석정 유지 2장) · W2(호계 백패 1장) · W3(충원군 공신교서 1장)
- 같은 방식으로 만든 100편: [예시 갤러리](https://changgi.github.io/archive-tools/examples/)

> 요리로 치면: ① 장보기(수집) ② 재료 고르기(큐레이션) ③ 손질하기(문구 에디팅) ④ 왜 이 요리인가 적기(큐레이터 노트) ⑤ 그릇·순서·조명 정하기(전달 에디팅) ⑥ 차려 내기(매개) ⑦ 영상 ⑧ 원재료 통째로 나누기(원본 묶음) ⑨ 코스 메뉴판(시리즈).

| 단계 | 명령 | 누가 | 결과 |
|---|---|---|---|
| 0 준비 | `pip install requests pillow` (+ 영상: ffmpeg, `pip install edge-tts`) | 사람 | |
| 1 찾기·목록 | `harvest.py find "완석정" --first --manifest W1 --match "유지"` | 도구 | `W1/docs.json` (맞는 문서만 면 목록) |
| 2 받기 | `harvest.py download --work W1 --match "유지"` | 도구 | 원본 해상도 JPG |
| 3 큐레이션·초안 | `harvest.py curate --work W1` → `studio.py edit --work W1 --all --id story` | 도구 | `selection.csv`(캡션 초안) · `curator.md`·`delivery.md` 틀 · 밀착인화 |
| 4 문구 에디팅 | 이미지를 읽고 `selection.csv`의 원문·번역·해제·요약·이야기 채우기 | Claude·사람 | "현대어(原文)" 인용 이야기 |
| 5 큐레이터 노트 | `curator.md` 6칸 | Claude·사람 | 왜 · 전하고 싶은 것 · 보이길 · 쓰는 법 · 비하인드 · 질문 |
| 6 전달 에디팅 | `studio.py delivery --work W1 --theme story` → 다듬기 | 도구 → 사람 | 정서 · 열기→펼치기→절정→여운 · 물질 · 통로 · 여운 장치 |
| (선택) 대표 면 | `studio.py page --work W3 --theme story --n 1 --page 002.jpg` | 사람 | 두루마리 겉면 대신 글이 있는 면 |
| 7 매개 | `studio.py promo … --ep 1` → `studio.py mediate --work W1 --theme story --url <주소>` | 도구 | 첫 페이지 · 전시 · 카드 · 활동지 · 비하인드 카드 · `channels.md` · 홍보 글 |
| 8 영상 | `video.py --work W1 --theme story --ep 1 --url <주소> --web` | 도구 | 릴스 9:16 · 가로 16:9 · 자막 · 웹 압축본 |
| 9 원본 묶음 | `studio.py originals --work W1 --theme story --full --dry-run` → `--full --videos W1/mediate/story/video` | 도구 | 문서 전체 면 + 원본 영상 + `출처.csv` ZIP |
| 10 시리즈 | `series.py --list series.tsv --note series.md --out site` | 도구 | 갤러리 · 기획 노트 · 홍보 가이드 · 활용 가이드 · 시리즈 카드 |

명령의 `harvest.py`·`studio.py`·`video.py`·`series.py`는 `plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/`에 있습니다. Claude에게는 "완석정 유지로 전시랑 영상까지 만들어줘"처럼 말하면 이 순서대로 진행합니다.

---

## 1–2. 찾고, 고른 문서만 받기

```bash
python3 harvest.py find "완석정" --first --manifest W1 --match "유지"
#   → W1/docs.json  (소장처 문서 416건 목록, 면 목록은 '유지'에 맞는 문서만)
python3 harvest.py download --work W1 --match "유지"
```

큰 소장처는 `--tree-only`로 문서명만 먼저 훑고, `--match "정규식"`으로 필요한 것만 받습니다. 서버 동시 접속 수(기본값)는 올리지 않습니다.

## 3. 큐레이션 — 자동 초안

```bash
python3 harvest.py curate --work W2
python3 studio.py edit --work W2 --all --id story
#   01. 1646 백패 — 1646년 신채(申埰) 진사 백패(進士白牌)
```

`edit`가 만든 것: [`steps/W2/1_auto/`](steps/W2/1_auto/) — `selection.csv`, 빈 `curator.md`, 초안 `delivery.md`, 밀착인화.

## 4. 문구 에디팅 — 무엇을 말할까

| 칸 | 자동 초안 (`1_auto`) | 문구 에디팅 후 (`3_final`) |
|---|---|---|
| 해제 | 1646년 신채 관련 백패. 생원·진사시(소과) 합격 증서입니다… | 1646년(인조 24) 사마시 진사과에 합격한 의성의 신채에게 내린 백패입니다. 홍패가 붉은 종이인 것과 달리 소과 합격증은 흰 종이여서 '백패'… |
| 판독 | (비어 있음) | 敎旨 幼學申埰進士三等第十八人入格者 順治三年三月初八日 |
| 번역 | (비어 있음) | 교지. 유학 신채를 진사 3등 제18인으로 입격시킨다. 순치 3년(1646) 3월 초8일. |
| 이야기 | (비어 있음) | 합격증은 짧다. 스무 남짓 글자. "유학 신채를 진사 3등 제18인으로 입격시킨다(幼學申埰進士三等第十八人入格者)." 그런데 날짜가 눈에 걸린다. "순치 3년(順治三年)." 청나라의 연호다… |

원문은 끝까지(□ 못 읽은 글자 · (?) 불확실), 이야기는 종이에 적힌 문장을 "현대어(原文)"로 인용합니다. 판독이 끝나면 `검토` 칸에 표시하면 "초안" 딱지가 사라집니다(이 예제는 초안 표시를 남겨 두었습니다).

## 5. 큐레이터 노트 — 왜 골랐고 무엇을 전하려 하나

[`steps/W2/3_final/curator.md`](steps/W2/3_final/curator.md)

> **왜 이 문서들인가** 스무 남짓 글자의 백패에 청나라 연호 '順治'가 적혀 있다는 점이 눈에 걸렸습니다.
> **전하고 싶은 것** 치욕의 시대에도 사람들은 자기 삶의 성취를 소중히 간직했다는 것.
> **남겨 둔 질문** 오랑캐라 부르던 나라의 연호를 쓰며, 선비들은 어떤 마음이었을까요?

있었던 일만 씁니다. 의도는 만든 사람이 정할 몫이라, Claude는 초안을 쓰고 확인을 받습니다.

## 6. 전달 에디팅 — 어떻게 · 무엇으로 · 어디로 전할까

문구 에디팅을 마친 뒤 초안을 다시 만들면 절정 후보(원문 한 줄)와 여운 질문이 채워집니다.

```bash
python3 studio.py delivery --work W1 --theme story
#   절정: "너는 역마를 타고 올라오라(爾其乘馹上來事)" — 화면·공간에서 이 한 줄만 크게…
```

| | 다시 만든 초안 ([`2_delivery_redraft`](steps/W1/2_delivery_redraft/delivery.md)) | 다듬은 결과 ([`3_final`](steps/W1/3_final/delivery.md)) |
|---|---|---|
| 핵심 정서 | (비어 있음 — 사람이 정함) | 부름의 긴장 |
| 감각과 물질 | 역마 방울·말발굽 소리와 함께 펼치는 두루마리 | 두 유지를 마주 보게, 역마 방울 소리 |
| 여운 장치 | (비어 있음) | "두 번 부르면 가겠어요?" |
| 전달 에디팅 후 | (비어 있음) | 「왕이 보낸 쪽지의 마지막 한 마디」로 열고 … "너는 역마를 타고 올라오라"에서 멈춘다 … |

이미 사람이 쓴 칸(정서 · 여운 장치 · 전달 에디팅 후)이 있으면 덮어쓰지 않습니다(`--force`로만, 백업을 남김).

![전시 웹페이지의 연출 노트](img/delivery.jpg)

## 7. 매개 — 전시 · 카드 · 활동지 · 비하인드 · 채널

```bash
python3 studio.py promo   --work W1 --theme story --ep 1 --series "임금이 보낸 종이" --url <전시 주소>
python3 studio.py mediate --work W1 --theme story --url <전시 주소>
#   2차 홍보: 비하인드 카드 3장 · channels.md(채널별 홍보안)
```

| 결과물 | 예시 |
|---|---|
| 첫 페이지 `index.html` | ![첫 페이지](img/ep-index.jpg) |
| 전시 웹페이지 `exhibit.html` | ![전시](img/exhibit.jpg) |
| 활동지 `handout.html` — 끝에 「선생님께」 | ![활동지](img/handout.jpg) |
| 비하인드 카드 `cards/b1–b3` | ![비하인드 카드](img/behind.jpg) |
| 채널별 홍보안 | [`site/eps/01-story/channels.md`](site/eps/01-story/channels.md) |

이미지 사용 동의 전에 공개하려면 `mediate --placeholder`(이미지 대신 "자료관 뷰어에서 보기" 자리).

## 8. 영상 — 릴스와 가로

```bash
python3 video.py --work W3 --theme story --ep 3 --url <전시 주소> --web
#   ep03-story_reel.mp4  52초  장면 6개
#   ep03-story_wide.mp4  52초  장면 6개
```

장면: 열기(전달 에디팅) → 소개 → 문서마다 이미지 + 원문 인용 → 절정 → 비하인드 → 질문·출처. 내레이션은 edge-tts(없으면 무음 + 자막). 사내 프록시처럼 자체 인증서 환경이면 `AKS_CA_BUNDLE=인증서경로`.

| 가로 16:9 | 세로 9:16 |
|---|---|
| ![가로](img/video_wide.jpg) | ![릴스](img/video_reel.jpg) |

영상: [EP.03 가로](site/eps/03-story/video/ep03-story_wide_web.mp4) · [EP.01 릴스](site/eps/01-story/video/ep01-story_reel_web.mp4)

## 9. 원본 묶음 — 문서 전체 면 + 원본 영상

```bash
python3 studio.py originals --work W3 --theme story --full --dry-run
#   선별 문서 1건 · 전체 6면
python3 studio.py originals --work W3 --theme story --full --videos W3/mediate/story/video
#   상주충주박씨충원군박동형종가_원본.zip  18MB
#   → 사진 6면 / 전체 6면 · 영상 3개
```

ZIP 안 목록: [`steps/W3/originals_list.txt`](steps/W3/originals_list.txt) (용량 때문에 ZIP은 저장소에 넣지 않았습니다).

## 10. 시리즈 — 여러 편을 한 사이트로

[`series.tsv`](series.tsv) (편 · 작업 폴더 · 테마) 와 [`series.md`](series.md) (기획 노트: 왜 만들었나 · 전하고 싶은 것 · 고른 기준 · 이렇게 보이길 바랐다 · 이렇게 써 주세요 · 지킨 원칙 · 히스토리)를 쓰고:

```bash
python3 series.py --list series.tsv --note series.md --out site
#   → site  편 3 · 문서 4 · 시리즈 카드 7장
```

![시리즈 사이트](img/site.jpg)

결과: [갤러리](site/index.html) · [기획 노트](site/about.html) · [홍보 가이드](site/promote.html) · [활용 가이드](site/use.html) · 편마다 [`eps/`](site/eps/).

---

### 다음은

- 자기 소장처로 바꿔 보세요: `find "소장처 이름"` 한 줄부터.
- 2차 홍보(비하인드 카드 · 시리즈 카드)와 채널별 홍보: [홍보 가이드](https://changgi.github.io/archive-tools/examples/promote.html)
- 받은 사람이 무엇을 할 수 있나: [활용 가이드](https://changgi.github.io/archive-tools/examples/use.html)

이미지: 한국학중앙연구원 한국고문서자료관 소장·제공 · 성주 명곡 벽진이씨 완석정 이언영 종가 · 의성 아주신씨 호계 신적도 가문 · 상주 충주박씨 충원군 박동형 종가. 재사용은 소장처 동의가 필요합니다(031-730-8873, 8876). 판독·해석은 이미지에 근거한 초안입니다.
