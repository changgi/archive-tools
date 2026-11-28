// archive-tools 원격 MCP 서버 — Streamable HTTP(stateless), 프로토콜 2025-06-18.
//   큐레이션: curation_* — 「고문서 한 장」 200편 · 문서 726건 · 인용 763곳 · 인물 258명(오프라인 데이터셋)
//   실시간  : aks_*       — 한국고문서자료관(archive.aks.ac.kr) 소장처·문서 트리 읽기
//   도구 12종 · 전 도구 readOnly / idempotent / openWorld · 응답 24KB 한도 · 같은 입력 → 같은 바이트
import { z } from 'zod';
import { createMcpHandler } from 'mcp-handler';
import {
  DATA, DOCS, DATASET_SHA256, GALLERY, CATALOG_COLLECTIONS, CATALOG,
  searchDocs, findDoc, docRef, episodeByKey, episodeOf, docsOfEpisode, linksOf,
  peopleSearch, timelineDocs, quotesSearch, glossaryLookup, examplesOfType,
} from '../../../lib/core.js';
import { text, clamp, cut, oneLine, excerpt } from '../../../lib/text.js';
import * as aks from '../../../lib/aks.js';

export const maxDuration = 60;
export const preferredRegion = 'icn1'; // 국내 공공 사이트(archive.aks.ac.kr) 접근 — 해외 IP 차단 회피가 아니라 정상 접근을 위한 고정
export const dynamic = 'force-dynamic';

const VERSION = '0.1.0';
const C = DATA.counts;

const TOOLS = [
  'curation_search', 'curation_item', 'curation_episode', 'curation_people', 'curation_timeline',
  'curation_quotes', 'doc_type', 'curation_stats', 'aks_catalog', 'aks_find', 'aks_manifest', 'health',
];

const linkBlock = (d, ep) => {
  const L = linksOf(d);
  const rows = [
    L.viewer ? `- 원본 뷰어(한국고문서자료관): ${L.viewer}` : '',
    `- 전시 웹페이지: ${L.exhibit}`,
    `- 수업 활동지: ${L.handout}`,
    `- 카드뉴스: ${L.cards}`,
    `- 검토지(원문 대조): ${L.proof}`,
    `- 기록 꾸러미(출처·고정값): ${L.record}`,
    L.iiif ? `- IIIF 캔버스: ${L.iiif}` : '',
    L.iiifManifest ? `- 편 매니페스트(IIIF Presentation 3): ${L.iiifManifest}` : '',
    ep ? `- 편 전체: ${GALLERY}/${ep.slug}/ · 소장처: ${ep.collection}` : '',
  ];
  return rows.filter(Boolean).join('\n');
};

const head = (d) => {
  const ep = episodeOf(d);
  const where = ep ? ep.ep : `${d.slug}(번호 전 예시)`;
  return `[${docRef(d)}] ${where} · ${d.year || '연도 미상'} · ${d.type || '유형 미상'}${d.persons.length ? ' · ' + d.persons.join(', ') : ''}`;
};

function itemBody(d, part, maxChars) {
  const ep = episodeOf(d);
  const rows = [];
  rows.push(head(d));
  rows.push(`문서명: ${d.title}`);
  if (ep) rows.push(`소장처: ${ep.collection}${ep.kind ? ` · ${ep.kind}` : ''}${ep.region ? ` · ${ep.region}` : ''}`);
  if (d.persons.length) rows.push(`인물: ${d.persons.join('; ')}`);
  if (d.tdesc) rows.push(`유형 설명: ${d.tdesc}`);
  if (d.shared) rows.push(`※ ${d.shared}`);
  if (d.review) rows.push(`검토: ${d.review}(사람이 원본과 대조했다고 기록된 문서)`);
  else rows.push('검토: 미검토 — 아래 판독·번역은 사람 대조 전 초안입니다');
  const sec = (label, body, hard = maxChars) => {
    const b = String(body || '').trim();
    if (!b) return;
    const s = cut(b, hard);
    rows.push('');
    rows.push(`■ ${label}`);
    rows.push(s + (s.length < b.length ? `\n…(${label} ${b.length}자 중 ${s.length}자까지 — part="all"이면 24KB 한도까지 더 나옵니다)` : ''));
  };
  if (part !== 'meta') {
    if (part !== 'reading') sec('이야기 — 왜 이 문서인가', d.story);
    if (part !== 'story') {
      sec('해제 — 어떤 문서인가', d.note);
      sec('내용 요약', d.summary);
      sec('판독 — 이미지에서 읽은 글자', d.read);
      sec('원문 — 판독한 원문 그대로', d.original, Math.max(1200, maxChars));
      sec('번역 — 현대 한국어', d.translation, Math.max(1600, maxChars));
    }
    if (d.caption && part !== 'reading') sec('캡션', d.caption);
  }
  rows.push('');
  rows.push('■ 링크');
  rows.push(linkBlock(d, ep));
  if (ep) {
    rows.push('');
    rows.push(`■ 이어서 — curation_episode(episode="${ep.ep}") 로 이 편의 다른 문서 ${ep.docs - 1}건, curation_quotes(query="…") 로 원문 인용 검색`);
  }
  return rows.join('\n');
}

const handler = createMcpHandler(
  (server) => {
    const _tool = server.tool.bind(server);
    server.tool = (name, desc, schema, cb) => _tool(name, desc.slice(0, 1024), schema, {
      title: name, readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true,
    }, async (args) => clamp(await cb(args)));

    // ── 1. 큐레이션 검색 ──────────────────────────────────────────────
    server.tool('curation_search',
      '「고문서 한 장」 큐레이션 데이터셋(200편 · 문서 726건 — 판독 · 번역 · 해제 · 이야기 전문)에서 낱말 · 한자 · 인물 · 문서유형 · 연대로 찾는다. 조선시대 고문서(고신 · 교지 · 홍패 · 호구단자 · 명문 · 편지 …)를 원문과 함께 읽고 싶을 때 첫 도구. 결과의 id로 curation_item을 부르면 판독·번역 전문이 나온다. 예: query="유관순", query="혼인 납폐서", type="홍패", year_from=1800.',
      {
        query: z.string().default('').describe('찾을 낱말 — 한국어 · 한자 · 이름 · 문서명 일부. 여러 낱말이면 모두 들어간 문서를 먼저 찾고, 없으면 하나라도 들어간 문서를 보여 준다. 비우면 필터만 적용'),
        type: z.string().default('').describe('문서유형 (예: 고신, 교지, 홍패, 호구단자, 명문, 분재기, 편지, 유서)'),
        person: z.string().default('').describe('인물 이름 (예: 유관순, 송준길)'),
        year_from: z.number().int().min(1000).max(2100).optional().describe('시작 연도'),
        year_to: z.number().int().min(1000).max(2100).optional().describe('끝 연도'),
        episode: z.string().default('').describe('편 번호 또는 폴더 이름 (예: "17", "EP.17", "dongnakdang")'),
        scope: z.enum(['series', 'all']).default('series').describe('series=정식 200편(726건)만 · all=번호 전 기획 예시 3편(22건) 포함'),
        limit: z.number().int().min(1).max(20).default(8),
      },
      async ({ query, type, person, year_from, year_to, episode, scope, limit }) => {
        let r = searchDocs({ query, type, person, yearFrom: year_from ?? null, yearTo: year_to ?? null, episode: episode || null, scope, limit });
        let widened = false;
        if (!r.hits.length && scope === 'series') { // 정식 200편에 없으면 번호 전 기획 예시까지 넓혀 본다(숨기지 않고 알린다)
          const w = searchDocs({ query, type, person, yearFrom: year_from ?? null, yearTo: year_to ?? null, episode: episode || null, scope: 'all', limit });
          if (w.hits.length) {
            r = w;
            widened = true;
          }
        }
        if (!r.hits.length) {
          return text(`큐레이션에서 '${query || '(필터)'}'에 맞는 문서가 없습니다(편 ${C.episodes} · 문서 ${C.docs}).\n`
            + '- 표기·연도를 바꿔 보세요(예: "고신" → "교지", "유관순" → "판결문").\n'
            + '- 데이터셋에 없을 수 있습니다 — 이 데이터셋은 사람이 고른 726건입니다(자료관 전체가 아님).\n'
            + '- 자료관 원본을 직접 훑으려면 aks_catalog → aks_manifest.\n- 문서 유형 이름이 낯설면 doc_type(query="고신")으로 사전을 보세요.');
        }
        const toks = String(query || '').split(/\s+/).filter(Boolean);
        const lines = r.hits.map((i, k) => {
          const d = DOCS[i];
          const ep = episodeOf(d);
          const ex = excerpt(d.story || d.summary || d.translation, toks[0] || '', 150);
          return `${k + 1}. [${docRef(d)}] ${d.year || '연도 미상'} · ${d.type || '유형 미상'} · ${d.title}`
            + (ep ? `\n   소장처: ${ep.collection}` : '')
            + (ex ? `\n   ${ex}` : '');
        });
        const modeNote = (r.mode === 'any' ? '\n※ 모든 낱말이 함께 든 문서가 없어, 하나라도 든 문서를 보여 줍니다.' : '')
          + (widened ? `\n※ 정식 200편에는 없고, 번호 전 기획 예시 ${C.episodes_pre_series}편에서 찾았습니다(scope="all").` : '');
        return text(`「고문서 한 장」 큐레이션 검색 — '${query || '(필터)'}' ${r.total}건 중 ${r.hits.length}건`
          + ` (전체 ${C.episodes}편 · 문서 ${C.docs}건)` + modeNote + '\n\n' + lines.join('\n\n')
          + `\n\n→ 전문(판독·번역·해제·링크): curation_item(id="${docRef(DOCS[r.hits[0]])}")`
          + '\n→ 원문 인용 검색: curation_quotes(query="…") · 인물: curation_people · 연표: curation_timeline');
      });

    // ── 2. 문서 상세 ─────────────────────────────────────────────────
    server.tool('curation_item',
      '큐레이션 문서 한 건의 전문 — 판독(이미지에서 읽은 글자) · 원문 · 번역 · 해제 · 요약 · 이야기와 전시 웹페이지 · 수업 활동지 · 카드뉴스 · IIIF · 원본 뷰어 링크까지. id는 자료ID 또는 "EP.17#3"(편#순서). part로 읽기/이야기/메타만 골라 받을 수 있다.',
      {
        id: z.string().describe('자료ID(G002+AKS+…) 또는 "EP.17#3" · "dongnakdang#2"'),
        part: z.enum(['all', 'reading', 'story', 'meta']).default('all').describe('all=전문 · reading=판독·원문·번역·해제 · story=이야기·캡션 · meta=머리 정보와 링크만'),
        max_chars: z.number().int().min(400).max(6000).default(3000).describe('항목별 글자 상한(원문·번역은 더 넉넉)'),
      },
      async ({ id, part, max_chars }) => {
        const i = findDoc(id);
        if (i == null) {
          return text(`'${id}' 문서를 찾지 못했습니다. 자료ID 전체 또는 "EP.17#3" 형식으로 주세요.\n찾는 법: curation_search(query="…")`);
        }
        return text(itemBody(DOCS[i], part, max_chars));
      });

    // ── 3. 편 상세 ───────────────────────────────────────────────────
    server.tool('curation_episode',
      '「고문서 한 장」 한 편(회차)의 구성 — 제목 · 소장처 · 시대 · 기획 의도 · 큐레이터 노트 · 문서 목록과 이 편의 산출물 링크(전시 웹페이지 · 수업 활동지 · 카드뉴스 · IIIF · 기록 꾸러미). 200편 모두 같은 구조.',
      {
        episode: z.string().describe('편 번호 또는 폴더 이름 (예: "17", "EP.17", "dongnakdang")'),
        part: z.enum(['all', 'list', 'meta']).default('all').describe('all=전부 · list=문서 목록만 · meta=기획 의도와 링크만'),
      },
      async ({ episode, part }) => {
        const ep = episodeByKey(episode);
        if (!ep) return text(`'${episode}' 편을 찾지 못했습니다. 1~200 사이 번호 또는 폴더 이름으로 주세요(예: "17").`);
        const docs = docsOfEpisode(ep);
        const rows = [`[${ep.ep}] ${ep.title}`, `소장처: ${ep.collection}${ep.kind ? ` · ${ep.kind}` : ''}${ep.region ? ` · ${ep.region}` : ''}`,
          `문서 ${ep.docs}건 · 연도 ${ep.years.length ? `${ep.years[0]}~${ep.years[ep.years.length - 1]}` : '미상'}${ep.emotion ? ` · 정서: ${ep.emotion}` : ''}`];
        if (part !== 'list') {
          if (ep.purpose) rows.push('', '■ 기획 의도', ep.purpose);
          if (ep.message) rows.push('', '■ 전하고 싶은 것', ep.message);
          if (ep.wish && ep.wish !== ep.message) rows.push('', '■ 큐레이터 노트 — 전하고 싶은 것', ep.wish);
          if (ep.backstage) rows.push('', '■ 만들며 있었던 일', ep.backstage);
          if (ep.question) rows.push('', '■ 남겨 둔 질문', ep.question);
        }
        if (part !== 'meta') {
          rows.push('', '■ 문서 목록');
          for (const d of docs) rows.push(`${d.o}. [${docRef(d)}] ${d.year || '연도 미상'} · ${d.type || '유형 미상'} · ${d.title}${d.persons.length ? ` (${d.persons.join(', ')})` : ''}`);
        }
        rows.push('', '■ 이 편의 산출물');
        rows.push(`- 갤러리: ${GALLERY}/${ep.slug}/`);
        rows.push(`- 전시 웹페이지: ${GALLERY}/${ep.slug}/exhibit.html`);
        rows.push(`- 수업 활동지: ${GALLERY}/${ep.slug}/handout.html`);
        rows.push(`- 카드뉴스: ${GALLERY}/${ep.slug}/cards/00_표지.jpg (문서별 01~${String(ep.docs).padStart(2, '0')})`);
        rows.push(`- 기록 꾸러미: ${GALLERY}/${ep.slug}/record.json · 검토지: ${GALLERY}/${ep.slug}/proof.html`);
        if (ep.iiif) rows.push(`- IIIF 매니페스트: ${ep.iiif}manifest.json`);
        if (docs[0]) rows.push('', `→ 전문: curation_item(id="${docRef(docs[0])}")`);
        return text(rows.join('\n'));
      });

    // ── 4. 인물 ─────────────────────────────────────────────────────
    server.tool('curation_people',
      '큐레이션에 나오는 인물 258명 찾아보기 — 이름으로 찾으면 그 사람이 적힌 문서와 편을 보여 준다(여러 편에 걸친 인물 포함). 문서에 적힌 이름만 세며, 같은 이름이 같은 사람인지는 문서로 확인해야 한다.',
      {
        query: z.string().default('').describe('이름 일부 (예: "유관순", "송준길", "이씨")'),
        limit: z.number().int().min(1).max(60).default(15),
      },
      async ({ query, limit }) => {
        const r = peopleSearch(query, limit);
        if (!r.total) return text(`'${query}' 이름을 찾지 못했습니다. 성 없이 이름만(예: "관순") 또는 다른 표기로 시도해 보세요.`);
        const lines = r.rows.map(([name, idx]) => {
          const eps = [...new Set(idx.map((i) => DOCS[i].ep).filter(Boolean))];
          const refs = idx.slice(0, 4).map((i) => `${docRef(DOCS[i])} ${DOCS[i].year || ''} ${oneLine(DOCS[i].title, 46)}`);
          return `- ${name} — 문서 ${idx.length}건${eps.length > 1 ? ` · ${eps.length}편` : ''}\n  ${refs.join('\n  ')}${idx.length > 4 ? `\n  …외 ${idx.length - 4}건` : ''}`;
        });
        const first = r.rows[0][1][0];
        return text(`인물 ${r.total}명 중 ${r.rows.length}명 (문서에 적힌 이름 기준)\n\n` + lines.join('\n')
          + `\n\n→ 그 사람 문서 전문: curation_item(id="${docRef(DOCS[first])}") · 이름이 본문에 나오는 곳: curation_search(query="${r.rows[0][0]}")`);
      });

    // ── 5. 연표 ─────────────────────────────────────────────────────
    server.tool('curation_timeline',
      '큐레이션 문서 726건의 연표 — 연도 범위로 그 시대 문서를 시간순으로 본다(연대 미상 52건 제외). 연도는 문서명·연호에서 읽은 값이고, 추정·자료관 연대는 데이터에 근거가 표시돼 있다.',
      {
        year_from: z.number().int().min(1000).max(2100).optional().describe('시작 연도 (예: 1592)'),
        year_to: z.number().int().min(1000).max(2100).optional().describe('끝 연도 (예: 1700)'),
        episode: z.string().default('').describe('한 편 안에서만 볼 때(예: "17")'),
        limit: z.number().int().min(1).max(60).default(25),
      },
      async ({ year_from, year_to, episode, limit }) => {
        const r = timelineDocs({ yearFrom: year_from ?? null, yearTo: year_to ?? null, episode: episode || null, limit });
        if (!r.total) return text('그 범위에 연대가 적힌 문서가 없습니다. 범위를 넓히거나 curation_search(type=…)로 찾아보세요.');
        const lines = r.rows.map((d) => `${d.year} · [${docRef(d)}] ${d.type || '유형 미상'} · ${oneLine(d.title, 70)}`);
        return text(`연표 ${year_from ?? C.span[0]}~${year_to ?? C.span[1]} — ${r.total}건 중 ${r.rows.length}건(시간순)\n\n`
          + lines.join('\n')
          + `\n\n※ 전체 연대 범위 ${C.span[0]}–${C.span[1]}년 · 연대가 적히지 않은 문서는 이 목록에서 빠집니다.`
          + `\n→ 전문: curation_item(id="${docRef(r.rows[0])}")`);
      });

    // ── 6. 인용 ─────────────────────────────────────────────────────
    server.tool('curation_quotes',
      '문서 위에 적힌 문장 763곳 — "현대어 풀이(原文)" 쌍으로 검색한다. 각주·강의·전시에 그대로 인용할 수 있는 원문과 그 뜻. 낱말 또는 한자로 찾는다.',
      {
        query: z.string().default('').describe('찾을 낱말 · 한자 (예: "농사", "課農桑", "어머니")'),
        limit: z.number().int().min(1).max(30).default(15),
      },
      async ({ query, limit }) => {
        const rows = quotesSearch(query, limit);
        if (!rows.length) return text(`'${query}'가 든 인용을 찾지 못했습니다. 더 짧은 낱말이나 한자 한두 자로 시도해 보세요.`);
        const lines = rows.map(([q, d], k) => `${k + 1}. "${q.h}" (${q.o})\n   — [${docRef(d)}] ${d.year || ''} ${oneLine(d.title, 60)}`);
        return text(`원문 인용 ${rows.length}곳${query ? ` — '${query}'` : ''}\n\n` + lines.join('\n')
          + '\n\n※ 인용은 데이터셋의 판독 · 이야기에서 그대로 가져온 값입니다. 인용할 때 출처는 문서명과 한국학중앙연구원 한국고문서자료관입니다.'
          + `\n→ 문서 전문: curation_item(id="${docRef(rows[0][1])}")`);
      });

    // ── 7. 문서 유형 사전 ────────────────────────────────────────────
    server.tool('doc_type',
      '고문서 유형 사전 — 고신 · 교지 · 홍패 · 백패 · 호구단자 · 준호구 · 납폐서 · 명문 · 분재기 · 완문 · 소지 · 상량문 … 의 뜻과 읽는 법(서식 설명), 그리고 데이터셋에서 그 유형의 실제 문서 예. 낯선 문서 이름을 만났을 때.',
      {
        query: z.string().describe('문서 유형 이름 (예: "홍패", "준호구", "분재기") — 이름 일부로도 찾는다'),
      },
      async ({ query }) => {
        const g = glossaryLookup(query);
        if (!g) {
          const near = ['고신', '교지', '홍패', '호구단자', '명문', '분재기', '유서', '소지'].join(' · ');
          return text(`'${query}' 유형을 사전에서 찾지 못했습니다. 자주 쓰는 유형: ${near}\n데이터셋 검색: curation_search(query="${query}")`);
        }
        const ex = examplesOfType(g.term, 3);
        const rows = [`■ ${g.term}`, g.meaning || ''];
        if (g.read_guide) rows.push('', '읽는 법: ' + g.read_guide);
        if (ex.length) {
          rows.push('', '■ 데이터셋의 실제 문서');
          for (const d of ex) rows.push(`- [${docRef(d)}] ${d.year || '연도 미상'} ${oneLine(d.title, 60)}`);
          rows.push(`→ 판독·번역: curation_item(id="${docRef(ex[0])}")`);
        }
        rows.push('', `※ ${C.types}개 유형이 데이터셋에 나옵니다. 유형별 검색: curation_search(type="${g.term}")`);
        return text(rows.filter(Boolean).join('\n'));
      });

    // ── 8. 통합 통계 ────────────────────────────────────────────────
    server.tool('curation_stats',
      '「고문서 한 장」 데이터셋의 규모와 분포 — 편·문서·소장처·연대 범위·판독 한자·인용·인물 수, 문서 유형·세기·소장처 종류·지역 분포, 검토 진행 상황. 데이터의 지문(SHA-256)도 함께 준다.',
      {},
      async () => {
        const rd = DATA.reading || {};
        const byType = {};
        const byCentury = {};
        const byKind = {};
        const byRegion = {};
        const byColl = {};
        for (const d of DOCS) {
          if (!d.ep) continue; // 발행 지표(편 200 · 문서 726)와 같은 범위 — 번호 전 기획 예시는 뺀다
          byType[d.type || '미상'] = (byType[d.type || '미상'] || 0) + 1;
          if (d.year) {
            const c = `${Math.floor((d.year - 1) / 100) + 1}세기`;
            byCentury[c] = (byCentury[c] || 0) + 1;
          }
          const ep = episodeOf(d);
          if (ep) {
            byKind[ep.kind || '미상'] = (byKind[ep.kind || '미상'] || 0) + 1;
            byRegion[ep.region || '미상'] = (byRegion[ep.region || '미상'] || 0) + 1;
            byColl[ep.collection] = (byColl[ep.collection] || 0) + 1;
          }
        }
        const top = (o, n) => Object.entries(o).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, n)
          .map(([k, v]) => `${k} ${v}`).join(' · ');
        const lines = [
          DATA.source.series,
          `편 ${C.episodes} · 문서 ${C.docs}건 · 소장처 ${C.collections}곳 · 연대 ${C.span[0]}–${C.span[1]}년`,
          `판독 한자 ${C.hanja.toLocaleString('en-US')}자 · 원문 인용 ${C.quotes_series}곳 · 인물 ${C.people}명 · 문서 유형 ${C.types}개`,
          `읽기: 판독 ${rd.read}건 · 번역 ${rd.translated}건 · 판독 불가 글자(□) ${rd.unknown} · 불확실(?) ${rd.unsure} · 날짜 언급 ${rd.date_mentions}`,
          rd.quote_issues && rd.quote_issues.length ? `인용 대조 불일치 ${rd.quote_issues.length}건` : '인용 대조: 763곳 전부 원문과 일치',
          rd.date_issues && rd.date_issues.length ? `날짜가 어긋난 문서: ${rd.date_issues.join(', ')}(원문 그대로 두고 해제에 밝힘)` : '',
          `이 밖에 번호 전 기획 예시 ${C.episodes_pre_series}편 · ${C.docs_pre_series}건(scope="all"로 검색)`,
          '',
          `■ 문서 유형 상위: ${top(byType, 12)}`,
          `■ 세기 분포: ${top(byCentury, 8)}`,
          `■ 소장처 종류(문서 수): ${top(byKind, 6)}`,
          `■ 지역(문서 수): ${top(byRegion, 8)}`,
          `■ 문서 많은 소장처: ${top(byColl, 5)}`,
          '',
          `■ 데이터 지문: sha256 ${DATASET_SHA256}`,
          `■ 출처: ${DATA.source.archive} · 갤러리 ${DATA.source.gallery}`,
          `■ 이용: ${DATA.source.license}`,
        ];
        return text(lines.filter((x) => x !== '').join('\n'));
      });

    // ── 9. 소장처 목록 ──────────────────────────────────────────────
    server.tool('aks_catalog',
      '한국고문서자료관(archive.aks.ac.kr) 소장처 목록 173곳 — 문중 · 서원향교 · 박물관도서관 · 공공기관 · 사찰 · 촌락 · 개인. 분류·지역·이름으로 걸러 본다. 소장처를 고르면 aks_manifest로 그 안의 문서 목록을 읽는다.',
      {
        group: z.string().default('').describe('분류 (문중 · 서원향교 · 박물관도서관 · 공공기관 · 사찰 · 촌락 · 개인 · 기타)'),
        region: z.string().default('').describe('지역 또는 지명 (예: "경상북도", "경주", "제주")'),
        query: z.string().default('').describe('소장처 이름 일부 (예: "독락당", "경성당")'),
        limit: z.number().int().min(1).max(80).default(30),
      },
      async ({ group, region, query, limit }) => {
        const q = String(query || '').toLowerCase();
        const rows = CATALOG_COLLECTIONS.filter((c) => (!group || c.group.includes(group))
          && (!region || c.region.includes(region) || c.name.includes(region))
          && (!q || `${c.name} ${c.region}`.toLowerCase().includes(q)));
        const groups = {};
        for (const c of CATALOG_COLLECTIONS) groups[c.group] = (groups[c.group] || 0) + 1;
        if (!rows.length) {
          return text(`조건에 맞는 소장처가 없습니다. 분류: ${Object.entries(groups).map(([k, v]) => `${k} ${v}`).join(' · ')}\n`
            + '이름 찾기는 aks_find(query="…")를 쓰세요.');
        }
        const lines = rows.slice(0, limit).map((c) => `[${c.id}] ${c.group} > ${c.region || '—'} > ${c.name}\n   → aks_manifest(name="${c.name}")`);
        return text(`한국고문서자료관 소장처 ${rows.length}곳 (전체 ${CATALOG_COLLECTIONS.length}곳 · 분류: ${Object.entries(groups).map(([k, v]) => `${k} ${v}`).join(' · ')})\n\n`
          + lines.join('\n')
          + (rows.length > limit ? `\n…외 ${rows.length - limit}곳 — limit을 올리거나 group·region으로 좁히세요.` : '')
          + '\n\n※ 문서 목록은 실시간 조회입니다(사이트 응답에 따라 시간이 걸릴 수 있음).');
      });

    // ── 10. 소장처 이름 찾기 ─────────────────────────────────────────
    server.tool('aks_find',
      '소장처 이름으로 한국고문서자료관 찾기 — "동춘당 송준길", "독락당", "경성당"처럼 부르는 이름으로 후보와 data_url을 찾는다. aks_manifest에 이름을 그대로 넘겨도 된다.',
      {
        query: z.string().describe('소장처 이름 또는 그 일부 (지역명 · 성씨 · 인물명도 됨)'),
        limit: z.number().int().min(1).max(20).default(8),
      },
      async ({ query, limit }) => {
        const toks = String(query || '').toLowerCase().split(/\s+/).filter(Boolean);
        const scored = CATALOG_COLLECTIONS.map((c) => {
          const hay = `${c.group} ${c.region} ${c.name}`.toLowerCase();
          const hit = toks.filter((t) => hay.includes(t)).length;
          return { c, hit };
        }).filter((x) => x.hit > 0).sort((a, b) => b.hit - a.hit || a.c.name.localeCompare(b.c.name));
        if (!scored.length) return text(`'${query}'로 찾지 못했습니다. 지역명·성씨·인물명 등 다른 낱말로 시도하거나 aks_catalog로 목록을 보세요.`);
        const full = scored.filter((x) => x.hit === toks.length);
        const rows = (full.length ? full : scored).slice(0, limit);
        return text(`'${query}' — ${rows.length}곳${full.length ? '' : ' (모든 낱말이 맞는 곳은 없어 일부만 맞는 곳을 보여 줍니다)'}\n\n`
          + rows.map(({ c }) => `[${c.id}] ${c.group} > ${c.region || '—'} > ${c.name}\n   → aks_manifest(name="${c.name}")`).join('\n')
          + '\n\n※ aks_manifest는 이 소장처의 문서 트리를 실시간으로 읽습니다.');
      });

    // ── 11. 소장처 문서 목록(실시간) ─────────────────────────────────
    server.tool('aks_manifest',
      '한국고문서자료관 소장처 안의 문서 목록을 실시간으로 읽는다 — 문서마다 자료ID · 문서명 · 페이지 수 · 원본 뷰어 링크. 정규식 match로 문서를 골라낼 수 있다(예: "유지|소지|명문"). 목록만 필요하면 pages=0(빠름), 페이지 수까지 보려면 pages=8~20.',
      {
        name: z.string().default('').describe('소장처 이름 (aks_find · aks_catalog로 확인)'),
        data_url: z.string().default('').describe('소장처 data-url (?itemId=book&…) — 이름 대신 직접 줄 때'),
        match: z.string().default('').describe('문서명 정규식 (예: "유지|소지", "상량문") — 비우면 전부'),
        limit: z.number().int().min(1).max(50).default(20).describe('보여 줄 문서 수'),
        pages: z.number().int().min(0).max(20).default(0).describe('페이지 수를 조회할 문서 수(0이면 조회 안 함 — 가장 빠름)'),
      },
      async ({ name, data_url, match, limit, pages }) => {
        let target = null;
        if (data_url) {
          target = { name: name || '(직접 지정)', data_url, group: '', region: '' };
        } else if (name) {
          const toks = name.toLowerCase().split(/\s+/).filter(Boolean);
          const scored = CATALOG_COLLECTIONS.map((c) => {
            const hay = `${c.group} ${c.region} ${c.name}`.toLowerCase();
            return { c, hit: toks.filter((t) => hay.includes(t)).length };
          }).filter((x) => x.hit === toks.length).sort((a, b) => a.c.name.length - b.c.name.length || a.c.name.localeCompare(b.c.name));
          if (!scored.length) return text(`'${name}' 소장처를 찾지 못했습니다. aks_find(query="${name}")로 후보를 확인하거나 data_url을 직접 주세요.`);
          if (scored.length > 1 && scored[0].hit === scored[1].hit && scored[0].c.name !== scored[1].c.name) {
            return text(`'${name}'에 여러 소장처가 맞습니다 — 하나를 골라 이름을 더 구체적으로 주세요.\n`
              + scored.slice(0, 8).map(({ c }) => `- ${c.group} > ${c.region} > ${c.name} [${c.id}]`).join('\n'));
          }
          target = scored[0].c;
        } else {
          return text('name 또는 data_url 중 하나가 필요합니다. 먼저 aks_find(query="…")로 소장처를 찾으세요.');
        }
        let re = null;
        if (match) {
          try {
            re = new RegExp(match);
          } catch {
            return text(`정규식 '${match}'을 읽을 수 없습니다. 예: "유지|소지", "상량문".`);
          }
        }
        const t = await aks.tree(target.data_url, { maxNodes: 80, maxDepth: 6, budgetMs: 14000 });
        if (!t.docs.length) {
          return text(`[${target.name}] 문서를 찾지 못했습니다 — 조회한 폴더 ${t.visited}곳`
            + (t.folders.filter((f) => f.error).length ? ` · 오류 ${t.folders.filter((f) => f.error).map((f) => `${f.path.join('>') || '루트'}: ${f.error}`).join(', ')}` : '')
            + '\n※ 사이트가 응답하지 않았거나 소장처에 공개 문서가 없을 수 있습니다. 브라우저로 확인: https://archive.aks.ac.kr');
        }
        const matched = re ? t.docs.filter((d) => re.test(d.name)) : t.docs;
        const shown = matched.slice(0, limit);
        let pagesInfo = { rows: [], failed: 0, elapsedMs: 0 };
        if (pages > 0) pagesInfo = await aks.pagesFor(shown.slice(0, pages), { max: pages, concurrency: 4, budgetMs: 10000 });
        const pageOf = new Map(pagesInfo.rows.map((r) => [r.id, r.pages]));
        const lines = shown.map((d, k) => {
          const p = !pageOf.has(d.id) ? '' : pageOf.get(d.id) == null ? ' · 페이지 조회 실패' : ` · ${pageOf.get(d.id)}장`;
          return `${k + 1}. ${d.name}${p}\n   ${d.id} · ${aks.viewerLink(d.q)}`;
        });
        const folders = [...new Set(t.docs.map((d) => d.path.join(' > ')).filter(Boolean))];
        return text(`[${target.name}]${target.group ? ` ${target.group} > ${target.region}` : ''} — 문서 ${t.docs.length}건`
          + (re ? ` 중 '${match}' ${matched.length}건` : '') + (folders.length ? ` · 분류: ${folders.slice(0, 6).join(' / ')}` : '')
          + (t.truncated ? ' · ※ 사이트 응답 한도로 일부만 읽었습니다(더 보려면 match로 좁히세요)' : '')
          + `\n\n${lines.join('\n')}`
          + (matched.length > shown.length ? `\n…외 ${matched.length - shown.length}건 — limit을 올리거나 match로 좁히세요.` : '')
          + (pages > 0 ? `\n※ 페이지 수 ${pagesInfo.rows.filter((r) => r.pages != null).length}건 조회${pagesInfo.failed ? ` · 실패 ${pagesInfo.failed}건` : ''} — 원본은 자료관 사이트에서 확인하세요.` : '')
          + `\n※ 수집·내려받기는 이 저장소의 harvest.py(플러그인)로 합니다. 이 도구는 읽기 전용 조회입니다.`);
      });

    // ── 12. 헬스체크 ────────────────────────────────────────────────
    server.tool('health',
      '이 서버의 상태 — 버전 · 도구 목록 · 데이터셋 지문과 규모 · 자료관 실시간 접속(probe=true일 때). 심사·점검용이며, probe 없이 부르면 언제나 같은 값이 나온다.',
      {
        probe: z.boolean().default(false).describe('true면 archive.aks.ac.kr에 실제로 한 번 접속해 결과를 덧붙인다(값이 매번 달라짐)'),
      },
      async ({ probe }) => {
        const lines = [
          `archive-tools MCP v${VERSION} — Streamable HTTP(stateless) · protocol 2025-06-18 · region icn1`,
          `도구 ${TOOLS.length}종(readOnly · idempotent · openWorld): ${TOOLS.join(', ')}`,
          `데이터셋: 편 ${C.episodes} · 문서 ${C.docs} · 소장처 ${C.collections} · 인용 ${C.quotes_series} · 인물 ${C.people} · 판독 한자 ${C.hanja}`,
          `데이터 지문 sha256 ${DATASET_SHA256}`,
          `소장처 목록: ${CATALOG_COLLECTIONS.length}곳(archive.aks.ac.kr 실시간 트리에서 ${CATALOG.fetched} 받은 스냅숏)`,
          '데이터 상태: 큐레이션 도구는 정적 데이터만 읽어 네트워크 없이 같은 응답을 냅니다. aks_* 도구만 실시간입니다.',
        ];
        if (probe) {
          const p = await aks.probe();
          lines.push(`자료관 접속(probe): ${p.ok ? '정상' : '실패'} · HTTP ${p.status ?? '—'}${p.groups ? ` · 최상위 분류 ${p.groups}` : ''}${p.error ? ` · ${p.error}` : ''} · ${p.ms}ms`);
        }
        return text(lines.join('\n'));
      });
  },
  {
    instructions: '한국 기록·고문서 조사용 커넥터입니다. (1) 「고문서 한 장」 200편 · 문서 726건의 판독·번역·해제·이야기를 찾을 때는 curation_search → curation_item 순서로 부르고, 원문 인용은 curation_quotes를 쓰세요. (2) 한국고문서자료관(archive.aks.ac.kr) 원본을 직접 훑을 때는 aks_find/aks_catalog로 소장처를 찾고 aks_manifest로 문서 목록을 읽으세요. (3) 판독·번역·해제는 데이터에 있는 문자열만 인용하고 새로 지어내지 마세요. 특히 한자 원문은 데이터에 있는 것만 옮기세요. (4) 검토 칸이 비어 있는 문서는 "사람 대조 전 초안"이라고 밝히세요. (5) 고문서 이미지의 이용·재배포는 소장처 동의가 필요합니다(응답의 링크 안내). (6) 응답은 24KB 한도라 limit·max_chars·part로 나눠 받으세요.',
  },
  { basePath: '/api' },
);

export { handler as GET, handler as POST, handler as DELETE };
