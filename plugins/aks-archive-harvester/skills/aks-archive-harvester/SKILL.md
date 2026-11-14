---
name: aks-archive-harvester
description: This skill should be used when the user wants to collect, curate, edit, mediate (exhibit web page, card news, lesson handout, SNS post) or package for comparative research the old documents of a family archive (문중·후손가), academy, temple or other collection on the Academy of Korean Studies 한국고문서자료관 (archive.aks.ac.kr), for one collection or many at once. Trigger phrases include "한국고문서자료관 다운로드", "OO 후손가 문서 전부 받아줘", "archive.aks.ac.kr 전부 받아줘", "문중 고문서 큐레이션", "고문서로 전시 만들어줘", "고문서 카드뉴스", "고문서 수업 자료", "여러 문중 비교 연구", "고문서 연구 패키지", "고문서 이미지 일괄 수집". Finds the collection by name, rebuilds original-resolution JPGs from DZI tiles, then curates, edits, mediates and packages.
---

# AKS 한국고문서자료관: 수집 → 큐레이션 → 에디팅 → 매개 → 패키징

Two scripts live in `${CLAUDE_PLUGIN_ROOT}/skills/aks-archive-harvester/scripts/`:

- `harvest.py` (needs `requests`, `Pillow`) handles finding, collecting, curation metadata, packaging and batch comparison.
- `studio.py` (needs `Pillow` only, works offline) handles curation themes, editing selections, mediation outputs and the comparison report.

Site internals: `references/site-structure.md`. Problems and fixes: `references/troubleshooting.md`.

Tell the user which stage you are in, using the five stage names, so the flow matches what they expect.

## ① 수집 (Collect)

**Find the collection by name.** No browser step is needed.

```bash
python3 harvest.py find "동춘당 송준길"                       # 후보 목록
python3 harvest.py find "동춘당 송준길" --manifest WORK        # 하나면 바로 목록 수집
```

- The first `find` builds a catalog of all collections (about 170, about 25 seconds) and caches it in `~/.aks-archive-catalog.json`. Use `--refresh` to rebuild it.
- If several collections match, show them and ask which one. Use `--first` only when the user's words clearly name one.
- If the user gives a viewer tab instead, the data-url can also come from the page. See `references/site-structure.md`.

**Confirm the scale, then download in timed chunks.**

```bash
python3 harvest.py manifest --work WORK --data-url '<data-url>'   # find --manifest가 이미 했으면 생략
python3 harvest.py download --work WORK [--category 교령류] --time 540
```

- Report documents and pages per category. Estimate about 3MB and 2–4s per page at original size.
- Before a large download, confirm with AskUserQuestion whether to take all pages or start with one category.
- Re-run `download` until it prints `STATUS: DONE`. Saved pages are skipped.
- Keep the defaults (`--tile-workers 16 --page-workers 2`). Never raise concurrency or add an `X-Requested-With` header; the site has a web firewall and is a public research archive.
- Exit 137 means out of memory on long scrolls. Re-run it, and use `--page-workers 1` if it happens again.
- Pages in `missing.txt` do not exist on the server. Pages in `partial.txt` were saved from a lower zoom level. Report both.

## ② 큐레이션 (Curate)

```bash
python3 harvest.py curate --work WORK --collection "<소장처 이름>"
python3 studio.py themes --work WORK
```

- `curate` writes `metadata.csv` / `metadata.jsonl` (year, document type, people/offices, pages, ID) and `summary.md` (type and period distribution, person timelines).
- `themes` proposes themes from the real distribution: a person's life, family life (혼인·호적), the path of office, a century, or a primer with one document per type.
- Show the user the theme list with counts and spans, and let them pick one or describe their own (person, types, years, keyword).
- Values come from document titles. Call them a draft.

## ③ 에디팅 (Edit)

```bash
python3 studio.py edit --work WORK --theme <id> [--count 9]
python3 studio.py edit --work WORK --person 송준길 --types 고신,유서 --years 1650-1680 --title "송준길의 관직 생애" --id songjungil
```

This picks representative documents spread across time and types, skips dark covers and blank pages, and keeps only one document per shared album. Single documents inside an album (첩) all get the album's full image set from the server, so the page for each cannot be known. Their captions say so (`공유이미지` column); never pair such a page with a specific document as if confirmed. It writes `WORK/edit/<id>/` with `selection.csv`, `images/` and `contact_sheet.jpg`.

Then edit as a curator:

1. Open `contact_sheet.jpg` and the selected images with Read. Swap documents that are weak or duplicated (re-run with other filters or `--count`).
2. In `selection.csv`, rewrite `캡션` and fill `이야기`: one or two sentences linking each document to the theme's story, in plain Korean for non-specialists.
3. Use only what the title, document type and visible image support. Do not present a transcription, translation or a person's biography as fact unless the user supplies or checks it.
4. Put `확인` in `검토` only for rows the user has confirmed. Unchecked rows are marked as drafts in every output.

## ④ 매개 (Mediate)

```bash
python3 studio.py mediate --work WORK --theme <id> [--lead "도입 문장"] [--font 한글글꼴.ttf]
```

This writes `WORK/mediate/<id>/`:

- `exhibit.html`: a single-file exhibition page with a timeline, images, captions and source. It prints as panels.
- `cards/`: card-news PNGs at 1080×1350 (cover, one per document, closing card).
- `handout.html`: an A4 lesson worksheet with "what is this document", "find it" and "think about it" prompts, plus a summary box.
- `sns.txt`: a post draft with hashtags.

The archive states that image use needs the collection owner's consent through its staff (031-730-8873, 8876).
- For anything the user will post publicly, offer `--placeholder`. It replaces each image with a box that links to the document in the archive viewer.
- Without it, outputs embed the downloaded images, which is fine for the user's own work.
- Examples: https://changgi.github.io/archive-tools/examples/

After it runs:

- Look at a few cards and screenshot `exhibit.html` before handing them over.
- Offer to publish `exhibit.html` as a page, or to send the cards.
- Every output cites 한국학중앙연구원 한국고문서자료관. Tell the user that reuse of the images follows the archive's terms.
- If the user has their own content skills (e.g. archive-fullpackage), offer them for a richer version built on `selection.csv`.

## ⑤ 패키징 (Package) + 대량 유사 연구

**One collection:**

```bash
python3 harvest.py report --work WORK --out 문서목록.csv
python3 harvest.py bundle --work WORK --dest OUT --prefix <약칭> [--no-images] [--max-mb 350]
```

`OUT/<약칭>_연구패키지/` holds metadata.csv/jsonl, summary.md, 수집현황.csv, CITATION.txt, README, `datapackage.json` (Frictionless Data descriptor), the `edit/` and `mediate/` results, and `images/` as split ZIPs. Another researcher can reuse or merge it.

- The chat upload limit is 400MiB, so keep `--max-mb` at 350.
- One document may span two parts. Tell the user to extract all parts of a category into one folder.

**Many collections (comparative research):**

```bash
python3 harvest.py catalog --group 문중 --region 충청 --tsv collections.tsv   # 후보 목록 파일 (불필요한 줄 삭제)
python3 harvest.py batch --list collections.tsv --root ROOT --step manifest    # 규모 확인
python3 harvest.py batch --list collections.tsv --root ROOT --step download    # 반복 실행 (이어받기)
python3 harvest.py batch --list collections.tsv --root ROOT --step curate
python3 harvest.py compare --list collections.tsv --root ROOT                  # compare_metadata.csv, compare_summary.md
python3 studio.py report --root ROOT                                           # compare_report.html (그래프)
```

- Confirm the total page count with the user before `download`. Many collections can take days.
- For metadata-only comparison, skip `download`. `curate` and `compare` need only `docs.json`.
- Propose comparative questions from the tables, e.g. how 고신 and 호구단자 shares differ between 문중 by century. Note that counts come from titles.

## Output layout

```
WORK/docs.json  out/<분류>/<NNN>_<문서명>/<NNN>.jpg  missing.txt  partial.txt   # ① 수집
WORK/metadata.csv  metadata.jsonl  summary.md  themes.json                     # ② 큐레이션
WORK/edit/<id>/selection.csv  images/  contact_sheet.jpg  theme.json           # ③ 에디팅
WORK/mediate/<id>/exhibit.html  cards/*.png  handout.html  sns.txt             # ④ 매개
OUT/<약칭>_연구패키지/   ROOT/compare_*.csv|md|html                              # ⑤ 패키징·비교
```
