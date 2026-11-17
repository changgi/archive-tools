# 공개 · 묶음 — 원본 묶음 · 영상 · 시리즈 사이트 · 통합 분석 · 모아 보기

SKILL.md ④에서 넘어오는 자세한 안내입니다.

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
- Writes `WORK/mediate/<id>/video/<base>_reel.mp4` · `_wide.mp4` · `.ko.srt` · `.ko.vtt`; `--web` adds 540p `_web.mp4` copies for web pages. Hand the full-resolution files to `originals --videos`. Run `mediate` again afterwards: the front page then gets video players with Korean subtitles (web copies preferred) and a 「자막 전문 읽기」 transcript for people who watch without sound or use screen readers.
- Look at one frame of each format before handing it over.
- Generated pages pass an automated WCAG 2 A/AA check (axe-core): keyboard-focusable scroll areas, visible focus, alt text on linked images, chart labels. Keep these when editing the templates.
- If narration fails it stops with a message instead of a traceback; retry with `--no-tts` or set `AKS_CA_BUNDLE`.

**Series site — `series.py`.** For several episodes:

```bash
python3 series.py --list series.tsv --note series.md --out SITE [--title "시리즈 제목"] [--text-license "CC BY 4.0"] [--home ../index.html --home-label "← 전체 갤러리"]
```

- `series.tsv`: a header line, then one line per episode — `ep<TAB>work<TAB>theme[<TAB>url]`. Work folders are found relative to the current folder or to the TSV's folder. Missing episodes are reported and skipped; videos: the `_web.mp4` copies when they exist, otherwise the full-size files (it warns about the size).
- `series.md`: the series note with headings (왜 만들었나 · 전하고 싶은 것 · 고른 기준 · 이렇게 보이길 바랐다 · 이렇게 써 주세요 · 지킨 원칙 · 히스토리). Same rule as curator notes: facts and the user's own intent only.
- Writes `SITE/index.html` (stats, 「이 사이트에 있는 것」 site map, four auto-summary lines, 결과물 바로 가기, episode grid with direct links), `analysis.html` (통합 분석, below), `about.html` (기획 노트 · per-episode message/emotion/question), `promote.html` (channels, 4-week plan), `use.html` (who can use the package and how, rights checklist), `cards/` (series cards from the note) and `eps/NN-<theme>/` copies (web videos only).

**Integrated analysis — `analysis.py` (통합 분석).** When the user wants to see the whole series at a glance ("전체를 통합 분석해줘", "한눈에 전체 콘텐츠"), `series.py` already writes `SITE/analysis.html`; standalone: `python3 analysis.py --list series.tsv --out analysis.html [--title …]` (optional 4th TSV column `kind`: 문중 · 서원 · 향교 · 사찰 · 마을 · 박물관 …).

- Sections: key numbers · auto-summary sentences (only computed facts) · documents by century and a year dot strip · document types and a type×century heatmap · collection kinds and regions (first place name → today's province) · 핵심 정서 words and chips · reading progress and hardest episodes (□ · (?)) · twelve quoted source lines spread across episodes · frequent names · 남겨 둔 질문 · one-line table per episode · limits of the analysis.
- The 「어디의 기록인가」 section adds a tile map of provinces (one square per 시·도, approximate positions). `series.py` also writes `data.zip` — every episode's selection.csv, curator.md, delivery.md, corrections.csv plus the analysis data and a 읽어보기.txt on sources and reuse (no images).
- Every chart has hover titles and a table view; the episode table has a search box. `analysis-data.json` (all counts, quotes, episodes) and `analysis-episodes.csv` are saved next to the page for classes and research. Read the summary before presenting it and keep its caveats: the figures describe the chosen documents, not the whole collection; dates, types and names are drafts extracted from titles.
- On a main page, show a few summary lines and link the analysis so first-time visitors see the whole at once.
- Collections (모아 보기), written next to the analysis: `search.html` (full-text search over 판독 · 원문 · 번역 · 해제 · 요약 · 이야기 with field filters and highlighted snippets; `?q=` opens a search), `types.html` (문서 유형 사전 — each document type with how to read it, count, centuries and examples from different episodes), `quotes.html` (every "현대어(原文)" quote, searchable), `timeline.html` (every dated document by century, with links to the episode and the archive viewer), `questions.html` (all 남겨 둔 질문 as cards that print two per row), `review.html` (검토 현황 — reviewed / remaining documents per episode). Analysis, collections and series pages have a light print style.
- Quotes are found by `studio.find_quotes`: a quotation that contains a parenthesis with Hanja or old Hangul counts, wherever the parenthesis sits ("…하오니(원문), 그 밖에 …") and in either order (원문(현대어) for old-Hangul letters); year parentheses like "(1646)" do not. `check`, `delivery`, `video.py` and the analysis share it.

- `--text-license` states the reuse terms for the texts the user made (판독 · 번역 · 해제 · notes · data) in every page footer and in `data.zip`'s 읽어보기. Ask the user; never choose a license for them. Images are never covered by it — they stay under the holding institution's consent.

**Accessibility (접근성) — every page the tools write.** All pages (exhibit · handout · episode index · proof sheet · series site · analysis · collections) pass through `studio.put_a11y` (via `put_oldhangul`), which is idempotent:

- a 「본문 바로가기」 skip link as the first focusable element (to the first heading after the menu, or to `main`) and a visible focus outline;
- exactly one `main`: notes added after it (큐레이터 노트 · 연출 노트 · 함께 고친 곳) are moved inside, and a page without `main` (the handout) gets one;
- regions with the same name are numbered (「원문 판독 1, 2 …」, 「표 1, 2 …」) and several menus get names (사이트 메뉴 · 이 페이지 차례);
- headings go down one level at a time (the handout's documents are `h2`, the timeline's centuries and the type dictionary's entries are `h2`).

`selftest.py` checks the skip link target, the single `main`, nothing outside it but footer/aside, and the heading order on every page it builds. For a browser check of a published site, `tools/check_a11y.js` in the repository runs axe-core (WCAG 2 A·AA + best practices) and fails on serious problems.

