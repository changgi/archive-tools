# 에디팅 도구 — 전달 에디팅 다시 쓰기 · 판독 고침 반영 · 옛한글 · 대표 면

SKILL.md ③·④에서 넘어오는 자세한 안내입니다.

**Redraft after 문구 에디팅 — `studio.py delivery`.** The first draft is written before the captions exist. Once `selection.csv` has stories with quoted source lines, run `python3 studio.py delivery --work WORK --theme <id> [--key "원문 한 줄"]` to rebuild the draft: the climax becomes the strongest "현대어(原文)" line and the closing becomes the curator note's question. Fields a person already wrote (핵심 정서 · 여운 장치 · 전달 에디팅 후) are kept unless `--force`; with `--force` the old file is saved as `delivery.bak.md`.

**Corrections — `studio.py fix` (판독 고침 반영).** When someone reports a misreading (the 「판독 고침 제보」 issue) or the user rereads a document:

```bash
python3 studio.py fix --work WORK --theme <id> --issue 12 --repo 아이디/저장소           # 제보 읽기: 문서 · 고칠 곳 · 고친 내용 · 근거
python3 studio.py fix --work WORK --theme <id> --n 3 --field 번역 --replace-part "초8일" --text "8일" --note "근거"   # 미리 보기
python3 studio.py fix … --apply        # 반영 → edit/<id>/corrections.csv(날짜 · 이전 · 이후 · 근거 · 제보)
python3 studio.py fix --work WORK --theme <id> --list
```

- It reads both the prefilled report from the buttons and the repository's issue form (`.github/ISSUE_TEMPLATE/correction.yml`); it finds the document by 자료 ID or, failing that, by its name, and reads "이전 → 이후" as a phrase replacement.
- Without `--apply` it only previews; it warns when the whole field would be replaced by a short text (use `--replace-part`). Check the original image before applying a reported reading; record the reason in `--note`.
- `mediate` then adds 「함께 고친 곳」 to `exhibit.html`, and `check` counts the corrections and flags outputs older than them.

**Old Hangul (옛한글).** When the texts contain old-Hangul jamo (ᄒᆞ, ᄉᆞ …), `mediate`, `series.py` and `analysis.py` add a small font subset (`assets/oldhangul-sans.woff2`, Noto Sans CJK KR, OFL) only for those characters, so 아래아 and other composed syllables look the same on every device. Card images need Pillow with libraqm for the same shaping.

**Representative page — `studio.py page`.** The first page of a document is sometimes a cover, a wrapper or the outside of a rolled scroll. `edit` already skips pages that are dark, or much smaller and emptier than the document's other pages, and `check` flags a representative page that still looks like one. `python3 studio.py page --work WORK --theme <id> --n <selection 번호> --page 002.jpg` swaps `images/NN.jpg` and the 원본경로 column to another page of the same document; re-run `mediate` and `video.py` afterwards.

**Proof and review — `studio.py proof` · `studio.py review` (검토지 · 검토 표시).**

```bash
python3 studio.py proof --work WORK --theme <id> [--all]          # edit/<id>/proof.html — 인쇄하면 한 장에 한 문서
python3 studio.py review --work WORK --theme <id> --n 1,3 --by 이름   # 검토 칸에 "이름 날짜" → 결과물의 「초안」 딱지가 빠짐
python3 studio.py review … --undo                                    # 표시 지우기
```

- The sheet shows the original page (or the representative image) beside 판독 · 번역 and the story's quoted lines, the count of □ · (?), check boxes (판독 · 번역 · 연도·인물 · 인용 원문 일치), reviewer and date lines and a box for corrections (줄 · 이전 → 이후 · 근거).
- Only unreviewed documents unless `--all`. Corrections go through `studio.py fix`; `review` is for documents a person has actually compared with the original — do not mark them on the user's behalf.
