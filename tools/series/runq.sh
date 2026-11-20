# 편 대기열: (데이터 폴더의) q4.txt에서 한 줄씩 꺼내 ep_make.sh 실행, 결과는 q4_status.txt (비면 종료)
#   한 줄 = 작업 이름 [norender]
CODE="$(cd "$(dirname "$0")" && pwd)"; DATA="${SERIES_DATA:-$CODE/data}"; STATE="${SERIES_STATE:-$CODE/state}"; mkdir -p "$STATE"
cd "$DATA"
while true; do
  w=$(head -1 q4.txt 2>/dev/null); [ -z "$w" ] && exit 0
  sed -i '1d' q4.txt
  bash "$CODE/ep_make.sh" $w > "$STATE/ep_${w// /_}.log" 2>&1 && echo "OK $w" >> q4_status.txt || echo "FAIL $w" >> q4_status.txt
done
