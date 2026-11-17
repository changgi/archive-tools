#!/usr/bin/env python3
"""CHANGELOG.md에서 한 버전의 기록만 꺼내기 — 릴리스 노트용.  python3 tools/changelog_section.py 1.7.1"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
v = (sys.argv[1] if len(sys.argv) > 1 else '').lstrip('v')
t = open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8').read()
m = re.search(rf'^## aks-archive-harvester {re.escape(v)} .*?\n(.*?)(?=^## |\Z)', t, re.S | re.M)
if not m: sys.exit(f'CHANGELOG에 {v}가 없습니다')
print(m.group(1).strip() + '\n\n— 설치: Claude Code에서 `/plugin marketplace add changgi/archive-tools` → `/plugin install aks-archive-harvester@changgi-archive-tools`, 또는 아래 `.plugin` · 스킬 ZIP')
