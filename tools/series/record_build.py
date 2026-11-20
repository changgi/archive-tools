# 편마다 기록 꾸러미(record.json · checksums.sha256)와 전체 색인(examples/records.jsonl · records-dc.csv)을 만든다.
#   갤러리(examples/index.html의 IT)에서 편 번호 · 제목 · 소장처 · 앞뒤 편을, curator.json에서 만든 목적을 가져와
#   studio.py record --meta 로 넘긴다. 바뀐 것이 없으면 이력(events)에 아무것도 더하지 않는다.
#   python3 tools/series/record_build.py [--verify]
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import json, os, re, subprocess, sys
EX = P.REPO + '/examples'
STUDIO = P.SCRIPTS + '/studio.py'
RIGHTS = ('고문서 이미지: 한국학중앙연구원 한국고문서자료관 소장 · 제공(각 소장처 기탁). '
          '다시 쓰려면 자료관을 통한 소장처 동의가 필요하며, 문제가 있으면 내립니다.')
SKIP = ['/tutorial/']  # 따라하기 예제는 편이 아님

def metas():
    s = open(EX + '/index.html', encoding='utf-8').read()
    IT = json.loads(re.search(r'const IT\s*=\s*(\[.*?\]);\s*\n', s, re.S).group(1))
    IT = [x for x in IT if x.get('f') and os.path.isdir(f"{EX}/{x['f']}")]
    cur = {}
    p = P.DATA + '/curator.json'
    if os.path.exists(p): cur = json.load(open(p, encoding='utf-8'))
    out = {}
    for i, x in enumerate(IT):
        f = x['f']; ep = x.get('ep')
        c = cur.get(f, {}) or {}
        out[f] = {k: v for k, v in dict(
            title=re.sub(r'<[^>]+>', '', x.get('t') or ''),
            identifier=f'gomunseo-hanjang/{f}',
            episode=(f'EP.{ep}' if ep not in (None, 'None') else None),
            series='「고문서 한 장」 — 원문으로 읽는 옛 문서 이야기',
            collection=(x.get('who') or '').split(' · ')[0] or None,
            holder=(x.get('who') or '').split(' · ')[0] or None,
            purpose=c.get('message') or (x['dv'].get('message') if isinstance(x.get('dv'), dict) else None),
            previous=IT[i - 1]['f'] if i else None,
            next=IT[i + 1]['f'] if i + 1 < len(IT) else None).items() if v}
    return out

if __name__ == '__main__':
    if '--verify' in sys.argv:
        sys.exit(subprocess.run(['python3', STUDIO, 'record', '--verify', '--in', EX, '--media', EX + '/media', '--exclude'] + SKIP).returncode)
    m = metas(); mp = os.path.join(P.STATE, 'record_meta.json')
    json.dump(m, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    r = subprocess.run(['python3', STUDIO, 'record', '--in', EX, '--media', EX + '/media', '--exclude'] + SKIP + ['--meta', mp,
                        '--agent', 'Claude (Anthropic) — 판독 · 번역 · 해제 · 이야기 초안, 산출물 제작',
                        '--creator', 'Song Chang-gi (chgsong@naver.com, github.com/changgi)',
                        '--license', 'CC BY 4.0 (이 시리즈가 새로 만든 텍스트) · MIT (코드)',
                        '--rights-images', RIGHTS, '--index', EX + '/records'] + (['--date', os.environ['RECORD_DATE']] if os.environ.get('RECORD_DATE') else []),
                       capture_output=True, text=True)
    print('\n'.join((r.stdout + r.stderr).strip().splitlines()[-2:]))
    sys.exit(r.returncode)
