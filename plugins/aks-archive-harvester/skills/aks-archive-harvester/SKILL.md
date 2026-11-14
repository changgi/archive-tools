---
name: aks-archive-harvester
description: This skill should be used when the user wants to bulk-download every document image under a collection, family archive (문중·후손가), or category on the Academy of Korean Studies 한국고문서자료관 (archive.aks.ac.kr). Trigger phrases include "한국고문서자료관 다운로드", "archive.aks.ac.kr 전부 받아줘", "OO 후손가 하위 문서 모두 다운로드", "고문서 이미지 일괄 수집", "AKS 뷰어 원본 이미지 저장". Rebuilds original-resolution JPGs from DZI tiles, resumable, with missing/low-res logging and size-limited ZIP packing.
---

# AKS 한국고문서자료관 일괄 수집

The site has no download button. The viewer (`viewer.do`) shows images as OpenSeadragon DZI tiles. Collect the tree with `treeAjax.do`, the page list with `imgnode.do`, then fetch the highest-level tiles and stitch them into original-size JPGs.

Script: `${CLAUDE_PLUGIN_ROOT}/skills/aks-archive-harvester/scripts/harvest.py` (needs `requests` and `Pillow`). Site details: `references/site-structure.md`. Problems and fixes: `references/troubleshooting.md`.

## Workflow

### 1. Get the start node's `data-url`

Ask the user to open the target node in the viewer, or use the user's open viewer tab with Claude in Chrome. Run this in the page (it lists each tree node's ID, name and `data-url`):

```js
Array.from(document.querySelectorAll('li[data-dataid]')).filter(l=>!l.dataset.dataid.startsWith('G002'))
 .map(l=>l.dataset.dataid+' | '+(l.querySelector('span')||{}).textContent+' | '+l.getAttribute('data-url').replace(/&amp;/g,'&')).join('\n')
```

Output filters may block strings containing `?`, `=` or `&`. If so, replace them with tokens before returning (`.replace(/\?/g,' QM ').replace(/=/g,' EQ ').replace(/&/g,' AMP ')`) and restore them afterwards. Pick the row the user named (e.g. `L013001 | 대전 회덕 은진송씨 동춘당 송준길 후손가`).

### 2. Build the manifest and confirm the scale

```bash
python3 harvest.py manifest --work WORK --data-url '<data-url>' [--name 분류명]
```

Report the document and page counts per category. Estimate about 3MB and 2–4s per page at original size (pages around 4000×3000 are about 200 tiles each). Before a big download, confirm with AskUserQuestion: resolution (original, or offer a smaller first trial), packaging, and whether to start with one category.

### 3. Download in timed chunks (resumable)

```bash
python3 harvest.py download --work WORK [--category 교령류] --time 540
```

- Each run stops starting new pages after `--time` seconds. Re-run until it prints `STATUS: DONE`. Pages already saved are skipped.
- Keep the defaults (`--tile-workers 16 --page-workers 2`). Do not raise concurrency. The site has a web firewall, and this is a public research archive.
- If a run is killed (exit 137, out of memory on very long scrolls), re-run it. Lower `--page-workers` to 1 if it happens again.
- Never add an `X-Requested-With` header. The firewall blocks it.

### 4. Report and pack

```bash
python3 harvest.py report --work WORK --out 문서목록.csv
python3 harvest.py pack --work WORK --dest /mnt/user-data/outputs --prefix <소장처약칭> --max-mb 350
```

- The chat upload limit is 400MiB per file, so keep `--max-mb` at 350. Split parts carry document-number ranges (`part03of17_010-015`). One document may span two parts, so tell the user to extract all parts of a category into one folder.
- Free disk between categories by deleting `WORK/out/<분류>` after its ZIPs are delivered.
- Deliver ZIPs with SendUserFile in batches of about 10 files.

### 5. Final summary to the user

Include a table of category, documents, and pages received / total. Name the pages missing on the server (`missing.txt`) and the pages saved below original resolution (`partial.txt`). Missing pages do not exist on the server: they are not download failures, and the user can confirm them in the viewer.

## Output layout

```
WORK/docs.json                      # documents, pages, DZI paths
WORK/out/<분류>/<NNN>_<문서명>/<NNN>.jpg
WORK/missing.txt  WORK/partial.txt
```
