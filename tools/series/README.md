# tools/series — 「고문서 한 장」 제작 도구

이 시리즈(예시 사이트 `examples/`)를 **처음부터 다시 만들 수 있도록** 실제로 쓴 제작 스크립트와 원고를 그대로 둔 곳입니다.
플러그인(`plugins/aks-archive-harvester`)이 "누구나 쓰는 도구"라면, 여기는 "이 시리즈를 만든 작업대"입니다.

> 비유하면 플러그인은 **조리 도구**, `data/`는 **레시피 카드**, 여기 스크립트는 **이 식당의 주방 순서표**입니다.
> 순서표와 레시피가 남아 있으면 요리사가 바뀌어도 같은 음식을 다시 낼 수 있습니다.

## 무엇이 들어 있나

| 위치 | 내용 | 저장소에 |
|---|---|---|
| `data/new*/<작업>.json` | 편 원고 — 판독 · 원문 · 번역 · 해제 · 요약 · 이야기, 훅 · 인용, 홍보 문구, 큐레이터 노트, 전달 에디팅 | 올림 |
| `data/ep*-<폴더>.json` | 영상 렌더 설정(장면 · 자막 · 음성 문장). 폴더 위치는 `$WORK` · `$DATA` 이름으로 저장 | 올림 |
| `data/promo/` · `*.json` | 홍보 글 원본, 갤러리용 모음(captions · curator · delivery) | 올림 |
| `work/` | 소장처 작업 폴더(`harvest.py --work`) — 원본 이미지 | **안 올림**(자료관에서 다시 받음) |
| `../archive-tools-next/media/` | 예시 영상(mp4) — GitHub Pages 1GB 한도 때문에 [별도 저장소](https://github.com/changgi/archive-tools-next). `media_offload.py`가 옮기고 링크를 바꿈 | 별도 저장소 |
| `state/` | 원본 묶음 목록(collect.json) · 기록 메타 · 로그 | 안 올림 |

## 순서

```bash
# 0) 소장처 받기 — 플러그인 도구 (동시 요청 수는 기본값 그대로)
python3 plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/harvest.py ... --work tools/series/work/<작업>

# 1) 선별 — 문서명 정규식에 맞는 문서를 순서대로 고름
python3 tools/series/pick.py <작업> "홍패" "교지@2"

# 2) 원고 — data/new4/<작업>.json 작성(판독 · 번역 · 해제 · 이야기 …) → 날짜 · 인용 점검

# 3) 한 편 만들기 — 전시 · 카드 → 영상(릴스 · 가로) → media · README → 노트 · 홍보 · 비하인드 · 검토지
bash tools/series/ep_make.sh <작업>          # 영상 빼고: bash tools/series/ep_make.sh <작업> norender
#    여러 편: data/q4.txt에 한 줄씩 적고  bash tools/series/runq.sh

# 4) 사이트 다시 만들기 → 판독 점검 → 기록 꾸러미 → 링크 점검
bash tools/series/site_build.sh
```

`site_build.sh` 안의 순서(바꾸면 결과가 달라짐): gallery → readme_ex → analysis_build → about_build → share_apply → seo_apply → a11y_apply → a11y_all → en_build → readme_stats → `studio.py audit` → `record_build.py` → `check_links.py`.

## 폴더 위치 바꾸기

모든 스크립트는 `_paths.py`를 거쳐 위치를 정합니다. 환경 변수로 바꿀 수 있습니다.

| 변수 | 뜻 | 기본 |
|---|---|---|
| `SERIES_REPO` | 저장소 | 이 폴더의 두 단계 위 |
| `SERIES_DATA` | 원고 · 설정 | `tools/series/data` |
| `SERIES_WORK` | 소장처 작업 폴더 | `tools/series/work` |
| `SERIES_CAND` | 예전 후보 작업 폴더 | `SERIES_WORK` |
| `SERIES_STATE` | 상태 · 로그 | `tools/series/state` |
| `SERIES_NEXT` | 영상 저장소 archive-tools-next | 저장소 옆 `../archive-tools-next` |

## 기록 꾸러미 (record.json · checksums.sha256)

`record_build.py`가 편 폴더마다 **맥락 · 출처 · 파생물 · 검증 · 검토 · 작업 이력**을 담은 `record.json`과 SHA-256 고정값 목록을 만들고,
전체 목록을 `examples/records.jsonl`(한 줄 한 편) · `examples/records-dc.csv`(Dublin Core)로 냅니다. 개념은 [`references/records.md`](../../plugins/aks-archive-harvester/skills/aks-archive-harvester/references/records.md).

```bash
python3 tools/series/record_build.py            # 만들기(바뀐 것이 있을 때만 이력에 한 줄)
python3 tools/series/record_build.py --verify   # 대조만 — CI도 같은 대조를 함
```

## 다시 만들 때 필요한 것

- Python 3.10+, `pillow`, `numpy`, `hanja`, `edge-tts`(음성), `requests`
- `ffmpeg`, Node + `playwright`(전시 화면 캡처 · 카드 렌더)
- 원본 이미지는 저장소에 없습니다. 선별표(`selection.csv`)의 **자료ID**로 자료관에서 다시 받습니다.

## 지켜 온 원칙

- 검토 칸은 **원본과 대조한 사람만** 채웁니다. 도구와 AI는 검토를 표시하지 않습니다.
- 이미지 재사용은 자료관을 통한 **소장처 동의**가 필요합니다. 출처를 적고, 문제가 있으면 내립니다.
- 텍스트(판독 · 번역 · 해제 · 이야기 · 노트)는 CC BY 4.0, 코드는 MIT. 플러그인을 쓰는 다른 사람의 라이선스는 정하지 않습니다.
- 자료관 서버에 부담을 주지 않도록 내려받기 동시 요청 수는 기본값을 그대로 둡니다.

만든 사람: Song Chang-gi · chgsong@naver.com · https://github.com/changgi
