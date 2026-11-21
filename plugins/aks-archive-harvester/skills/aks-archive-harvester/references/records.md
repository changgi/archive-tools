# 기록 꾸러미 — 산출물을 "현용기록"으로 남기기

`studio.py record`는 편 폴더(전시 · 카드 · 영상 · 판독표 …)마다 **record.json**과 **checksums.sha256**을 만듭니다.
산출물이 흩어져 퍼져 나가도 "이것이 무엇이고, 어디서 왔고, 누가 · 무엇으로 만들었고, 바뀌지 않았는가"를 스스로 말할 수 있게 하는 장치입니다.

> 비유: 병원의 **전자의무기록(EMR)** 은 진료 결과만이 아니라 누가 · 언제 · 무엇을 근거로 처방했는지를 함께 남깁니다.
> 회계 **원장**은 숫자만이 아니라 증빙 번호와 전표 이력을 함께 둡니다. 기록 꾸러미는 산출물에 그 "차트"와 "전표"를 붙이는 일입니다.

## 다섯 가지 성질과 담는 곳

| 성질 | 질문 | record.json에서 |
|---|---|---|
| 맥락 | 왜 · 어떤 묶음 안에서 만들었나 | `context`(시리즈 · 소장처 · 원 출처 · 만든 목적 · 공정), `relations`(앞 편 · 다음 편 · 속한 시리즈) |
| 증거성 | 원본은 무엇이고, 바뀌지 않았나 | `sources`(자료ID · 연도와 근거 · 뷰어 주소 · 검토 상태), `derivatives[].sha256`, `checksums.sha256` |
| 데이터화 | 기계가 읽을 수 있나 | JSON 한 파일 + 전체 목록 `records.jsonl` · Dublin Core `records-dc.csv` |
| 변환 · 확산 | 여러 매체로 퍼져도 같은 것임을 알 수 있나 | `derivatives[]`(역할 · 종류 · 형식 · 크기 · 고정값 — 전시 · 카드 · 릴스 · 자막 · 활동지 · 판독표 …) |
| 지속가능성 | 사람 · 도구가 바뀌어도 다시 만들고 확인할 수 있나 | `agents`(사람 · AI · 도구 버전), `events`(생성 · 수정 · 검증 · 검토 이력), `--verify` 대조, 제작 스크립트 공개 |

## 쓰는 법

```bash
# 만들기 — 편 폴더(selection.csv가 있는 곳)마다 record.json + checksums.sha256
python3 studio.py record --in <결과물 폴더> --media <영상 폴더> \
  --creator "이름" --agent "Claude (Anthropic)" \
  --license "<내가 정한 텍스트 라이선스>" --rights-images "<이미지 이용 조건 · 소장처 동의 문구>" \
  --index <폴더>/records          # records.jsonl · records-dc.csv 함께

# 대조 — 기록된 고정값과 지금 파일을 비교, 어긋나면 종료 코드 1 (CI에 넣기 좋음)
python3 studio.py record --verify --in <결과물 폴더> --media <영상 폴더>
```

- `--meta meta.json`: 폴더 이름을 열쇠로 `title · episode · series · collection · holder · purpose · previous · next`를 넘길 수 있습니다.
- `--date YYYY-MM-DD`: 기록 날짜를 고정(다시 만들어도 같은 결과가 나오게).
- `--media-remote 폴더 주소`: 영상처럼 큰 파일을 다른 저장소 · 서버로 옮겼을 때. 기록에는 공개 주소로 남고, 고정값은 그 폴더의 파일로 대조합니다. 내용(고정값)이 같은 채 자리만 옮기면 이력에 `migration`(옮김) 한 줄이 붙습니다 — 도서관이 책을 다른 서고로 옮기며 청구기호 옆에 '이관'을 적는 것과 같습니다.
- 바뀐 것이 없으면 `events`에 아무것도 더하지 않습니다. 파일이 바뀌면 "수정", 검토 칸이 새로 채워지면 "검토" 한 줄이 붙습니다.

## record.json 모양 (줄임)

```json
{
 "schema": "aks-record/1.0",
 "identifier": "series/folder", "title": "…", "episode": "EP.12",
 "context": {"series": "…", "collection": "…", "source_archive": "한국학중앙연구원 한국고문서자료관", "purpose": "…", "process": ["수집", "선별", "판독 · 번역 · 해제", "…", "사람 검토"]},
 "agents": [{"name": "…", "type": "person"}, {"name": "Claude (Anthropic)", "type": "software"}, {"name": "aks-archive-harvester 1.9.0", "type": "software"}],
 "sources": [{"identifier": "자료ID", "date": "1698", "date_basis": "자료관 목록", "source_url": "…", "review": "미검토"}],
 "derivatives": [{"path": "exhibit.html", "role": "전시 웹페이지", "format": "text/html", "bytes": 0, "sha256": "…"}],
 "validation": {"date_issues": 0, "quote_issues": 0},
 "review": {"status": "미검토", "reviewed": 0, "total": 3, "rule": "원본과 대조한 사람만 검토 칸을 채운다 — 도구와 AI는 검토를 표시하지 않는다"},
 "rights": {"text": "…", "images": "…"},
 "relations": {"is_part_of": "…", "previous": "…", "next": "…"},
 "events": [{"type": "creation", "date": "…", "agent": "…", "outcome": "…"}]
}
```

`events`는 디지털 보존 표준 PREMIS의 이벤트(생성 · 수정 · 고정값 검사)를 본떴고, `records-dc.csv`는 Dublin Core 15요소 가운데 쓰는 것만 채웁니다. 다른 목록 시스템으로 옮길 때 이 두 파일이 다리 역할을 합니다.

## 지켜야 할 것

- **검토는 사람만.** `review`는 selection.csv의 검토 칸을 셀 뿐이며, 도구와 AI는 그 칸을 채우지 않습니다. "날짜 · 인용 어긋남 0"은 규칙 통과이지 판독이 정확하다는 뜻이 아닙니다.
- **라이선스는 쓰는 사람이 정합니다.** `--license`를 비우면 비워 둡니다. 도구가 대신 고르지 않습니다.
- **이미지는 소장처의 것.** `--rights-images`에 이용 조건을 적으세요. 고문서 이미지를 다시 쓰려면 자료관을 통한 소장처 동의가 필요합니다.
- 고정값은 "바뀌지 않았다"를 증명할 뿐, "맞다"를 증명하지 않습니다. 고친 뒤에는 `record`를 다시 돌려 이력에 남기세요.
