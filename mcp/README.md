# archive-tools MCP — 원격 MCP 서버

「고문서 한 장」 큐레이션과 한국고문서자료관(archive.aks.ac.kr)을 AI 비서에서 바로 쓰게 하는
**원격 MCP 서버**입니다. 이 폴더만 Vercel에 배포하며, 저장소의 GitHub Pages(`examples/`)와
Claude 플러그인(`plugins/aks-archive-harvester`)은 그대로입니다.

| 항목 | 값 |
|---|---|
| 엔드포인트 | `https://archive-tools-mcp.vercel.app/api/mcp` |
| 프로토콜 | MCP **2025-06-18** · Streamable HTTP · **stateless**(세션 없이 매 요청 독립) |
| 도구 | **12종** — 전부 `readOnlyHint` · `idempotentHint` · `openWorldHint: true` |
| 응답 | 24KB 이내 · 같은 입력 → 같은 바이트(정렬 고정 · 시각 값 없음) |
| 실행 리전 | 서울(icn1) — 국내 공공 사이트 정상 접근용 |
| 실측 기록 | [VERIFICATION.md](VERIFICATION.md) — 데이터 재생성 바이트 일치 · 정적 21건 · 엔드포인트 19건 · MCP 클라이언트 14건 |

## 도구

| 묶음 | 도구 | 하는 일 |
|---|---|---|
| 큐레이션 | `curation_search` | 200편 · 문서 726건에서 낱말 · 한자 · 인물 · 문서유형 · 연도로 검색 |
| | `curation_item` | 문서 한 건의 **판독 · 원문 · 번역 · 해제 · 요약 · 이야기** + 전시 · 활동지 · 카드뉴스 · IIIF · 원본 뷰어 링크 |
| | `curation_episode` | 한 편의 기획 의도 · 큐레이터 노트 · 문서 목록 · 산출물 |
| | `curation_people` | 인물 258명 — 이름이 적힌 문서와 편 |
| | `curation_timeline` | 726건 연표(1403–2000) |
| | `curation_quotes` | 문서 위 문장 763곳 — "현대어(原文)" 쌍 |
| | `doc_type` | 문서 유형 사전(79항목) + 유형별 실제 문서 |
| | `curation_stats` | 규모 · 분포 · 데이터 지문 |
| 실시간 | `aks_catalog` | 한국고문서자료관 소장처 173곳 |
| | `aks_find` | 이름으로 소장처 찾기 |
| | `aks_manifest` | 소장처 안의 문서 목록(자료ID · 문서명 · 페이지 수 · 원본 뷰어) — 실시간 |
| 상태 | `health` | 버전 · 도구 목록 · 데이터 지문 · (선택) 자료관 접속 |

## 데이터는 어디서 오나

`data/curation.json`은 손으로 쓰지 않습니다. 저장소의 실제 산출물에서 생성합니다.

```
python3 mcp/scripts/build_dataset.py      # examples/*/selection.csv + record.json + curator.md
                                          # + analysis-data.json + viewer-data.json
                                          # + studio.py GLOSSARY / find_quotes
```

- 편 200 · 문서 726 · 소장처 131곳 · 1403–2000년 · 판독 한자 44,093자 · 원문 인용 763곳 · 인물 258명
- 위 수치는 `examples/analysis-data.json`(통합 분석 페이지가 쓰는 값)과 **정확히 같아야** 하고, CI가 대조합니다.
- `data/aks_catalog.json`은 archive.aks.ac.kr의 소장처 트리를 받아 둔 스냅숏입니다(2026-11-28, 173곳).

## 만들고 확인하기

```bash
cd mcp
npm ci
python3 scripts/build_dataset.py     # 데이터셋 재생성(같은 저장소 상태면 같은 바이트)
node scripts/ci-verify.mjs           # 정적 검증 21건
npx next build && npx next start -p 3111
python3 scripts/verify_endpoint.py --url http://127.0.0.1:3111/api/mcp --repeat 3
node scripts/client-check.mjs         # 실제 MCP 클라이언트(SDK)로 붙어 도구 12종 호출
```

CI는 `mcp/ci/mcp-verify.yml`(데이터 재생성 대조 · 정적 21건 · 빌드 · 엔드포인트 실측)입니다.

`verify_endpoint.py`는 initialize · tools/list · 도구 12종 실호출 · **같은 질의 여러 번 실행해
바이트 일치** · 24KB 한도 · 세션 헤더 없이 동작을 확인합니다. 운영 URL을 그대로 넣어 점검할 수 있습니다.

## 배포 (Vercel 빌드 CPU 0원)

`mcp/ci/deploy-prebuilt.yml`(→ `.github/workflows/`, 이유는 [mcp/ci/README.md](ci/README.md))이 GitHub Actions 러너에서 `vercel build`로 빌드를 끝내고
`vercel deploy --prebuilt`로 산출물만 올립니다. Vercel 쪽에서는
**Settings → Build and Deployment → Ignored Build Step = "Don't build anything (exit 0)"** 으로 두어
Git push 때 중복 빌드가 돌지 않게 합니다. 기계는 **Standard**(함수 1,769MB · 1 vCPU)를 씁니다.

필요한 Repository secret은 `VERCEL_TOKEN` 하나입니다(값은 로그·파일에 남기지 않습니다).

## 예절과 한계

- **읽기 전용.** 이 서버는 아무것도 내려받거나 저장하지 않고, `aks_*` 도구는 자료관 사이트에서 메타데이터만 읽습니다(동시 요청 4개 이하, 정직 UA — 브라우저 위장 없음).
- 판독 · 번역 · 해제는 **사람 대조 전 초안**이 섞여 있습니다. `검토` 칸이 비어 있으면 응답도 그렇게 밝힙니다.
- 고문서 이미지의 이용·재배포는 소장처 동의가 필요합니다(한국학중앙연구원 한국고문서자료관).
- 텍스트 CC BY 4.0 · 코드 MIT.
