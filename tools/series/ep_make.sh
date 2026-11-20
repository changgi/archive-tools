# 한 편 만들기: data/new4/<작업>.json → 전시·카드(mediate) → 영상 → media·README → 노트·홍보·비하인드·검토지
#   bash tools/series/ep_make.sh <작업> [norender]
#   폴더 위치는 _paths.py와 같은 환경 변수(SERIES_DATA · SERIES_WORK …)로 바꿀 수 있음
set -e
CODE="$(cd "$(dirname "$0")" && pwd)"
cd "${SERIES_DATA:-$CODE/data}"
W=$1; J=new4/$W.json
ID=$(python3 -c "import json;print(json.load(open('$J',encoding='utf-8'))['meta']['id'])")
python3 "$CODE/new_eps.py" "$PWD/$J" mediate | tail -1
if [ "$2" != "norender" ]; then python3 "$CODE/showcase.py" "$ID.json" both > "logs_$ID.txt" 2>&1; tail -1 "logs_$ID.txt"; fi
python3 "$CODE/assemble_new.py" "$ID" | tail -1
python3 "$CODE/new4_post.py" "$W" | tail -1
python3 "$CODE/gallery.py" > /dev/null && python3 "$CODE/proof_build.py" "$W" | tail -1
