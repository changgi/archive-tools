---
name: aks-archive-harvester
description: This skill should be used when the user wants to collect, curate, edit (with 해제·판독·내용요약 reading aids), mediate (exhibit web page, card news, lesson handout, SNS post, Reels promo copy) or package for comparative research the old documents of a family archive (문중·후손가), academy, temple or other collection on the Academy of Korean Studies 한국고문서자료관 (archive.aks.ac.kr), for one collection or many at once. Trigger phrases include "한국고문서자료관 다운로드", "OO 후손가 문서 전부 받아줘", "archive.aks.ac.kr 전부 받아줘", "문중 고문서 큐레이션", "고문서로 전시 만들어줘", "고문서 카드뉴스", "고문서 수업 자료", "여러 문중 비교 연구", "고문서 연구 패키지", "고문서 이미지 일괄 수집", "원본 사진 전부 줘", "문서 전체 다운로드", "고해상도 원본 영상", "영상 만들어줘", "릴스 영상", "시리즈 사이트", "대표 면 바꿔", "전달 에디팅", "큐레이터 노트", "처음부터 끝까지 만들어줘", "공개 전 점검해줘", "통합 분석", "전체를 한눈에", "설치 확인", "링크 미리 보기". Finds the collection by name, rebuilds original-resolution JPGs from DZI tiles, then curates, edits, mediates and packages.
---

# AKS 한국고문서자료관: 수집 → 큐레이션 → 에디팅 → 매개 → 패키징

Two scripts live in `${CLAUDE_PLUGIN_ROOT}/skills/aks-archive-harvester/scripts/`:

- `harvest.py` (needs `requests`, `Pillow`) handles finding, collecting, curation metadata, packaging and batch comparison.
- `studio.py` (needs `Pillow` only, works offline) handles curation themes, editing selections, mediation outputs and the comparison report.
- `video.py` (needs `ffmpeg`, `Pillow`; optional `edge-tts`) makes a Reels (9:16) and a wide (16:9) video with subtitles from one theme.
- `series.py` (needs `Pillow`) gathers several themes/episodes into one series site with a series note, promotion and use guides, and an integrated analysis.
- `analysis.py` (no extra needs) builds the integrated analysis page (통합 분석) of a whole series; `series.py` calls it.
- `selftest.py` checks an installation offline: it builds three fake documents in a temporary folder and runs every step (`--video` adds video). Run it first when a user reports that something does not work, or after installing on a new computer.

## Full pipeline checklist (처음부터 끝까지)

A worked example of every step, with the auto drafts and the edited results side by side: `examples/tutorial/` in the repository (https://changgi.github.io/archive-tools/examples/tutorial/site/index.html, guide in `examples/tutorial/README.md`). When the user asks for "everything", go in this order and show the user the result of steps 4–6 before making media:

| # | step | command | who |
|---|---|---|---|
| 1 | find + page list only for matching documents | `harvest.py find "<소장처>" --first --manifest W --match "<문서명 정규식>"` | tool |
| 2 | download | `harvest.py download --work W --match "…"` (repeat until `STATUS: DONE`) | tool |
| 3 | curate + drafts | `harvest.py curate --work W` → `studio.py edit --work W --all --id <id>` (or `--theme`) | tool |
| 4 | 문구 에디팅 | read the images; fill 판독 · 번역 · 해제 · 요약 · 이야기("현대어(原文)") in `selection.csv` | Claude + user |
| 5 | 큐레이터 노트 | fill `curator.md` (six headings) — facts only, intent confirmed by the user | Claude + user |
| 6 | 전달 에디팅 | `studio.py delivery --work W --theme <id>` (redraft after step 4: climax line, closing question) → refine `delivery.md` | tool → Claude + user |
| 6b | readiness check | `studio.py check --work W --theme <id>` — empty fields, stories without "현대어(原文)" quotes, cover-like representative pages, outputs older than their notes → numbered next steps (`--strict` exits 1 while anything is left) | tool |
| 6a | representative page | `studio.py page --work W --theme <id> --n 1 --page 002.jpg` when page 1 is a cover/rolled scroll | user choice |
| 7 | promo, then mediate | `studio.py promo … --ep N --url <exhibit URL>` → `studio.py mediate --work W --theme <id> --url <exhibit URL>` | tool |
| 8 | video | `video.py --work W --theme <id> --ep N --url <exhibit URL> --web` | tool |
| 9 | originals | `studio.py originals … --full --dry-run` → `--full --videos W/mediate/<id>/video` | tool |
| 10 | series | `series.py --list series.tsv --note series.md --out site` | tool |

Run `studio.py check` before steps 7–10 and again before handing anything over; follow its 다음 할 일 list. Run `promo` before `mediate` so the 홍보 글 tile appears on the front page. Pass the public address (`mediate --url`, `series.py --site-url`) so every page carries link-preview tags and a 1200×630 `share.jpg` — what KakaoTalk, Facebook, X and Threads show when the link is pasted. Re-running `mediate` is safe: injected blocks are replaced, not duplicated.

Site internals: `references/site-structure.md`. Problems and fixes: `references/troubleshooting.md`. Reading old documents (full transcription, zoom, formats): `references/reading-aid.md`. Storytelling from the sources: `references/storytelling.md`. Reels copy template: `references/reels-caption.md`. Channel-by-channel promotion and second-wave (behind) materials: `references/channels.md`. What people can do with the package: `references/package-uses.md`.

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
- For a large collection (thousands of documents), fetch names first and page lists only for what you need: `find "이름" --manifest WORK --tree-only` (names only, fast), look at the names, then `manifest --work WORK --data-url '<data-url>' --match "유지|소지|명문"` fetches page lists only for matching documents (earlier ones are kept). If every sampled document returns no images, the collection has no published images; pick another.
- For a large collection where the user wants one theme, download only matching documents: `download --work WORK --match "상량문|양안|완문"`. Add `--pages 3` to take only the first pages of each document (enough to find where the text starts in a book). Without `--pages`, `download` takes **every page** of each matching document; to fill in the rest later for the documents you selected, use `studio.py originals --full` (below).
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

Use `--all` to select from every document whose images were downloaded (after `download --match`). This picks representative documents spread across time and types, skips dark covers and blank pages, and keeps only one document per shared album. Single documents inside an album (첩) all get the album's full image set from the server, so the page for each cannot be known. Their captions say so (`공유이미지` column); never pair such a page with a specific document as if confirmed. It writes `WORK/edit/<id>/` with `selection.csv`, `images/` and `contact_sheet.jpg`.

Then edit as a curator:

1. Open `contact_sheet.jpg` and the selected images with Read. Swap documents that are weak or duplicated (re-run with other filters or `--count`).
2. Read first, then tell (step 3 before step 2 in practice). In `selection.csv`, rewrite `캡션` and fill `이야기` **from what the documents actually say**, not from their titles. Do not list documents ("1665년 고신, 1668년 유지…"); tell the story the texts themselves carry, and let the source speak: in each `이야기` quote one short phrase of the original with its meaning, in the form "현대어 풀이(原文)", e.g. "농사와 누에치기를 권해 우리 백성을 입히고 먹이라(課農桑以衣食吾民)". Open the series with a question, follow the documents in time order, connect each one to the next (who, what changed, why it mattered), and close with one line on what the record means. Prefer documents with substantial text (petitions, letters, royal edicts, contracts, prefaces) over covers and formulaic one-liners; choose the pages where the text is. Reorder rows to follow the story. See `references/storytelling.md`.
3. Fill the reading aid for every row, because most viewers cannot read old hanja, idu, cursive script (초서) or old Korean letters (언간). Read each image with Read (crop or zoom where the text is small), then write:
   - `원문`: the **full transcription of the whole text** — every line of every page you show, not a sample. If the document has several pages (`download --pages N` or all pages), run `zoom --all-pages` and transcribe each page in order with a "(2쪽)" marker. If a page is only a cover, say "(표지)" and transcribe the next page that carries the text. Transcription is line by line in the original column order (right to left for vertical text), one source line per output line. Transcribe everything legible, not a summary: heading, body, date, names, small notes beside the date, seals, endorsements (題辭), envelope. Run `python3 studio.py zoom --work WORK --theme <id>` first and read every tile in order (`c1` is the rightmost); for small or cursive text crop further with PIL until each character is clear. Use □ per unreadable character, (?) after an uncertain one, (…) where the line runs off the image or is cut, and (괄호) for notes like (도장), (작은 글씨), (겉봉). For 언간 keep the old spelling (ᄒᆞ, ᄋᆞ) and do not modernize. If only part of a long book page can be read, say which part, e.g. "(오른쪽 면만 판독)".
   - `번역`: a **full modern-Korean translation of `원문`**, sentence by sentence, keeping the order; explain idu (이두) and formula words in brackets; keep (…) where the source is cut. A transcription without its translation is not finished.
   - Hanja in `원문` are shown with their Korean reading above each character (ruby) automatically in the exhibit page and handout when the `hanja` package is installed (`pip install hanja`); check readings of idu and names, which the dictionary may get wrong.
   - `판독`: the key characters you actually read (heading, name, office, date, seal text). Use □ for characters you cannot read and add "(판독 불확실)" when unsure. If nothing is legible, write a note in parentheses such as "(흘림 글씨 — 판독 필요)".
   - `해제`: when, who, to whom, what kind of document, and how to read its format. `edit` pre-fills a draft from the document type; correct it with what the image shows (era name → Western year, issuer, idu words).
   - `요약`: the content in plain modern Korean, a few sentences. For formulaic documents (고신, 교지, 유지, 홍패, 추증교지, 명문, 고목) translate the formula fully; for long texts summarize only what you read and say what needs reading.
   - Point out where the image contradicts the title (e.g. a different recipient on the envelope) instead of hiding it.
   See `references/reading-aid.md` for document formats, idu words and examples.
4. Use only what the title, document type and visible image support. Do not present a transcription, translation or a person's biography as fact unless the user supplies or checks it.
5. Put `확인` in `검토` only for rows the user has confirmed. Unchecked rows are marked as drafts in every output.

## ④ 매개 (Mediate)

```bash
python3 studio.py mediate --work WORK --theme <id> [--lead "도입 문장"] [--font 한글글꼴.ttf]
```

This writes `WORK/mediate/<id>/`:

- `exhibit.html`: a single-file exhibition page with a timeline, images, captions, a 「읽기 도움」 box (해제 · 원문 읽기 · 내용 요약) and source. It prints as panels.
- `cards/`: card-news PNGs at 1080×1350 (cover, one per document, closing card).
- `handout.html`: an A4 lesson worksheet with 해제 ("what is this document"), 내용 요약, the characters to find in the image (from `판독`), "find it" and "think about it" prompts, plus a summary box.
- `sns.txt`: a post draft with hashtags.
- `index.html`: the front page — 「결과물 한눈에 보기」. One tile per output (전시 · 활동지 · 카드뉴스 · SNS 글 · CSV · 홍보 문구) with a direct link, a card strip and the document list, so a first-time visitor sees at a glance what exists and opens it in one click. When you publish several themes or episodes together (e.g. a gallery), put the same direct links on the main page too, not only inside detail views.

The archive states that image use needs the collection owner's consent through its staff (031-730-8873, 8876).
- For anything the user will post publicly, offer `--placeholder`. It replaces each image with a box that links to the document in the archive viewer.
- Without it, outputs embed the downloaded images, which is fine for the user's own work.
- Examples: https://changgi.github.io/archive-tools/examples/

**Two kinds of editing — 문구 에디팅 and 전달 에디팅.** Editing the captions and stories in `selection.csv` is 문구 에디팅 (what to say). After it, do 전달 에디팅 (how, through what and where to deliver the chosen records): `edit` writes `edit/<id>/delivery.md` with a draft from `delivery_draft` — 핵심 정서 · 한 문장 · 열기 · 펼치기 · 절정(the source line to stop on) · 여운 · 감각과 물질(by document type: 붉은 홍패 실물 크기, 탁본, 낭독, 조명 …) · 통로와 매개 · 여운 장치 · 전달 에디팅 전/후. Refine it so each record leaves a feeling, not only a fact; ask the user about the venue and audience when they matter. `mediate` adds it as 「연출 노트」 to `exhibit.html` and `index.html`. Guide: `references/delivery-editing.md`. Treat sensitive records (famine, slavery, self-sale, punishment) with dignity first.

**Redraft after 문구 에디팅 — `studio.py delivery`.** The first draft is written before the captions exist. Once `selection.csv` has stories with quoted source lines, run `python3 studio.py delivery --work WORK --theme <id> [--key "원문 한 줄"]` to rebuild the draft: the climax becomes the strongest "현대어(原文)" line and the closing becomes the curator note's question. Fields a person already wrote (핵심 정서 · 여운 장치 · 전달 에디팅 후) are kept unless `--force`; with `--force` the old file is saved as `delivery.bak.md`.

**Representative page — `studio.py page`.** The first page of a document is sometimes a cover, a wrapper or the outside of a rolled scroll. `edit` already skips pages that are dark, or much smaller and emptier than the document's other pages, and `check` flags a representative page that still looks like one. `python3 studio.py page --work WORK --theme <id> --n <selection 번호> --page 002.jpg` swaps `images/NN.jpg` and the 원본경로 column to another page of the same document; re-run `mediate` and `video.py` afterwards.

**Curator note (큐레이터 노트 — 기획 의도 · 비하인드).** `edit` writes `edit/<id>/curator.md` with six headings. Fill it before `mediate`, because people want to know why these documents were chosen and what the work hopes to say, not only what the documents read:

| heading | what to write |
|---|---|
| 왜 이 문서들인가 | why these documents out of the whole collection — the line or fact that caught your eye |
| 전하고 싶은 것 | the one thing a viewer should take away (one or two sentences) |
| 이렇게 보이길 바랐다 | how the order, quotations and scenes were arranged, and the feeling you aimed for |
| 이렇게 써 주세요 | how to use the outputs in class, exhibitions, research or SNS |
| 만들며 있었던 일 | what actually happened while making it — unread parts, changed decisions, missing images, points that need checking |
| 남겨 둔 질문 | a question the documents cannot answer, to share with viewers |

- Write only what the documents and the work actually show. Ask the user for their own intent when it is theirs to state; never invent motives, events or facts for the 비하인드. Leave a heading empty rather than pad it.
- `mediate` then adds 「큐레이터 노트」 to the end of `exhibit.html` (with a link in the header), a 「선생님께」 box (왜 · 전하고 싶은 것 · 쓰는 법 · 질문) to `handout.html`, and a tile and section to `index.html`, plus an automatic 제작 기록 line (문서 수 · 연대 · 받은 면 · 판독/번역 수 · □/(?) 수 · "확인 필요" 수). `promo` adds a "✍️ 큐레이터 노트 — …" block from 전하고 싶은 것.
- For a series of several themes or episodes, also write one series note (why the series, how documents were chosen, history of versions, principles, how to use, request for corrections) and link it from the main page.

**2차 홍보 (비하인드) · 채널별 홍보안 · 활용 안내.** With a filled `curator.md`, `mediate` also writes three behind cards (`cards/b1_전하고싶은것`, `b2_만들며있었던일`, `b3_남겨둔질문`) and `channels.md` — a table of channels (Instagram feed·Reels, YouTube Shorts·long-form, TikTok, Facebook, Threads, X, blog·newsletter, online and offline exhibitions, classes, books, fiction, webtoon, film·drama, ads·brand, podcast) with format, files to use, copy formula and metric, plus ready-to-post drafts and expansion ideas. Pass `--url` so the drafts carry the public link. Polish the drafts with `references/channels.md`. When handing a package to others, include `references/package-uses.md` (who can do what, value-adding paths, rights and ethics checklist). For a series, make series-level behind Reels and cards only from facts in the series note, CHANGELOG and curator notes.

**Reels promo copy (「고문서 한 장」 format).** When the user wants a post for Reels/Shorts/Instagram:

```bash
python3 studio.py promo --work WORK --theme <id> --ep <번호> --url <전시 웹페이지 주소>
```

This writes `mediate/<id>/promo.md` with the fixed lines filled in and [bracketed] slots. Fill the slots from `selection.csv` (이야기·해제·요약), keep one blank line between blocks exactly as in `references/reels-caption.md`, and never claim more than the documents show.

After it runs:

- Look at a few cards and screenshot `exhibit.html` before handing them over.
- Offer to publish `exhibit.html` as a page, or to send the cards.
- Every output cites 한국학중앙연구원 한국고문서자료관. Tell the user that reuse of the images follows the archive's terms.
- If the user has their own content skills (e.g. archive-fullpackage), offer them for a richer version built on `selection.csv`.

**Originals for the user (원본 묶음 — 문서 전체 + 원본 영상).** When the user asks for the high-resolution originals, the photos of each record, or the whole document (문서 전체), not only the pages shown in the outputs:

```bash
python3 studio.py originals --work WORK --theme <id> --full --dry-run          # 문서별 전체 면 수 먼저 확인
python3 studio.py originals --work WORK --theme <id> --full [--videos 영상폴더] [--max-mb 380]
```

- `--full` downloads every page of each selected document (already saved pages are skipped; it runs `manifest --match` first if the page list is missing, then `download --match` round after round until `STATUS: DONE`). It keeps the default connection counts; never raise them, and never run two manifests at once.
- Use `--dry-run` first and tell the user the page count when a document is a long book (e.g. a 90-page 녹권), then ask whether to take all of it or `--only 1,3`.
- `--videos` adds the original-resolution videos and subtitles (mp4 · srt · vtt) from a folder — the files before any web compression.
- It writes `WORK/originals/<id>/<소장처>_원본[_partNNofMM].zip`, stored (not recompressed), each under `--max-mb`: `기록사진/NN_문서명/001.jpg…`, `기록사진/출처.csv` (문서명 · 받은 면 · 전체 면 · 자료관 원본 뷰어 링크), `영상/…`, and `읽어보기_출처와이용조건.txt` (credit line, the consent-needed notice with the archive's phone numbers, and "문제가 있으면 바로 내림").
- Without `--full` it bundles only the pages already downloaded and says how many pages are missing.
- Deliver the ZIPs as they are, and repeat the reuse terms in your reply: the images may be redistributed only with the holding institution's consent through the archive.

**Video — `video.py`.**

```bash
python3 video.py --work WORK --theme <id> [--ep 7] [--url 전시주소] [--format both|reel|wide] [--no-tts] [--web]
```

- Scenes: opener (전달 에디팅 열기) → introduction → one scene per document with its image and quoted source line → climax → 비하인드 (큐레이터 노트 전하고 싶은 것) → closing question with source.
- Narration uses edge-tts when installed (`--voice ko-KR-SunHiNeural`); otherwise a silent video timed by text length. Behind a proxy with its own certificate, set `AKS_CA_BUNDLE=<ca file>`.
- Writes `WORK/mediate/<id>/video/<base>_reel.mp4` · `_wide.mp4` · `.ko.srt` · `.ko.vtt`; `--web` adds 540p `_web.mp4` copies for web pages. Hand the full-resolution files to `originals --videos`. Run `mediate` again afterwards: the front page then gets video players with Korean subtitles (web copies preferred).
- Look at one frame of each format before handing it over.
- If narration fails it stops with a message instead of a traceback; retry with `--no-tts` or set `AKS_CA_BUNDLE`.

**Series site — `series.py`.** For several episodes:

```bash
python3 series.py --list series.tsv --note series.md --out SITE [--title "시리즈 제목"] [--home ../index.html --home-label "← 전체 갤러리"]
```

- `series.tsv`: a header line, then one line per episode — `ep<TAB>work<TAB>theme[<TAB>url]`. Work folders are found relative to the current folder or to the TSV's folder. Missing episodes are reported and skipped; videos: the `_web.mp4` copies when they exist, otherwise the full-size files (it warns about the size).
- `series.md`: the series note with headings (왜 만들었나 · 전하고 싶은 것 · 고른 기준 · 이렇게 보이길 바랐다 · 이렇게 써 주세요 · 지킨 원칙 · 히스토리). Same rule as curator notes: facts and the user's own intent only.
- Writes `SITE/index.html` (stats, 「이 사이트에 있는 것」 site map, four auto-summary lines, 결과물 바로 가기, episode grid with direct links), `analysis.html` (통합 분석, below), `about.html` (기획 노트 · per-episode message/emotion/question), `promote.html` (channels, 4-week plan), `use.html` (who can use the package and how, rights checklist), `cards/` (series cards from the note) and `eps/NN-<theme>/` copies (web videos only).

**Integrated analysis — `analysis.py` (통합 분석).** When the user wants to see the whole series at a glance ("전체를 통합 분석해줘", "한눈에 전체 콘텐츠"), `series.py` already writes `SITE/analysis.html`; standalone: `python3 analysis.py --list series.tsv --out analysis.html [--title …]` (optional 4th TSV column `kind`: 문중 · 서원 · 향교 · 사찰 · 마을 · 박물관 …).

- Sections: key numbers · auto-summary sentences (only computed facts) · documents by century and a year dot strip · document types and a type×century heatmap · collection kinds and regions (first place name → today's province) · 핵심 정서 words and chips · reading progress and hardest episodes (□ · (?)) · twelve quoted source lines spread across episodes · frequent names · 남겨 둔 질문 · one-line table per episode · limits of the analysis.
- Every chart has hover titles and a table view; the episode table has a search box. `analysis-data.json` (all counts, quotes, episodes) and `analysis-episodes.csv` are saved next to the page for classes and research. Read the summary before presenting it and keep its caveats: the figures describe the chosen documents, not the whole collection; dates, types and names are drafts extracted from titles.
- On a main page, show a few summary lines and link the analysis so first-time visitors see the whole at once.

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
WORK/edit/<id>/curator.md   # 큐레이터 노트(기획 의도 · 비하인드)
WORK/edit/<id>/delivery.md  # 전달 에디팅(정서 · 장면 · 물질 · 통로 · 매개)
WORK/mediate/<id>/index.html  exhibit.html  channels.md  cards/*.png(b1–b3 비하인드)  handout.html  sns.txt  promo.md   # ④ 매개
WORK/mediate/<id>/video/<base>_reel.mp4  _wide.mp4  .ko.srt  (_web.mp4)   # 영상
WORK/originals/<id>/<소장처>_원본*.zip   # 원본 묶음(문서 전체 면 · 원본 영상 · 출처.csv)
SITE/index.html  about.html  promote.html  use.html  analysis.html  cards/  eps/   # 시리즈 사이트 · 통합 분석
OUT/<약칭>_연구패키지/   ROOT/compare_*.csv|md|html                              # ⑤ 패키징·비교
```
