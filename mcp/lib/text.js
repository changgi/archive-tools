// 응답 조립 공통 — 24KB 한도(카카오·PlayMCP 제약) 안에서 항상 유효한 텍스트를 돌려준다.
export const LIMIT_B = 23800;

export const enc = new TextEncoder();
const dec = new TextDecoder('utf-8', { fatal: false });

export const text = (s) => ({ content: [{ type: 'text', text: s }] });

export function byteLen(s) {
  return enc.encode(s).length;
}

// UTF-8 경계에서 자른다(깨진 글자 없음). 자른 사실은 호출부가 문장으로 알린다.
export function cut(s, maxBytes) {
  const str = String(s == null ? '' : s);
  const b = enc.encode(str);
  if (b.length <= maxBytes) return str;
  const head = dec.decode(b.slice(0, Math.max(0, maxBytes - 3)));
  return head.replace(/\uFFFD+$/, '').replace(/[\uD800-\uDBFF]$/, '');
}

export function clamp(res) {
  for (const c of (res && res.content) || []) {
    if (c.type !== 'text' || typeof c.text !== 'string') continue;
    if (byteLen(c.text) <= LIMIT_B) continue;
    c.text = cut(c.text, LIMIT_B - 220)
      + `\n\n…[응답 ${byteLen(c.text)}B → 24KB 한도로 잘림. limit·max_chars를 줄이거나 part로 나눠 다시 요청하세요]`;
  }
  return res;
}

export function oneLine(s, max = 160) {
  const t = String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  return t.length <= max ? t : t.slice(0, max - 1) + '…';
}

// 검색어 주변만 보여 준다(앞에서 자르면 정작 걸린 낱말이 잘리는 경우가 많다)
export function excerpt(field, token, max = 170) {
  const t = String(field == null ? '' : field).replace(/\s+/g, ' ').trim();
  if (!t) return '';
  const at = token ? t.toLowerCase().indexOf(String(token).toLowerCase()) : -1;
  if (at <= Math.max(0, max / 3)) return oneLine(t, max);
  const start = Math.max(0, at - Math.floor(max / 4));
  return '…' + oneLine(t.slice(start), max);
}

export function bullets(rows) {
  return rows.filter(Boolean).join('\n');
}

export function section(title, body) {
  const b = String(body == null ? '' : body).trim();
  return b ? `${title}\n${b}` : '';
}
