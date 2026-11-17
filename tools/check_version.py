#!/usr/bin/env python3
"""버전이 한 곳에서만 바뀌지 않았는지 — plugin.json · marketplace.json(두 곳) · CHANGELOG 맨 위 · CITATION.cff가 같은지 확인"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
pj = json.load(open('plugins/aks-archive-harvester/.claude-plugin/plugin.json', encoding='utf-8'))['version']
mk = json.load(open('.claude-plugin/marketplace.json', encoding='utf-8'))
mv = {mk.get('metadata', {}).get('version'), *[p.get('version') for p in mk.get('plugins', []) if p.get('name') == 'aks-archive-harvester']} - {None}
ch = re.search(r'^## aks-archive-harvester (\S+)', open('CHANGELOG.md', encoding='utf-8').read(), re.M).group(1)
cf = re.search(r'^version:\s*(\S+)', open('CITATION.cff', encoding='utf-8').read(), re.M) if os.path.exists('CITATION.cff') else None
vs = {'plugin.json': pj, 'CHANGELOG': ch, **({'CITATION.cff': cf.group(1)} if cf else {}), **{f'marketplace.json({i})': v for i, v in enumerate(sorted(mv))}}
ok = len(set(vs.values())) == 1
print(('버전 일치: ' + pj) if ok else '버전 불일치: ' + ' · '.join(f'{k} {v}' for k, v in vs.items()))
sys.exit(0 if ok else 1)
