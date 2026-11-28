#!/usr/bin/env node
// 실제 MCP 클라이언트(@modelcontextprotocol/sdk)로 붙어 보는 점검 — initialize 협상 · tools/list · 도구 호출.
//   node mcp/scripts/client-check.mjs [url]
// 기본 url: http://127.0.0.1:3111/api/mcp
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

const url = new URL(process.argv[2] || 'http://127.0.0.1:3111/api/mcp');
const transport = new StreamableHTTPClientTransport(url);
const client = new Client({ name: 'archive-tools-check', version: '1.0.0' });
let fail = 0;
const ok = (m) => console.log('  ✓ ' + m);
const bad = (m) => { console.log('  ✗ ' + m); fail++; };

await client.connect(transport);
const sv = client.getServerVersion();
ok(`initialize — ${sv?.name}/${sv?.version}`);
const caps = client.getServerCapabilities();
ok(`capabilities — tools=${!!caps?.tools}`);

const { tools } = await client.listTools();
tools.length === 12 ? ok(`tools/list ${tools.length}종`) : bad(`tools/list ${tools.length}종`);

const calls = [
  ['curation_search', { query: '이언적', limit: 3 }, 'EP.'],
  ['curation_item', { id: 'EP.17#1', part: 'reading' }, '■ 판독'],
  ['curation_episode', { episode: 'EP.17', part: 'meta' }, '독락당'],
  ['curation_people', { query: '이언적' }, '문서'],
  ['curation_timeline', { year_from: 1539, year_to: 1545 }, '연표'],
  ['curation_quotes', { query: '농사', limit: 3 }, '원문 인용'],
  ['doc_type', { query: '유서' }, '■ 유서'],
  ['curation_stats', {}, 'sha256'],
  ['aks_catalog', { group: '문중', region: '경주', limit: 5 }, '소장처'],
  ['health', {}, '데이터 지문'],
];
for (const [name, args, must] of calls) {
  const t0 = Date.now();
  const res = await client.callTool({ name, arguments: args });
  const txt = (res.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
  const bytes = Buffer.byteLength(txt);
  if (res.isError) bad(`${name} — isError: ${txt.slice(0, 120)}`);
  else if (!txt.includes(must)) bad(`${name} — 기대 문구 없음(${must})`);
  else if (bytes > 23800) bad(`${name} — ${bytes}B (24KB 초과)`);
  else ok(`${name} ${bytes}B · ${Date.now() - t0}ms`);
}

// 같은 호출 두 번 → 같은 텍스트
const a = (await client.callTool({ name: 'curation_search', arguments: { query: '혼인', limit: 5 } })).content[0].text;
const b = (await client.callTool({ name: 'curation_search', arguments: { query: '혼인', limit: 5 } })).content[0].text;
a === b ? ok('같은 질의 두 번 → 같은 응답') : bad('같은 질의 응답이 다름');

await client.close();
console.log(fail ? `\n실패 ${fail}건` : '\n클라이언트 점검 전부 통과');
process.exit(fail ? 1 : 0);
