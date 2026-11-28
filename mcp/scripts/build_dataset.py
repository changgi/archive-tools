#!/usr/bin/env python3
"""archive-tools 원격 MCP 서버의 큐레이션 데이터셋(mcp/data/curation.json)을 저장소의 실제 산출물에서 만든다.

입력(모두 저장소에 커밋된 실제 파일 — 새로 지어내는 값 없음)
  examples/<편>/selection.csv   판독 · 원문 · 번역 · 해제 · 요약 · 이야기 · 캡션 · 인물 · 검토
  examples/<편>/record.json     기록 꾸러미(맥락 · 소장처 · 출처 · 고정값)
  examples/<편>/curator.md      큐레이터 노트
  examples/analysis-data.json   통합 분석 집계(편 200 · 문서 726 · 인용 763 · 판독 한자 44,093)
  examples/viewer-data.json     IIIF 뷰어 목록(편별 캔버스)
  plugins/.../scripts/studio.py GLOSSARY(문서 유형 사전) · find_quotes(인용 추출)

출력
  mcp/data/curation.json        MCP 도구가 읽는 단일 데이터셋
  mcp/data/glossary.json        문서 유형 사전(studio.py GLOSSARY 그대로)

같은 저장소 상태면 같은 바이트가 나온다(정렬 고정 · 시각 값 없음).
  python3 mcp/scripts/build_dataset.py [--repo <저장소 루트>]
"""
import argparse
import csv
import glob
import hashlib
import importlib.util
import json
import os
import re

GITHUB = 'https://changgi.github.io/archive-tools'
EXAMPLES = GITHUB + '/examples'
IIIF = 'https://changgi.github.io/archive-tools-next/iiif'


def load_module(repo, name):
    p = os.path.join(repo, 'plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/%s.py' % name)
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def load_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def section(md, heading):
    """curator.md의 '## 제목' 절 본문(다음 '## ' 전까지) — 없으면 빈 문자열."""
    if not md:
        return ''
    m = re.search(r'^##\s*' + re.escape(heading) + r'\s*$(.*?)(?=^##\s)', md, re.S | re.M)
    if not m:
        return ''
    body = re.sub(r'<!--.*?-->', '', m.group(1), flags=re.S)
    return re.sub(r'\s+', ' ', body).strip()


def year_of(cell):
    m = re.search(r'(?<!\d)(\d{4})(?!\d)', str(cell or ''))
    if not m:
        return None
    y = int(m.group(1))
    return y if 1000 <= y <= 2100 else None


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--repo', default=os.path.abspath(os.path.join(here, '..', '..')))
    ap.add_argument('--out', default=os.path.abspath(os.path.join(here, '..', 'data')))
    a = ap.parse_args()
    repo = a.repo
    studio = load_module(repo, 'studio')
    analysis_mod = load_module(repo, 'analysis')  # persons_of — people.html 인물 찾아보기와 같은 규칙
    ex = os.path.join(repo, 'examples')

    analysis = load_json(os.path.join(ex, 'analysis-data.json'), {}) or {}
    ep_meta = {e['episode']: e for e in analysis.get('episodes', [])}
    viewer = load_json(os.path.join(ex, 'viewer-data.json'), {}) or {}
    iiif_eps = {e['f'] for e in viewer.get('eps', [])}

    episodes, docs = [], []
    for sel in sorted(glob.glob(os.path.join(ex, '*', 'selection.csv'))):
        slug = os.path.basename(os.path.dirname(sel))
        rows = read_csv(sel)
        if not rows:
            continue
        base = os.path.dirname(sel)
        record = load_json(os.path.join(base, 'record.json'), {}) or {}
        curator = ''
        cp = os.path.join(base, 'curator.md')
        if os.path.exists(cp):
            curator = open(cp, encoding='utf-8').read()
        ep_raw = record.get('episode') or None
        ep = ('EP.%02d' % int(re.sub(r'\D', '', ep_raw))) if ep_raw else None  # EP.1 → EP.01 (analysis-data.json 표기)
        meta = ep_meta.get(ep, {}) if ep else {}
        coll = (record.get('context') or {}).get('collection') or meta.get('collection') or ''
        holder = (record.get('context') or {}).get('holder') or coll
        first = len(docs)
        years = set()
        for row in rows:
            order = int(row.get('순서') or 0)
            year = year_of(row.get('연도'))
            if year:
                years.add(year)
            docs.append({
                'id': (row.get('자료ID') or '').strip(),
                'ep': ep,
                'slug': slug,
                'o': order,
                'title': re.sub(r'\s+', ' ', (row.get('문서명') or '').strip()),
                'year': year,
                'type': (row.get('문서유형') or '').strip(),
                'tdesc': (row.get('유형설명') or '').strip(),
                'persons': [x.strip() for x in (row.get('인물') or '').split(';') if x.strip()],
                'caption': (row.get('캡션') or '').strip(),
                'story': (row.get('이야기') or '').strip(),
                'read': (row.get('판독') or '').strip(),
                'original': (row.get('원문') or '').strip(),
                'translation': (row.get('번역') or '').strip(),
                'note': (row.get('해제') or '').strip(),
                'summary': (row.get('요약') or '').strip(),
                'review': (row.get('검토') or '').strip(),
                'viewer': (row.get('뷰어링크') or '').strip(),
                'img': (row.get('이미지') or '').strip(),
                'shared': (row.get('공유이미지') or '').strip(),
            })
        episodes.append({
            'ep': ep,
            'n': int(re.sub(r'\D', '', ep)) if ep else 0,
            'slug': slug,
            'title': re.sub(r'\s+', ' ', record.get('title') or meta.get('title') or slug),
            'collection': coll,
            'holder': holder,
            'kind': meta.get('kind') or '',
            'region': meta.get('region') or '',
            'purpose': re.sub(r'\s+', ' ', (record.get('context') or {}).get('purpose') or ''),
            'message': meta.get('message') or '',
            'question': meta.get('question') or '',
            'emotion': meta.get('emotion') or '',
            'wish': section(curator, '전하고 싶은 것'),
            'backstage': section(curator, '만들며 있었던 일'),
            'years': sorted(years),
            'docs': len(rows),
            'first': first,
            'iiif': IIIF + '/' + slug + '/' if slug in iiif_eps else '',
        })

    episodes.sort(key=lambda e: (e['n'] == 0, e['n'], e['slug']))
    docs.sort(key=lambda d: (d['ep'] is None, int(re.sub(r'\D', '', d['ep'] or '0') or 0), d['o'], d['id']))
    for e in episodes:  # 정렬 뒤 편의 첫 문서 위치
        e['first'] = next(i for i, d in enumerate(docs) if d['slug'] == e['slug'])

    by_key = {(d['slug'], d['o']): i for i, d in enumerate(docs)}
    quotes = []
    for sel in sorted(glob.glob(os.path.join(ex, '*', 'selection.csv'))):
        slug = os.path.basename(os.path.dirname(sel))
        for row in read_csv(sel):
            i = by_key.get((slug, int(row.get('순서') or 0)))
            if i is None:
                continue
            for h, o, _ in studio.find_quotes((row.get('이야기') or '').strip()):
                quotes.append({'h': h, 'o': o, 'd': i})
    quotes.sort(key=lambda q: (q['d'], q['h'], q['o']))

    people = {}
    for i, d in enumerate(docs):
        for p in analysis_mod.persons_of({'인물': '; '.join(d['persons']), '문서명': d['title']}):
            people.setdefault(p, set()).add(i)
    people_list = [[k, sorted(v)] for k, v in sorted(people.items(), key=lambda kv: (-len(kv[1]), kv[0]))]

    data = {
        'schema': 'archive-tools-mcp/1.0',
        'source': {
            'repo': 'https://github.com/changgi/archive-tools',
            'gallery': EXAMPLES + '/',
            'archive': '한국학중앙연구원 한국고문서자료관 (https://archive.aks.ac.kr)',
            'series': '「고문서 한 장」 — 원문으로 읽는 옛 문서 이야기',
            'license': '판독·번역·해제·이야기·노트 텍스트 CC BY 4.0 · 코드 MIT · 고문서 이미지는 소장처 동의 필요',
        },
        'counts': {
            'episodes': sum(1 for e in episodes if e['ep']),
            'episodes_pre_series': sum(1 for e in episodes if not e['ep']),
            'docs': sum(1 for d in docs if d['ep']),
            'docs_pre_series': sum(1 for d in docs if not d['ep']),
            'collections': analysis.get('colls'),
            'span': analysis.get('span'),
            'hanja': analysis.get('han'),
            'quotes': len(quotes),
            'quotes_series': sum(1 for q in quotes if docs[q['d']]['ep']),
            'people': len(people_list),
            'types': len({d['type'] for d in docs if d['type']}),
        },
        'reading': analysis.get('reading') or {},
        'summary_text': analysis.get('summary_text') or [],
        'episodes': episodes,
        'docs': docs,
        'quotes': quotes,
        'people': people_list,
    }

    os.makedirs(a.out, exist_ok=True)
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(a.out, 'curation.json'), 'w', encoding='utf-8') as f:
        f.write(blob)
    with open(os.path.join(a.out, 'glossary.json'), 'w', encoding='utf-8') as f:
        json.dump({'glossary': [{'term': k, 'meaning': v} for k, v in studio.GLOSSARY.items()],
                   'read_guide': [{'term': t, 'guide': g} for t, g in getattr(studio, 'READ_GUIDE', [])]},
                  f, ensure_ascii=False, indent=1)

    print('docs %d (편 %d · 번호 전 %d) · 인용 %d · 인물 %d · 유형 %d · %.1fKB · sha256 %s' % (
        len(docs), data['counts']['episodes'], data['counts']['episodes_pre_series'], len(quotes),
        data['counts']['people'], data['counts']['types'], len(blob.encode()) / 1024,
        hashlib.sha256(blob.encode()).hexdigest()[:16]))


if __name__ == '__main__':
    main()
