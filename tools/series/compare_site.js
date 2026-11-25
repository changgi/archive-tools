/* 공유판: 편은 data/<편>.json · 사진은 img/<편>/<순서>.jpg, 고친 내용은 db(edits · log)에 함께 저장 */
window.__compareSite = A => {
  const { S, loadEp, renderDocs, renderText, drawBands, toast, esc } = A;
  const $ = s => document.querySelector(s);
  const DATA = JSON.parse(document.getElementById('data').textContent || 'null') || { index: [] };
  const sync = (t, warn) => { const s = $('#sync'); s.textContent = t; s.style.color = warn ? 'var(--red)' : ''; };
  let ALL = null, db = null, me = null, unsub = null, watchKey = null, loadT = null;
  const pushed = {}, busy = {}, lastLocal = {};

  $('#outdl').hidden = true; // 이 화면은 파일 저장을 막음 — 「복사」로
  // 편 고르기
  const sel = $('#ep'); sel.hidden = false;
  sel.innerHTML = '<option value="">편 고르기…</option>' + DATA.index.map(x => `<option value="${esc(x.key)}">${esc(x.ep ? x.ep + ' · ' : '')}${esc(x.title)} (${x.n})</option>`).join('');
  async function open(key) {
    $('#eptitle').textContent = '여는 중…';
    try {
      if (!ALL) { const r = await fetch('data.json'); if (!r.ok) throw new Error(r.status); ALL = await r.json(); }
      const ep = ALL[key]; if (!ep) throw new Error('없는 편');
      if (!ep._img) { // 사진은 편마다 한 묶음(p/<번호>.json)
        try { const r2 = await fetch(`p/${ep.pk}.json`); const pk = r2.ok ? await r2.json() : {}; ep.docs.forEach(d => { d.img = pk[d.n] || ''; }); } catch (e) {}
        ep._img = true;
      } ep.docs.forEach(d => { d.ep = ep.key; });
      if (!S.eps.some(x => x.key === ep.key)) S.eps.push(ep); else S.eps[S.eps.findIndex(x => x.key === ep.key)] = ep;
      loadEp(ep); sel.value = key;
      try { if (location.hash.slice(1) !== key) history.replaceState(null, '', '#' + key); } catch (e) {}
    } catch (e) { $('#eptitle').textContent = '이 편을 열지 못했습니다'; toast('편 파일을 읽지 못했습니다: ' + e.message); }
  }
  sel.onchange = () => sel.value && open(sel.value);
  window.addEventListener('hashchange', () => { const h = decodeURIComponent(location.hash.slice(1)); if (h && h !== (S.ep && S.ep.key) && DATA.index.some(x => x.key === h)) open(h); });
  const w = $('#welcome');
  if (w) {
    w.querySelector('ol li').innerHTML = '위에서 <b>편을 고릅니다</b>(주소 끝에 <code>#폴더이름</code>을 붙여 바로 열 수도 있습니다).';
    w.querySelector('ol li:last-child').innerHTML = '고친 내용은 <b>함께 저장</b>되어 다른 검토자에게도 보이고, 저장소 관리자가 모아 원본 저장소에 반영합니다. 바뀐 칸마다 누가 · 언제 · 무엇을 · 왜 고쳤는지 기록이 남습니다.';
  }

  // 공유 저장
  const keyOf = (ep, n) => `edits/${ep}~${n}`;
  const body = (ep, d, e) => ({ ep, n: d.n, rid: d.id, name: d.name, f: e.f || {}, anchors: (e.anchors || []).map(x => x == null ? -1 : x), dir: e.dir || 'v', pairs: e.pairs || {}, why: e.why || '', done: !!e.done, who: e.who || '', by: me || '', at: e.at || new Date().toISOString() });
  const fromBody = b => ({ f: b.f || {}, anchors: (b.anchors || []).map(x => x < 0 ? null : x), dir: b.dir || 'v', pairs: b.pairs || {}, why: b.why || '', done: !!b.done, who: b.who || '', at: b.at || '' });
  async function push(d) {
    if (!db) return; const ep = d.ep || S.ep.key, k = keyOf(ep, d.n), e = (S.edits[ep] || {})[d.n]; if (!e) return;
    lastLocal[k] = Date.now();
    if (busy[k]) { busy[k] = 'again'; return; }
    busy[k] = true; sync('저장 중…');
    try {
      const b = body(ep, d, e), prev = pushed[k] || { f: {} };
      await db.doc(k).set(b);
      for (const f of new Set([...Object.keys(b.f), ...Object.keys(prev.f || {})])) { // 칸마다 바뀐 것을 기록으로
        const before = f in (prev.f || {}) ? prev.f[f] : (d.f[f] ?? ''), after = f in b.f ? b.f[f] : (d.f[f] ?? '');
        if (before !== after) await db.collection('log').add({ ep, n: d.n, rid: d.id, name: d.name, field: f, before, after, why: b.why, who: b.who, by: me || '', at: new Date().toISOString() });
      }
      if (!!prev.done !== b.done) await db.collection('log').add({ ep, n: d.n, rid: d.id, name: d.name, field: '검토', before: prev.done ? '표시' : '', after: b.done ? '표시' : '', why: '', who: b.who, by: me || '', at: new Date().toISOString() });
      pushed[k] = JSON.parse(JSON.stringify(b)); sync('함께 저장됨');
    } catch (err) {
      const c = err && err.code;
      if (c === 'invalid_argument') sync('보기 권한만 있어 고친 내용은 이 브라우저에만 남습니다 — 「고친 내용 내보내기」로 보관하세요', true);
      else if (c === 'quota_exceeded') sync('공유 저장 공간이 가득 찼습니다 — 관리자에게 알려 주세요', true);
      else sync('저장하지 못했습니다 — 잠시 뒤 다시 고치면 저장됩니다', true);
    }
    const again = busy[k] === 'again'; busy[k] = false; if (again) push(d);
  }
  function watch(key) {
    if (!db || watchKey === key) return;
    unsub && unsub(); watchKey = key; sync('함께 고친 내용을 불러오는 중…');
    clearTimeout(loadT); loadT = setTimeout(() => sync('공유 저장소에 닿지 않습니다 — 고친 내용은 이 브라우저에 남습니다', true), 10000);
    unsub = db.collection('edits').where('ep', '==', key).onSnapshot(snap => {
      if (!snap.metadata.fromCache) clearTimeout(loadT);
      if (!S.ep || S.ep.key !== key) return;
      let touched = false, others = new Set();
      for (const doc of snap.docs) {
        const b = doc.data(); if (!b) continue; const k = keyOf(key, b.n);
        if (b.who) others.add(b.who);
        if (!pushed[k]) pushed[k] = JSON.parse(JSON.stringify(b));
        if (lastLocal[k] && Date.now() - lastLocal[k] < 6000) continue; // 지금 내가 고치는 문서는 그대로
        const cur = (S.edits[key] || {})[b.n];
        if (cur && cur.at && b.at && cur.at > b.at) continue; // 내 쪽이 더 새것
        (S.edits[key] ||= {})[b.n] = fromBody(b); pushed[k] = JSON.parse(JSON.stringify(b)); touched = true;
      }
      if (touched) {
        renderDocs();
        const a = document.activeElement; if (!(a && a.closest && a.closest('#text') && /INPUT|TEXTAREA/.test(a.tagName))) { renderText(); drawBands(); }
      }
      sync(snap.size ? `함께 저장됨 · 이 편에서 고친 문서 ${snap.size}건${others.size ? ' · 검토자 ' + [...others].slice(0, 4).join(', ') : ''}` : '함께 저장됨 · 이 편은 아직 고친 곳이 없습니다');
    }, err => { clearTimeout(loadT); sync('공유 저장을 쓸 수 없습니다 — 고친 내용은 이 브라우저에 남습니다', true); });
  }
  async function hist(d) {
    const ul = $('#hist'); if (!db || !ul || !S.ep) return;
    try {
      const q = await db.collection('log').where('ep', '==', S.ep.key).where('n', '==', d.n).orderBy('at', 'desc').limit(30).get();
      if (S.docs[S.i] !== d) return;
      ul.innerHTML = q.size ? '<li><b>고친 기록</b></li>' + q.docs.map(x => { const b = x.data(); const s = (b.after || '').slice(0, 60);
        return `<li>${esc((b.at || '').slice(0, 16).replace('T', ' '))} · ${esc(b.who || '이름 없음')} · ${esc(b.field)}: ${esc(s)}${(b.after || '').length > 60 ? '…' : ''}${b.why ? ' <small>(근거: ' + esc(b.why.slice(0, 60)) + ')</small>' : ''}</li>`; }).join('') : '';
    } catch (e) {}
  }
  S.remote = { push, watch, hist, me() {} };

  (async () => {
    if (typeof claude === 'undefined' || !claude.use) { sync('공유 저장을 쓸 수 없는 화면입니다 — 고친 내용은 이 브라우저에만 남습니다', true); return; }
    try { db = await claude.use('db'); } catch (e) { db = null; }
    try { const u = await claude.use('user'); me = u ? await u.id() : null; } catch (e) {}
    if (!db) sync('공유 저장을 쓸 수 없는 화면입니다 — 고친 내용은 이 브라우저에만 남습니다(「고친 내용 내보내기」로 보관)', true);
    else { sync('함께 저장 준비됨'); if (S.ep) watch(S.ep.key); }
  })();
  const h = decodeURIComponent(location.hash.slice(1));
  if (h && DATA.index.some(x => x.key === h)) open(h);
};
