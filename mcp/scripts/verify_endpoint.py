#!/usr/bin/env python3
"""archive-tools MCP 운영 엔드포인트 실측 점검.

  initialize · tools/list · 주요 도구 실호출 · 같은 질의 여러 번 실행해 바이트 일치 확인
  24KB 한도 · JSON 유효성 · stateless(세션 헤더 없이 매 요청) 확인

  python3 mcp/scripts/verify_endpoint.py --url http://127.0.0.1:3111/api/mcp
  python3 mcp/scripts/verify_endpoint.py --url https://archive-tools-mcp.vercel.app/api/mcp --repeat 5
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request

LIMIT = 23800


def post(url, payload, timeout=120):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST', headers={
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'MCP-Protocol-Version': '2025-06-18',
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode('utf-8', 'replace')
            return r.status, dict(r.headers), body, time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode('utf-8', 'replace'), time.time() - t0


def parse(body):
    s = body.strip()
    if s.startswith('{'):
        return json.loads(s)
    out = []
    for blk in s.split('\n\n'):
        for line in blk.splitlines():
            if line.startswith('data:'):
                out.append(json.loads(line[5:].strip()))
    return out[-1] if out else {}


class Probe:
    def __init__(self, url):
        self.url = url
        self.results = []
        self.calls = 0

    def rpc(self, method, params, ident=None):
        self.calls += 1
        ident = ident or self.calls
        st, h, body, dt = post(self.url, {'jsonrpc': '2.0', 'id': ident, 'method': method, 'params': params})
        if st != 200:
            raise RuntimeError(f'{method} HTTP {st}: {body[:300]}')
        msg = parse(body)
        if 'error' in msg:
            raise RuntimeError(f'{method} JSON-RPC error: {msg["error"]}')
        return msg.get('result', {}), dt, h

    def tool(self, name, args=None):
        res, dt, _ = self.rpc('tools/call', {'name': name, 'arguments': args or {}})
        txt = '\n'.join(c.get('text', '') for c in res.get('content', []) if c.get('type') == 'text')
        raw = json.dumps(res, ensure_ascii=False, sort_keys=True).encode()
        return txt, dt, hashlib.sha256(raw).hexdigest()[:12], bool(res.get('isError'))

    def check(self, label, fn, repeat=1, expect=None, stable=True):
        texts, times, hashes = [], [], []
        err = ''
        for _ in range(repeat):
            try:
                t, dt, h, iserr = fn()
            except Exception as e:  # noqa: BLE001 — 점검 스크립트는 실패를 모아 보고한다
                err = str(e)
                break
            texts.append(t)
            times.append(dt)
            hashes.append(h)
            if iserr:
                err = 'isError=true: ' + t[:200]
        size = max((len(t.encode()) for t in texts), default=0)
        ok = not err and size <= LIMIT and (expect is None or expect in texts[0]) and len(set(hashes)) == 1
        if not stable:
            ok = not err and size <= LIMIT
        self.results.append((label, ok, size, min(times) if times else 0, len(set(hashes)), err or ''))
        return texts, hashes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:3111/api/mcp')
    ap.add_argument('--repeat', type=int, default=3, help='바이트 일치 확인을 위한 반복 횟수')
    ap.add_argument('--skip-live', action='store_true', help='aks_* 실시간 호출 건너뛰기')
    a = ap.parse_args()
    p = Probe(a.url)
    head = []

    # 1) initialize — 세션 없이
    res, dt, h = p.rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'verify', 'version': '1.0'}})
    proto = res.get('protocolVersion')
    info = res.get('serverInfo') or {}
    instr = res.get('instructions') or ''
    head.append(f'protocol={proto} · server={info.get("name")}/{info.get("version")} · instructions={len(instr)}자 · session_header={"yes" if h.get("Mcp-Session-Id") else "none(stateless)"}')
    print('initialize:', head[-1])
    assert proto == '2025-06-18', f'protocolVersion {proto}'

    # 2) tools/list
    res, dt, _ = p.rpc('tools/list', {})
    tools = res.get('tools', [])
    print(f'tools/list: {len(tools)}종')
    bad = []
    for t in tools:
        an = t.get('annotations') or {}
        line = f'  - {t["name"]:18s} desc {len(t.get("description","")):4d}자  readOnly={an.get("readOnlyHint")} idempotent={an.get("idempotentHint")} openWorld={an.get("openWorldHint")}'
        print(line)
        if not (an.get('readOnlyHint') is True and an.get('idempotentHint') is True and an.get('openWorldHint') is True):
            bad.append(t['name'])
        if len(t.get('description', '')) > 1024:
            bad.append(t['name'] + '(설명 1024자 초과)')
    p.results.append(('tools/list (12종 · readOnly/idempotent/openWorld · 설명 ≤1024자)', len(tools) == 12 and not bad, 0, dt, 1, ','.join(bad)))

    N = a.repeat
    p.check('curation_search("유관순") — 데이터에 없을 때 정직한 0건 안내', lambda: p.tool('curation_search', {'query': '유관순'}), N, expect='맞는 문서가 없습니다')
    p.check('curation_search("송준길") — 번호 전 예시로 자동 확장', lambda: p.tool('curation_search', {'query': '송준길'}), N, expect='번호 전 기획 예시')
    p.check('curation_search("이언적")', lambda: p.tool('curation_search', {'query': '이언적'}), N, expect='큐레이션 검색')
    p.check('curation_search(type="홍패", limit=5)', lambda: p.tool('curation_search', {'type': '홍패', 'limit': 5}), N, expect='홍패')
    p.check('curation_search(query="혼인 납폐서")', lambda: p.tool('curation_search', {'query': '혼인 납폐서'}), N, expect='검색')
    p.check('curation_item(id="EP.01#1")', lambda: p.tool('curation_item', {'id': 'EP.01#1'}), N, expect='■ 판독')
    p.check('curation_item(id=자료ID, part="reading")', lambda: p.tool('curation_item', {'id': 'G002+AKS+KSM-XA.1895.1111-20101008.B038a_058_00001_XXX', 'part': 'reading'}), N, expect='■ 원문')
    p.check('curation_episode("EP.124")', lambda: p.tool('curation_episode', {'episode': 'EP.124'}), N, expect='■ 문서 목록')
    p.check('curation_people("최진립")', lambda: p.tool('curation_people', {'query': '최진립'}), N, expect='최진립')
    p.check('curation_timeline(1592~1598)', lambda: p.tool('curation_timeline', {'year_from': 1592, 'year_to': 1598}), N, expect='연표')
    p.check('curation_quotes("농사")', lambda: p.tool('curation_quotes', {'query': '농사'}), N, expect='원문 인용')
    p.check('doc_type("홍패")', lambda: p.tool('doc_type', {'query': '홍패'}), N, expect='■ 홍패')
    p.check('curation_stats()', lambda: p.tool('curation_stats'), N, expect='sha256')
    p.check('aks_catalog(group="문중", region="경주")', lambda: p.tool('aks_catalog', {'group': '문중', 'region': '경주'}), N, expect='소장처')
    p.check('aks_find("독락당")', lambda: p.tool('aks_find', {'query': '독락당'}), N, expect='독락당')
    p.check('health()', lambda: p.tool('health'), N, expect='데이터 지문')
    if not a.skip_live:
        p.check('aks_manifest("경주 옥산 여주이씨 독락당", limit=10, pages=3)',
                lambda: p.tool('aks_manifest', {'name': '경주 옥산 여주이씨 독락당', 'limit': 10, 'pages': 3}), 1, expect='문서')
        p.check('health(probe=true)', lambda: p.tool('health', {'probe': True}), 1, expect='자료관 접속', stable=False)

    print('\n%-52s %-5s %8s %6s %4s %s' % ('점검', '결과', '최대B', '초', '해시', '비고'))
    ok_all = True
    for label, ok, size, dt, nh, err in p.results:
        ok_all = ok_all and ok
        print('%-52s %-5s %8d %6.2f %4d %s' % (label, 'PASS' if ok else 'FAIL', size, dt, nh, err[:120]))
    n_ok = sum(1 for r in p.results if r[1])
    print(f'\nRESULT: {"PASS" if ok_all else "FAIL"} — {n_ok}/{len(p.results)}건 · 같은 질의 {a.repeat}회 실행 바이트 일치(해시 1개)')
    sys.exit(0 if ok_all else 1)


if __name__ == '__main__':
    main()
