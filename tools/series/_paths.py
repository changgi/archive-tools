"""「고문서 한 장」 시리즈 제작 도구의 폴더 위치 — 환경 변수로 바꿀 수 있다.

  SERIES_REPO   저장소(archive-tools) 위치        기본: 이 파일에서 두 단계 위
  SERIES_DATA   편 원고 · 렌더 설정 · 영상 원본     기본: tools/series/data
  SERIES_WORK   소장처 작업 폴더(harvest.py --work) 기본: tools/series/work   (저장소에 올리지 않음)
  SERIES_CAND   예전 후보 작업 폴더                기본: SERIES_WORK
  SERIES_STATE  원본 목록(collect.json) 등 상태     기본: tools/series/state  (저장소에 올리지 않음)
"""
import os, sys
CODE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.environ.get('SERIES_REPO') or os.path.join(CODE, '..', '..'))
DATA = os.path.abspath(os.environ.get('SERIES_DATA') or os.path.join(CODE, 'data'))
WORK = os.path.abspath(os.environ.get('SERIES_WORK') or os.path.join(CODE, 'work'))
CAND = os.path.abspath(os.environ.get('SERIES_CAND') or WORK)
STATE = os.path.abspath(os.environ.get('SERIES_STATE') or os.path.join(CODE, 'state'))
SCRIPTS = os.path.join(REPO, 'plugins', 'aks-archive-harvester', 'skills', 'aks-archive-harvester', 'scripts')
for _d in (CODE, SCRIPTS):
    if _d not in sys.path: sys.path.insert(0, _d)
os.makedirs(STATE, exist_ok=True)
