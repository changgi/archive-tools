# 실측 기록 — archive-tools MCP

이 파일은 **직접 실행한 점검 결과**를 그대로 옮긴 것입니다. 재현 방법은 [README](README.md#만들고-확인하기).

- 점검일: 2026-11-28 (KST)
- 대상: `mcp/` (Next.js 15.5.29 · mcp-handler 1.1.0 · Node 24) — 로컬 `next start`
- 데이터 지문: `sha256 5fe988d21f83fdc0c5d66c947c8a8843c45a8e0285653c587add8396d06dc3ce`

## 1. 데이터셋 재생성 — 같은 바이트

```
$ python3 mcp/scripts/build_dataset.py
docs 748 (편 200 · 번호 전 3) · 인용 766 · 인물 258 · 유형 189 · 2434.5KB · sha256 5fe988d21f83fdc0
$ python3 mcp/scripts/build_dataset.py
docs 748 (편 200 · 번호 전 3) · 인용 766 · 인물 258 · 유형 189 · 2434.5KB · sha256 5fe988d21f83fdc0
```

세 번 연속 실행해도 같은 지문입니다. 수치는 `examples/analysis-data.json`(통합 분석 페이지)과 일치합니다 —
편 200 · 문서 726 · 소장처 131 · 1403–2000년 · 판독 한자 44,093 · 인용 763.

## 2. 정적 검증 — 21건 전부 통과

```
$ node mcp/scripts/ci-verify.mjs
  ✓ 편 200   ✓ 문서 726   ✓ 소장처 131   ✓ 판독 한자 44093   ✓ 인용 763   ✓ 연대 1403–2000
  ✓ 문서 748건 필드 정상   ✓ 인용 766곳 참조 정상   ✓ 인물 258명 참조 정상   ✓ 편·순서 고유
  ✓ 문서 유형 사전 79항목   ✓ 사전 항목 완전   ✓ 소장처 목록 173곳   ✓ 소장처 항목 완전
  ✓ 도구 12종   ✓ 도구 이름 고유   ✓ readOnly · idempotent · openWorld 표시   ✓ 서버 instructions 있음
  ✓ X-Requested-With 미사용(방화벽 예절)   ✓ 정직 UA(13개 파일 검사)
  ✓ 데이터 지문 sha256 5fe988d21f83fdc0

전부 통과 21건
```

## 3. 엔드포인트 실측 — 19/19 PASS

```
$ python3 mcp/scripts/verify_endpoint.py --url http://127.0.0.1:3111/api/mcp --repeat 3
initialize: protocol=2025-06-18 · server=mcp-typescript server on vercel/0.1.0 · instructions=452자 · session_header=none(stateless)
tools/list: 12종
  - curation_search    desc  257자  readOnly=True idempotent=True openWorld=True
  - curation_item      desc  163자  readOnly=True idempotent=True openWorld=True
  - curation_episode   desc  133자  readOnly=True idempotent=True openWorld=True
  - curation_people    desc  116자  readOnly=True idempotent=True openWorld=True
  - curation_timeline  desc  107자  readOnly=True idempotent=True openWorld=True
  - curation_quotes    desc   88자  readOnly=True idempotent=True openWorld=True
  - doc_type           desc  138자  readOnly=True idempotent=True openWorld=True
  - curation_stats     desc  112자  readOnly=True idempotent=True openWorld=True
  - aks_catalog        desc  141자  readOnly=True idempotent=True openWorld=True
  - aks_find           desc  106자  readOnly=True idempotent=True openWorld=True
  - aks_manifest       desc  156자  readOnly=True idempotent=True openWorld=True
  - health             desc  102자  readOnly=True idempotent=True openWorld=True

점검                                                   결과         최대B      초   해시 비고
tools/list (12종 · readOnly/idempotent/openWorld · 설명 ≤1024자) PASS         0   0.01    1
curation_search("유관순") — 데이터에 없을 때 정직한 0건 안내         PASS       470   0.01    1
curation_search("송준길") — 번호 전 예시로 자동 확장              PASS      4074   0.01    1
curation_search("이언적")                               PASS      3388   0.01    1
curation_search(type="홍패", limit=5)                  PASS      2267   0.00    1
curation_search(query="혼인 납폐서")                      PASS       772   0.01    1
curation_item(id="EP.01#1")                          PASS      3138   0.00    1
curation_item(id=자료ID, part="reading")               PASS      2864   0.00    1
curation_episode("EP.124")                           PASS      2333   0.00    1
curation_people("최진립")                              PASS       499   0.00    1
curation_timeline(1592~1598)                         PASS      2010   0.00    1
curation_quotes("농사")                               PASS       822   0.01    1
doc_type("홍패")                                     PASS       443   0.00    1
curation_stats()                                     PASS      1704   0.00    1
aks_catalog(group="문중", region="경주")                 PASS      1870   0.00    1
aks_find("독락당")                                    PASS       242   0.00    1
health()                                             PASS       757   0.00    1
aks_manifest("경주 옥산 여주이씨 독락당", limit=10, pages=3)    PASS      3786  12.93    1
health(probe=true)                                   PASS       832   0.25    1

RESULT: PASS — 19/19건 · 같은 질의 3회 실행 바이트 일치(해시 1개)
```

`해시` 열이 1인 것은 같은 호출을 3번 했을 때 응답 해시가 **하나**였다는 뜻입니다(바이트 단위 동일).
`aks_manifest`는 실제 사이트에서 독락당 문서 1,166건을 읽어 왔습니다(12.9초 — 사이트 응답 시간에 종속).

## 4. 실제 MCP 클라이언트 점검 — 14/14

```
$ node mcp/scripts/client-check.mjs
  ✓ initialize — mcp-typescript server on vercel/0.1.0
  ✓ capabilities — tools=true
  ✓ tools/list 12종
  ✓ curation_search 1430B · 27ms      ✓ curation_item 2879B · 9ms
  ✓ curation_episode 1436B · 28ms     ✓ curation_people 415B · 6ms
  ✓ curation_timeline 399B · 8ms      ✓ curation_quotes 822B · 8ms
  ✓ doc_type 434B · 15ms              ✓ curation_stats 1704B · 17ms
  ✓ aks_catalog 1021B · 5ms           ✓ health 757B · 6ms
  ✓ 같은 질의 두 번 → 같은 응답

클라이언트 점검 전부 통과
```

## 5. 운영(Vercel) 배포 실측 — 2026-11-28

- 운영 주소: `https://archive-tools-mcp.vercel.app/api/mcp` (public, 인증 없음)
- 프로젝트: `changgis-projects-22902153/archive-tools-mcp` · 배포: `vercel deploy --prebuilt --prod` (GitHub Actions 러너 빌드)
- 첫 배포 run [46148701112](https://github.com/changgi/archive-tools/actions/runs/46148701112) → 실측 스텝이 **배포별 URL**을 찔러 401 (Deployment Protection) → 워크플로가 프로덕션 앨리어스를 보도록 고침(커밋 `6db0242`)
- 재배포 run [46148967573](https://github.com/changgi/archive-tools/actions/runs/46148967573) — **success**, 배포 직후 실측 **17/17 PASS**
- `mcp` CI run [46148922999](https://github.com/changgi/archive-tools/actions/runs/46148922999) — success (데이터셋 재생성 바이트 일치 · 정적 21 · 빌드 · 로컬 실측)

```
$ python3 mcp/scripts/verify_endpoint.py --url https://archive-tools-mcp.vercel.app/api/mcp --repeat 5
initialize            protocol=2025-06-18 · stateless(세션 헤더 없음)          PASS
tools/list            12종 · readOnly/idempotent/openWorld                     PASS
… (19개 호출 전부)                                                              PASS
aks_manifest("경주 옥산 여주이씨 독락당", limit=10, pages=3)   3786B · 4.30s    PASS
RESULT: PASS — 19/19건 · 같은 질의 5회 실행 바이트 일치(해시 1개)
```

```
$ node mcp/scripts/client-check.mjs https://archive-tools-mcp.vercel.app/api/mcp
  ✓ initialize — mcp-typescript server on vercel/0.1.0
  ✓ capabilities — tools=true
  ✓ tools/list 12종
  ✓ curation_search 1430B · 162ms      ✓ curation_item 2879B · 158ms
  ✓ curation_episode 1436B · 157ms     ✓ curation_people 415B · 158ms
  ✓ curation_timeline 399B · 156ms     ✓ curation_quotes 822B · 157ms
  ✓ doc_type 434B · 296ms              ✓ curation_stats 1704B · 160ms
  ✓ aks_catalog 1021B · 153ms          ✓ health 757B · 165ms
  ✓ 같은 질의 두 번 → 같은 응답

클라이언트 점검 전부 통과   (14/14)
```

- 함수 실행 리전: 서울 `icn1` (응답 헤더 `x-vercel-id: pdx1::icn1::…`). 같은 `aks_manifest`가 로컬 **12.9초 → 운영 4.3초**.
- Vercel 프로젝트 설정: Ignored Build Step = `Don’t build anything`(`exit 0`) · Functions CPU = `Standard`(1 vCPU · 2 GB) · Fluid compute 사용 · 빌드는 GitHub 러너에서만 하므로 Vercel 빌드 CPU를 쓰지 않습니다.
- **Deployment Protection**: 팀 기본값이 Vercel Authentication(Standard Protection)이라 `*-<hash>.vercel.app` 배포 URL은 로그인해야 열립니다. 프로덕션 도메인은 공개이므로 이 서버는 그대로 쓸 수 있고, 자동 점검도 앨리어스를 봅니다. 배포 URL을 외부에 안내할 때는 401이 나옵니다.

## 6. 아직 확인하지 못한 것

- Vercel 대시보드에서 별도 커스텀 도메인 연결은 하지 않았습니다(필요 없으면 그대로).
- `aks_*` 실시간 도구는 archive.aks.ac.kr 상태에 따라 느려지거나 실패할 수 있습니다(응답에 그대로 표시).
