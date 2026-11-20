# examples/en.html — 해외 기록·아카이브 관계자를 위한 영어 안내 한 장
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import json, sys, html
sys.path.insert(0, (P.REPO + '/plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts'))
import studio as ST, series as SE
R = (P.REPO + '/examples/'); B = 'https://changgi.github.io/archive-tools/examples/'
S = json.load(open((P.DATA + '/analysis_summary.json'), encoding='utf-8'))
D = json.load(open(R + 'analysis-data.json', encoding='utf-8'))
kinds = {'문중': 'lineage families', '서원': 'Confucian academies (seowon)', '마을': 'villages', '박물관': 'museums', '사찰': 'Buddhist temples', '향교': 'local Confucian schools (hyanggyo)'}
kind_line = 'Episodes by kind of holder: ' + ', '.join(f'{v} from {kinds.get(k, k)}' for k, v in D['kinds'])
import glob, csv, analysis as AN
RD = D.get('reading', {})
ALL = [r for f in glob.glob(R + '*/selection.csv') for r in csv.DictReader(open(f, encoding='utf-8-sig'))]
NREV = sum(1 for r in ALL if (r.get('검토') or '').strip()); NPEOPLE = len({p for r in ALL for p in AN.persons_of(r)})
cent = ', '.join(f'{c.replace("세기", "th c.")}: {n}' for c, n in D['centuries'])
e = html.escape
body = f'''<p class="k">ENGLISH OVERVIEW</p><h1>One Old Document at a Time<br><small style="font-size:.5em;color:#c4964a">고문서 한 장 · Gomunseo Han Jang</small></h1>
<p class="lead">A public series that reads Korean historical documents from the Academy of Korean Studies' <b>Korean Old Documents Archive</b> (한국고문서자료관, archive.aks.ac.kr) one sheet at a time — full transcription, modern Korean translation, explanatory notes, and a short story built on the document's own words — and turns each into a video, an online exhibition, a classroom worksheet and card news. The pages are in Korean; this page explains what is here.</p>
<div class="stats"><div><b>{S["eps"]}</b><span>episodes</span></div><div><b>{S["docs"]}</b><span>documents read</span></div><div><b>{S["colls"]}</b><span>holding collections</span></div><div><b>{S["span"][0]}–{S["span"][1]}</b><span>date range</span></div><div><b>{S["han"]:,}</b><span>Chinese characters transcribed</span></div><div><b>{S["quotes"]}</b><span>quoted source lines</span></div></div>
<h2>What you can explore</h2><div class="g">
<div class="box"><h3><a href="index.html">Gallery</a></h3><p>All episodes with Reels (9:16) and wide (16:9) videos with Korean subtitles. Open an episode for the full reading: transcription, translation, notes, editing before/after.</p></div>
<div class="box"><h3><a href="search.html">Full-text search</a></h3><p>Search all transcriptions, translations and notes — try a single Chinese character such as <a href="search.html?q=乘馹">乘馹</a> ("ride the post-horse").</p></div>
<div class="box"><h3><a href="analysis.html">Integrated analysis</a></h3><p>Documents by century ({e(cent)}), type, region, emotional framing, reading difficulty, quotations and questions. Data as <a href="analysis-data.json">JSON</a>, <a href="analysis-episodes.csv">CSV</a> and a <a href="data.zip">text-only ZIP</a>.</p></div>
<div class="box"><h3><a href="timeline.html">Timeline</a> · <a href="types.html">Document types</a></h3><p>Every dated document in one chronology, and a guide to {len(D["types"])} document types (appointment letters, exam diplomas, household registers, sale deeds, letters…) with how to read each.</p></div>
<div class="box"><h3><a href="people.html">People index</a></h3><p>{NPEOPLE} people named in the documents, in Korean alphabetical order — each with their documents, mentions in other episodes' translations and notes, and those who appear across several episodes.</p></div>
<div class="box"><h3><a href="quotes.html">Quoted lines</a> · <a href="questions.html">Questions</a></h3><p>Every source line quoted in the stories, searchable; and the open questions each episode leaves for readers, printable as discussion cards.</p></div>
<div class="box"><h3><a href="tutorial/site/index.html">Make your own</a></h3><p>The whole series was produced with an open-source Claude plugin, <b>aks-archive-harvester</b>: harvest → curate → edit → mediate → package. A step-by-step <a href="https://github.com/changgi/archive-tools/blob/main/examples/tutorial/README.md">tutorial</a> runs the full pipeline on three collections.</p></div>
<div class="box"><h3><a href="about.html">Curatorial note</a></h3><p>Why the series exists, how documents were chosen (a human voice in one line; diversity of collections, periods and status), the version history and the principles kept.</p></div></div>
<h2>Where the documents come from</h2><p>{e(kind_line)}, across {len([r for r, _ in D['regions'] if r not in ('기타', '여러 지역')])} provinces and cities of Korea. Each page links to the original images in the archive's viewer.</p>
<h2>Two kinds of editing</h2><p><b>Text editing</b> decides what to say: from an automatic draft caption to a story quoting the source as "modern Korean (original)". <b>Delivery editing</b> decides how, through what and where it reaches people — the core emotion, the opening, the climax line, material and sensory devices, channels, and a closing question — so that the same fact becomes a record people remember.</p>
<h2>How reliable is it — checks and review</h2><ul>
<li><b>Quotations</b>: all {RD.get('quotes_checked', S['quotes'])} source lines quoted in the stories are matched letter for letter against the transcription (omissions must be marked …) — {('mismatches: ' + str(len(RD.get('quote_issues', [])))) if RD.get('quote_issues') else 'all match'}.</li>
<li><b>Dates</b>: {RD.get('date_mentions', 0)} date expressions — Chinese and Japanese era names, Joseon reign years, the sexagenary (60-year) cycle and Western years — are cross-checked; {len(RD.get('date_issues', []))} disagreement(s), where the original itself is inconsistent and says so in the notes. Years that come from the archive's own dating rather than the document are labelled as such.</li>
<li><b>Human review</b>: {NREV} of {len(ALL)} documents have been compared with the original images so far. Anyone can help — tick the documents you checked on the <a href="review.html">review page</a> and send the downloaded <code>reviews.csv</code> as a GitHub issue. Until then every reading is marked as a draft.</li></ul>
<h2>How to cite</h2><p>For a single document, press <b>인용</b> (cite) next to any <a href="search.html">search</a> result: it copies the title, year, holding collection, archive item ID, viewer URL and your access date, plus a line naming this transcription and whether it has been reviewed. For the series and the tool, use the repository's <a href="https://github.com/changgi/archive-tools/blob/main/CITATION.cff">CITATION.cff</a> (GitHub: “Cite this repository”).</p>
<h2>Please note</h2><ul><li>Transcriptions and translations are drafts based on images; □ marks unread characters and (?) uncertain ones. Corrections are welcome through the <b>판독 고침 제보</b> (report a correction) buttons or <a href="https://github.com/changgi/archive-tools/issues/new/choose">GitHub issues</a>.</li>
<li>Images: courtesy of the Academy of Korean Studies, Korean Old Documents Archive, and each holding collection. Reuse requires the holder's consent via the archive (+82-31-730-8873, 8876). Items are taken down on request.</li>
<li>This is an independent project, not affiliated with the Academy of Korean Studies. Code is MIT-licensed; transcriptions, translations, notes and analysis data are <a href="https://github.com/changgi/archive-tools/blob/main/LICENSE-CONTENT.md">CC BY 4.0</a> (images excluded).</li></ul>
<p>Made by <b>Song Chang-gi</b> · chgsong@naver.com · <a href="https://github.com/changgi/archive-tools">github.com/changgi/archive-tools</a></p>'''
nav = '<nav class="top"><a href="index.html">한국어 갤러리</a><a href="search.html">Search</a><a href="analysis.html">Analysis</a><a href="timeline.html">Timeline</a><a href="people.html">People</a><a href="review.html">Review</a><a href="about.html">About (Korean)</a></nav>'
page = f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>One Old Document at a Time — Korean old documents, read line by line</title><link rel="alternate" hreflang="ko" href="{B}"><style>{SE.CSS}</style></head><body><main>{nav}{body}</main></body></html>'
page = ST.put_share(page, ST.share_meta('One Old Document at a Time — Korean historical documents, read line by line', f'{S["eps"]} episodes, {S["docs"]} documents ({S["span"][0]}–{S["span"][1]}) from the Korean Old Documents Archive: transcription, translation, videos, exhibitions, worksheets and an open-source Claude plugin.', B + 'media/share.jpg', B + 'en.html').replace('ko_KR', 'en_US'))
open(R + 'en.html', 'w', encoding='utf-8').write(page)
print('en ok')
