# 변경 기록

## aks-archive-harvester 0.2.0 (2026-11-14)
- curate: 문서명에서 연도·문서유형·인명/기관 자동 추출 → metadata.csv/jsonl, summary.md(유형·시기 분포, 인물별 연표)
- bundle: 연구 패키지(메타데이터·수집현황·CITATION·README·이미지 ZIP)
- batch / compare: 여러 소장처 일괄 수집·큐레이션, 소장처 간 문서유형×세기 비교표
- 스킬: 큐레이션 → 에디팅 → 매개 → 패키징 단계와 대량 유사 연구 절차 추가
- 시스템 인증서 저장소도 함께 신뢰하도록 SSL 처리 보강

## aks-archive-harvester 0.1.0 (2026-11-14)
- 첫 공개. treeAjax.do 재귀 탐색, imgnode.do 페이지 목록, DZI 원본 스티칭
- 이어받기, 시간 제한 실행, 서버 누락·저해상도 기록, 목록 CSV, 용량 분할 ZIP
- 동춘당 송준길 후손가(497건·5,274장)로 검증
