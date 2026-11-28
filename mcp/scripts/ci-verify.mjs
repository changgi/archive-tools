#!/usr/bin/env node
// archive-tools MCP 정적 검증 — 데이터셋·도구 정의·예절(UA)·크기 규칙을 실행 없이 확인한다.
//   node mcp/scripts/ci-verify.mjs   (실패하면 종료 코드 1)
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..'); // mcp/
const REPO = join(ROOT, '..'); // archive-tools/
const fails = [];
const oks = [];
const ok = (msg) => oks.push(msg);
const bad = (msg) => fails.push(msg);

const readJson = (p) => JSON.parse(readFileSync(p, 'utf8'));

// 1) 데이터셋이 저장소 산출물과 같은 수치인가
const data = readJson(join(ROOT, 'data/curation.json'));
const analysis = readJson(join(REPO, 'examples/analysis-data.json'));
const c = data.counts;
c.episodes === analysis.eps ? ok(`편 ${c.episodes}`) : bad(`편 수 ${c.episodes} ≠ analysis ${analysis.eps}`);
c.docs === analysis.docs ? ok(`문서 ${c.docs}`) : bad(`문서 수 ${c.docs} ≠ analysis ${analysis.docs}`);
c.collections === analysis.colls ? ok(`소장처 ${c.collections}`) : bad(`소장처 ${c.collections} ≠ ${analysis.colls}`);
c.hanja === analysis.han ? ok(`판독 한자 ${c.hanja}`) : bad(`한자 ${c.hanja} ≠ ${analysis.han}`);
c.quotes_series === analysis.quotes.length ? ok(`인용 ${c.quotes_series}`) : bad(`인용 ${c.quotes_series} ≠ ${analysis.quotes.length}`);
c.span[0] === analysis.span[0] && c.span[1] === analysis.span[1] ? ok(`연대 ${c.span.join('–')}`) : bad(`연대 ${c.span} ≠ ${analysis.span}`);

// 2) 문서·인용·인물 참조가 성립하는가
const docs = data.docs;
let badDoc = 0;
for (const d of docs) {
  if (!d.id || !d.title || !d.slug || !d.o) badDoc++;
  if (d.ep && !/^EP\.\d{2,3}$/.test(d.ep)) badDoc++;
}
badDoc ? bad(`문서 필드 이상 ${badDoc}건`) : ok(`문서 ${docs.length}건 필드 정상`);
const qBad = data.quotes.filter((q) => !q.h || typeof q.d !== 'number' || q.d < 0 || q.d >= docs.length).length;
qBad ? bad(`인용 참조 이상 ${qBad}건`) : ok(`인용 ${data.quotes.length}곳 참조 정상`);
const pBad = data.people.filter(([n, idx]) => !n || !idx.length || idx.some((i) => i < 0 || i >= docs.length)).length;
pBad ? bad(`인물 참조 이상 ${pBad}건`) : ok(`인물 ${data.people.length}명 참조 정상`);
const dup = new Set();
let dupN = 0;
for (const d of docs) {
  for (const k of [`${d.slug}#${d.o}`]) {
    if (dup.has(k)) dupN++;
    dup.add(k);
  }
}
dupN ? bad(`편·순서 중복 ${dupN}건`) : ok('편·순서 고유');

// 3) 문서 유형 사전
const gl = readJson(join(ROOT, 'data/glossary.json'));
gl.glossary.length >= 50 ? ok(`문서 유형 사전 ${gl.glossary.length}항목`) : bad(`문서 유형 사전 ${gl.glossary.length}항목(50 미만)`);
gl.glossary.every((t) => t.term && t.meaning) ? ok('사전 항목 완전') : bad('사전 항목 누락');

// 4) 소장처 스냅숏
const cat = readJson(join(ROOT, 'data/aks_catalog.json'));
cat.collections.length >= 100 ? ok(`소장처 목록 ${cat.collections.length}곳`) : bad(`소장처 목록 ${cat.collections.length}곳(100 미만)`);
cat.collections.every((x) => x.name && x.data_url && x.group) ? ok('소장처 항목 완전') : bad('소장처 항목 누락');

// 5) 도구 정의 — 12종 · 이름 고유 · 읽기 전용 표시
const route = readFileSync(join(ROOT, 'app/api/[transport]/route.js'), 'utf8');
const names = [...route.matchAll(/server\.tool\('([a-z_]+)'/g)].map((m) => m[1]);
names.length === 12 ? ok(`도구 ${names.length}종`) : bad(`도구 ${names.length}종(12 아님): ${names.join(',')}`);
new Set(names).size === 12 ? ok('도구 이름 고유') : bad('도구 이름 중복');
/readOnlyHint: true/.test(route) && /idempotentHint: true/.test(route) && /openWorldHint: true/.test(route)
  ? ok('readOnly · idempotent · openWorld 표시') : bad('도구 annotation 누락');
/instructions:/.test(route) ? ok('서버 instructions 있음') : bad('instructions 없음');
!route.includes('quested-With') ? ok('X-Requested-With 미사용(방화벽 예절)') : bad('X-Requested-With 사용');

// 6) 예절 — 브라우저 위장 UA 금지(정직 UA)
const walk = (dir) => readdirSync(dir).flatMap((f) => {
  const p = join(dir, f);
  if (f === 'node_modules' || f === '.next' || f === '.vercel' || f === 'data') return [];
  return statSync(p).isDirectory() ? walk(p) : [p];
});
const srcFiles = walk(ROOT).filter((p) => /\.(js|mjs|jsx|json|py|md)$/.test(p));
const masked = srcFiles.filter((p) => /Mozilla\/5\.0|AppleWebKit\/|Gecko\/2/.test(readFileSync(p, 'utf8')));
masked.length ? bad(`브라우저 위장 UA ${masked.map((p) => relative(REPO, p)).join(', ')}`) : ok(`정직 UA(${srcFiles.length}개 파일 검사)`);

// 7) 데이터 집합의 지문을 출력 — 배포·재현 확인용
const sha = createHash('sha256').update(JSON.stringify(data)).digest('hex').slice(0, 16);
ok(`데이터 지문 sha256 ${sha}`);

for (const m of oks) console.log('  ✓ ' + m);
for (const m of fails) console.log('  ✗ ' + m);
console.log(fails.length ? `\n실패 ${fails.length}건 / 통과 ${oks.length}건` : `\n전부 통과 ${oks.length}건`);
process.exit(fails.length ? 1 : 0);
