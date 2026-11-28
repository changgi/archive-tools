// 한국고문서자료관(archive.aks.ac.kr) 실시간 읽기 — harvest.py 의 manifest·find 와 같은 사이트 인터페이스를 쓴다.
//  · treeAjax.do  : 소장처 안의 폴더·문서 트리(<li data-dataId data-url><span title>)
//  · imgnode.do   : 문서 한 건의 페이지 목록(JSON: infoTitle · imgItems[].dzi)
// 예절: 읽기만, 동시 요청 4개 이하, 문서 스스로를 밝히는 UA(브라우저 위장 없음), 실패는 숨기지 않고 표시.
const SITE = 'https://archive.aks.ac.kr';
const VIEWER = `${SITE}/viewer/`;
const UA = 'archive-tools-mcp/0.1 (+https://github.com/changgi/archive-tools; read-only archival metadata lookup)';

export const viewerLink = (q) => `${SITE}/viewer/viewer.do#imgnode.do${q}`;

function unescapeHtml(s) {
  return String(s)
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&apos;/g, "'");
}

async function getText(q, timeoutMs = 8000) {
  const s = String(q == null ? '' : q).trim();
  const url = /^https?:/i.test(s) ? s : VIEWER + (s.startsWith('?') ? 'treeAjax.do' + s : s.replace(/^\/+/, ''));
  const res = await fetch(url, {
    headers: { 'User-Agent': UA, Referer: `${VIEWER}viewer.do`, Accept: 'text/html,application/json;q=0.9,*/*;q=0.8' },
    signal: AbortSignal.timeout(timeoutMs),
    cache: 'no-store',
  });
  const body = await res.text();
  if (res.ok && /^WEBFIREWALL/.test(body)) throw new Error('사이트 방화벽 응답(WEBFIREWALL)');
  return { status: res.status, body };
}

const NODE_RE = /<li\s+data-dataId='([^']+)'\s+data-url\s*='([^']+)'\s*>\s*<span[^>]*title='([^']*)'/g;

export function parseNodes(html) {
  const out = [];
  let m;
  NODE_RE.lastIndex = 0;
  while ((m = NODE_RE.exec(String(html)))) {
    out.push({ id: m[1], q: unescapeHtml(m[2]), name: unescapeHtml(m[3]) });
  }
  return out;
}

const normQuery = (q) => {
  const s = String(q == null ? '' : q).trim();
  if (/^https?:/i.test(s)) return s;
  const i = s.indexOf('?');
  return i > 0 ? s.slice(i) : s.startsWith('?') ? s : '?' + s;
};

export async function tree(dataUrl, { maxNodes = 90, maxDepth = 6, budgetMs = 15000 } = {}) {
  const start = Date.now();
  const docs = [];
  const folders = [];
  let visited = 0;
  let truncated = false;
  const queue = [{ q: normQuery(dataUrl), path: [], depth: 0 }];
  while (queue.length) {
    if (visited >= maxNodes || Date.now() - start > budgetMs) {
      truncated = true;
      break;
    }
    const node = queue.shift();
    visited++;
    let r;
    try {
      const q = /^https?:/i.test(node.q) ? node.q : node.q.startsWith('?') ? 'treeAjax.do' + node.q : node.q;
      r = await getText(q, Math.min(8000, Math.max(2000, budgetMs - (Date.now() - start))));
    } catch (e) {
      folders.push({ path: node.path, error: e.message });
      continue;
    }
    if (r.status !== 200) {
      folders.push({ path: node.path, error: `HTTP ${r.status}` });
      continue;
    }
    for (const n of parseNodes(r.body)) {
      if (n.id.startsWith('G002')) {
        docs.push({ id: n.id, name: n.name, path: node.path.slice(), q: n.q });
      } else if (node.depth < maxDepth) {
        queue.push({ q: n.q, path: node.path.concat(n.name), depth: node.depth + 1 });
      } else {
        truncated = true;
      }
    }
  }
  docs.sort((a, b) => a.path.join('>').localeCompare(b.path.join('>')) || a.name.localeCompare(b.name) || a.id.localeCompare(b.id));
  return { docs, folders, visited, truncated, elapsedMs: Date.now() - start };
}

export async function pageList(q, timeoutMs = 7000) {
  const r = await getText('imgnode.do' + q, timeoutMs);
  if (r.status !== 200) throw new Error(`HTTP ${r.status}`);
  const j = JSON.parse(r.body);
  const imgs = (j.imgItems || []).map((x) => ({ dzi: x.dzi, fn: x.filename }));
  return { title: j.infoTitle || '', pages: imgs.length, imgs };
}

// 여러 문서의 페이지 수를 제한된 동시성으로(사이트 예절: 4)
export async function pagesFor(docs, { max = 12, concurrency = 4, budgetMs = 12000 } = {}) {
  const start = Date.now();
  const out = [];
  let next = 0;
  let failed = 0;
  const worker = async () => {
    while (next < docs.length && out.length < max) {
      const d = docs[next++];
      if (Date.now() - start > budgetMs) return;
      try {
        const p = await pageList(d.q);
        out.push({ ...d, title: p.title || d.name, pages: p.pages });
      } catch {
        failed++;
        out.push({ ...d, title: d.name, pages: null });
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(concurrency, docs.length) }, worker));
  return { rows: out.slice(0, max), failed, elapsedMs: Date.now() - start };
}

export async function probe() {
  const t0 = Date.now();
  try {
    const r = await getText('?itemId=book&gubun=booktree&depth=0&upPath=&dataId=&itemType=', 8000);
    const nodes = parseNodes(r.body);
    return { ok: r.status === 200 && nodes.length > 0, status: r.status, groups: nodes.length, ms: Date.now() - t0 };
  } catch (e) {
    return { ok: false, error: e.message, ms: Date.now() - t0 };
  }
}
