// 큐레이션 데이터셋(「고문서 한 장」 200편 · 726건) 로더와 결정론적 검색.
// 데이터는 저장소의 실제 산출물(examples/<편>/selection.csv · record.json · analysis-data.json)에서
// scripts/build_dataset.py 가 만든 mcp/data/*.json 뿐이다 — 이 파일은 그 파일들만 읽는다.
// (번들에 넣지 않고 파일로 읽는다 — next.config.mjs 의 outputFileTracingIncludes 가 함수에 함께 싣는다)
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

const readData = (name) => JSON.parse(fs.readFileSync(path.join(process.cwd(), 'data', name), 'utf8'));

const CURATION = readData('curation.json');
const GLOSSARY = readData('glossary.json');
const CATALOG = readData('aks_catalog.json');

export const GALLERY = 'https://changgi.github.io/archive-tools/examples';

export const DATA = CURATION;
export const DOCS = CURATION.docs;
export const EPISODES = CURATION.episodes;
export const GLOSSARY_TERMS = GLOSSARY.glossary;
export const READ_GUIDE = GLOSSARY.read_guide;
export const CATALOG_COLLECTIONS = CATALOG.collections;
export { CATALOG };

// 데이터 지문 — 같은 데이터면 언제나 같은 값(헬스체크·재현 확인용)
export const DATASET_SHA256 = createHash('sha256').update(JSON.stringify(CURATION)).digest('hex');

const norm = (s) => String(s == null ? '' : s).normalize('NFC').toLowerCase();
const squash = (s) => norm(s).replace(/[\s\u00a0]+/g, '');

// 문서마다 한 번만 만드는 검색용 문자열(필드 가중치 순서 = 배열 순서)
const WEIGHTS = [
  ['title', 6],
  ['persons', 5],
  ['type', 4],
  ['reading', 3], // 판독 · 원문
  ['note', 2], // 해제 · 요약
  ['text', 1], // 이야기 · 번역 · 캡션
];
const HAY = DOCS.map((d) => {
  const persons = (d.persons || []).join(' ');
  return {
    title: norm(d.title),
    persons: norm(persons),
    type: norm(d.type),
    reading: norm([d.read, d.original].filter(Boolean).join('\n')),
    note: norm([d.note, d.summary].filter(Boolean).join('\n')),
    text: norm([d.story, d.translation, d.caption].filter(Boolean).join('\n')),
    all: squash([d.title, persons, d.type, d.read, d.original, d.note, d.summary, d.story, d.translation, d.caption, d.ep, d.slug].filter(Boolean).join('\n')),
  };
});

const EP_BY_SLUG = new Map(EPISODES.map((e) => [e.slug, e]));
const EP_BY_N = new Map(EPISODES.filter((e) => e.n).map((e) => [e.n, e]));
const PEOPLE = new Map(CURATION.people.map(([name, idx]) => [name, idx]));

const epStamp = (d) => (d.ep ? Number(String(d.ep).replace(/\D/g, '')) : 9999);

export function episodeOf(doc) {
  return EP_BY_SLUG.get(doc.slug) || null;
}

export function episodeByKey(key) {
  const s = String(key == null ? '' : key).trim();
  if (!s) return null;
  const n = s.match(/^(?:ep\.?\s*)?(\d{1,3})$/i);
  if (n) return EP_BY_N.get(Number(n[1])) || null;
  if (EP_BY_SLUG.has(s)) return EP_BY_SLUG.get(s);
  const lower = s.toLowerCase();
  return EPISODES.find((e) => e.slug.toLowerCase() === lower || e.title.includes(s)) || null;
}

function tokensOf(q) {
  return norm(q).split(/[\s,]+/).filter(Boolean).map(squash).filter(Boolean);
}

function scoreDoc(i, toks, needAll) {
  const h = HAY[i];
  let score = 0;
  for (const t of toks) {
    let best = 0;
    for (const [field, w] of WEIGHTS) {
      if (h[field].includes(t)) {
        best = w;
        break;
      }
    }
    if (!best && h.all.includes(t)) best = 0.5;
    if (!best) {
      if (needAll) return 0;
      continue;
    }
    score += best;
  }
  return score;
}

// 문서 정렬: 점수 → 연도 → 편 → 순서 → 자료ID (모두 고정값이라 같은 질의는 같은 순서)
const byRank = (q) => (a, b) => q[b].score - q[a].score
  || (DOCS[a].year || 9999) - (DOCS[b].year || 9999)
  || epStamp(DOCS[a]) - epStamp(DOCS[b])
  || DOCS[a].o - DOCS[b].o
  || DOCS[a].id.localeCompare(DOCS[b].id);

export function searchDocs({ query = '', type = '', person = '', yearFrom = null, yearTo = null, episode = null, scope = 'series', limit = 8 }) {
  const toks = tokensOf(query);
  const ep = episode ? episodeByKey(episode) : null;
  const pass = (i) => {
    const d = DOCS[i];
    if (scope === 'series' && !d.ep) return false;
    if (ep && d.slug !== ep.slug) return false;
    if (type && !norm(d.type).includes(norm(type))) return false;
    if (person) {
      const p = norm(person);
      const listed = (d.persons || []).some((x) => norm(x).includes(p) || squash(x).includes(squash(person)));
      if (!listed && !HAY[i].note.includes(p) && !HAY[i].text.includes(p)) return false;
    }
    if (yearFrom != null || yearTo != null) {
      const y = d.year;
      if (!y) return false;
      if (yearFrom != null && y < yearFrom) return false;
      if (yearTo != null && y > yearTo) return false;
    }
    return true;
  };
  const candidates = [];
  for (let i = 0; i < DOCS.length; i++) if (pass(i)) candidates.push(i);
  if (!toks.length) {
    const q = {};
    for (const i of candidates) q[i] = { score: 1 };
    return { hits: candidates.sort(byRank(q)).slice(0, limit), total: candidates.length, mode: 'filter' };
  }
  const q = {};
  let matched = 0;
  for (const i of candidates) {
    const s = scoreDoc(i, toks, true);
    if (s > 0) {
      q[i] = { score: s + 1 };
      matched++;
    }
  }
  if (matched) return { hits: Object.keys(q).map(Number).sort(byRank(q)).slice(0, limit), total: matched, mode: 'all' };
  // 모두 포함하는 문서가 없을 때만, 하나라도 포함하는 문서로(정직하게 표시)
  for (const i of candidates) {
    const s = scoreDoc(i, toks, false);
    if (s > 0) {
      q[i] = { score: s };
      matched++;
    }
  }
  return { hits: Object.keys(q).map(Number).sort(byRank(q)).slice(0, limit), total: matched, mode: 'any' };
}

export function docRef(d) {
  return d.ep ? `${d.ep}#${d.o}` : `${d.slug}#${d.o}`;
}

// 자료ID · EP.17#3 · slug#3 어느 쪽으로도 문서를 찾는다
export function findDoc(key) {
  const s = String(key == null ? '' : key).trim();
  if (!s) return null;
  const direct = DOCS.findIndex((d) => d.id === s);
  if (direct >= 0) return direct;
  const m = s.match(/^(.*?)#(\d{1,2})$/);
  if (m) {
    const ep = episodeByKey(m[1]);
    const o = Number(m[2]);
    const i = DOCS.findIndex((d) => d.o === o && (ep ? d.slug === ep.slug : d.slug === m[1]));
    if (i >= 0) return i;
  }
  const loose = DOCS.map((d, i) => [d, i]).filter(([d]) => d.id && d.id.length > 12 && (d.id.endsWith(s) || d.id.includes(s)));
  return loose.length === 1 ? loose[0][1] : null;
}

export function docsOfEpisode(ep) {
  return DOCS.filter((d) => d.slug === ep.slug);
}

export function linksOf(d) {
  const base = `${GALLERY}/${d.slug}`;
  const ep = episodeOf(d);
  return {
    exhibit: `${base}/exhibit.html`, // 전시 웹페이지
    handout: `${base}/handout.html`, // 수업 활동지
    cards: `${base}/cards/${String(d.o).padStart(2, '0')}.jpg`, // 카드뉴스
    proof: `${base}/proof.html`, // 검토지(원문 대조)
    record: `${base}/record.json`, // 기록 꾸러미(출처·고정값)
    iiif: ep?.iiif ? `${ep.iiif}canvas/${d.o}` : '', // IIIF 캔버스
    iiifManifest: ep?.iiif ? `${ep.iiif}manifest.json` : '',
    viewer: d.viewer || '', // 한국고문서자료관 원본 뷰어
  };
}

export function peopleSearch(query, limit = 20) {
  const q = squash(query || '');
  const rows = CURATION.people.filter(([name]) => !q || squash(name).includes(q) || norm(name).includes(norm(query)));
  return { rows: rows.slice(0, limit), total: rows.length };
}

export function timelineDocs({ yearFrom = null, yearTo = null, episode = null, limit = 30 }) {
  const ep = episode ? episodeByKey(episode) : null;
  const rows = DOCS.filter((d) => d.year
    && (yearFrom == null || d.year >= yearFrom)
    && (yearTo == null || d.year <= yearTo)
    && (!ep || d.slug === ep.slug));
  rows.sort((a, b) => a.year - b.year || epStamp(a) - epStamp(b) || a.o - b.o || a.id.localeCompare(b.id));
  return { rows: rows.slice(0, limit), total: rows.length };
}

export function quotesSearch(query, limit = 20) {
  const toks = tokensOf(query);
  const rows = [];
  for (let i = 0; i < CURATION.quotes.length; i++) {
    const q = CURATION.quotes[i];
    if (toks.length && !toks.every((t) => squash(q.h + q.o).includes(t))) continue;
    rows.push([q, DOCS[q.d]]);
  }
  return rows.slice(0, limit);
}

export function glossaryLookup(query) {
  const q = norm(query || '').trim();
  if (!q) return null;
  const exact = GLOSSARY_TERMS.find((t) => norm(t.term) === q);
  if (exact) return { ...exact, match: 'exact' };
  const partial = GLOSSARY_TERMS.filter((t) => norm(t.term).includes(q) || q.includes(norm(t.term)))
    .sort((a, b) => b.term.length - a.term.length || a.term.localeCompare(b.term));
  if (partial.length) return { ...partial[0], match: 'partial' };
  const guide = READ_GUIDE.find((g) => norm(g.term) === q) || READ_GUIDE.find((g) => norm(g.term).includes(q));
  return guide ? { term: guide.term, meaning: guide.guide, match: 'guide', read_guide: guide.guide } : null;
}

export function examplesOfType(term, limit = 3) {
  const q = norm(term);
  const rows = DOCS.filter((d) => d.ep && (norm(d.type) === q || norm(d.type).includes(q)));
  rows.sort((a, b) => (a.year || 9999) - (b.year || 9999) || epStamp(a) - epStamp(b) || a.id.localeCompare(b.id));
  return rows.slice(0, limit);
}
