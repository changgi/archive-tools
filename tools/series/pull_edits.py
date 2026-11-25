# 원문 대조 편집기 공유판 db의 edits 컬렉션(문서 목록 JSON) → studio.py fix --from 용 JSON
#   python3 tools/series/pull_edits.py edits.json [data.json] > corrections-shared.json
#   python3 plugins/.../scripts/studio.py fix --from corrections-shared.json --in examples [--apply]
import _paths as P
import sys, json
ed = json.load(open(sys.argv[1], encoding='utf-8'))
ed = ed.get('docs', ed) if isinstance(ed, dict) else ed
data = json.load(open(sys.argv[2] if len(sys.argv) > 2 else (__import__('os').environ.get('SERIES_COMPARE_OUT') or P.STATE + '/compare_site') + '/data.json', encoding='utf-8'))
items, align, rev = [], {}, []
for x in ed:
    b = x.get('data', x)
    ep = data.get(b['ep']); d = next((d for d in ep['docs'] if d['n'] == str(b['n'])), None) if ep else None
    if not d: print('찾지 못함', b.get('ep'), b.get('n'), file=sys.stderr); continue
    for f, v in (b.get('f') or {}).items():
        if v != d['f'].get(f, ''): items.append({'편': b['ep'], '자료ID': d['id'], '순서': d['n'], '문서명': d['name'], '칸': f, '이전': d['f'].get(f, ''), '이후': v, '근거': b.get('why', ''), '검토자': b.get('who', '')})
    an = [a for a in (b.get('anchors') or [])]
    if any(a is not None and a >= 0 for a in an) or b.get('pairs'):
        align[d['id'] or b['ep'] + '#' + d['n']] = {'편': b['ep'], '순서': d['n'], '방향': b.get('dir', 'v'), '줄자리': [a if a is not None and a >= 0 else None for a in an], '짝': b.get('pairs') or {}}
    if b.get('done') and b.get('who'): rev.append({'편': b['ep'], '자료ID': d['id'], '순서': d['n'], '검토자': b['who'], '날짜': (b.get('at') or '')[:10]})
json.dump({'도구': '원문 대조 편집기(공유판)', '판': 1, '고침': items, '줄맞춤': align, '검토': rev}, sys.stdout, ensure_ascii=False, indent=1)
print(f'고친 칸 {len(items)} · 줄맞춤 {len(align)} · 검토 {len(rev)}', file=sys.stderr)
