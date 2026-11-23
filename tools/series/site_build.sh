# 예시 사이트 다시 만들기(순서 중요) → 점검 → 기록 꾸러미
#   bash tools/series/site_build.sh
set -e
CODE="$(cd "$(dirname "$0")" && pwd)"; REPO="${SERIES_REPO:-$(cd "$CODE/../.." && pwd)}"
S="$REPO/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts"
for s in gallery readme_ex analysis_build about_build share_apply seo_apply a11y_apply a11y_all en_build readme_stats; do
  echo "· $s"; python3 "$CODE/$s.py" | tail -1
done
echo "· media_offload"; python3 "$CODE/media_offload.py"
python3 "$S/studio.py" audit --in "$REPO/examples" --exclude tutorial --fail-on date,quote | tail -2
python3 "$CODE/record_build.py"
echo "· iiif_build (record.json 다음)"; python3 "$CODE/iiif_build.py" | tail -1
python3 "$REPO/tools/check_links.py" --all | tail -1
