# 소장처 비교 — 6곳 1,229건 (문중 2 · 사찰 · 마을 · 서원 · 박물관)

- 🌐 [비교 리포트(그래프)](https://changgi.github.io/archive-tools/examples/compare/compare_report.html)
- [`compare_summary.md`](compare_summary.md): 문서유형·세기 비교표
- [`compare_metadata.csv`](compare_metadata.csv): 여섯 소장처를 합친 메타데이터 1,229건
- [`collections.tsv`](collections.tsv): `batch`·`compare`에 넣는 목록 파일 예시 (`harvest.py catalog --tsv`로 만들 수 있음)

```bash
python3 harvest.py batch --list collections.tsv --root R --step manifest
python3 harvest.py compare --list collections.tsv --root R
python3 studio.py report --root R
```

연도·유형은 문서명에서 자동 추출한 초안입니다.
