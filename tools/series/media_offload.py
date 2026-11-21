# 영상(mp4)을 archive-tools-next 저장소로 옮기고, 예시 사이트의 영상 링크를 그쪽 주소로 바꾼다.
#   GitHub Pages는 사이트 하나를 1GB까지만 올려 주므로, 가장 큰 영상만 따로 둔다(포스터 · 자막 · 카드는 그대로).
#   - examples/media/*.mp4 → $SERIES_NEXT/media/ (같은 이름, 이미 있으면 내용이 같을 때만 지움)
#   - examples 아래 html · md · json · js · xml · txt · csv · jsonl와 저장소 README의
#     media/<이름>.mp4 · ../media/… · https://changgi.github.io/archive-tools/examples/media/… → NEXT_URL<이름>.mp4
#   여러 번 돌려도 같은 결과(이미 바꾼 주소는 건드리지 않음). site_build.sh가 빌드 끝에 부른다.
#   python3 tools/series/media_offload.py [--dry-run]
import _paths as P
import filecmp, glob, os, re, shutil, sys

EX = os.path.join(P.REPO, 'examples')
SRC = os.path.join(EX, 'media')
DST = os.path.join(P.NEXT, 'media')
DRY = '--dry-run' in sys.argv
RX = re.compile(r'(?<![\w/.\-])(?:https://changgi\.github\.io/archive-tools/examples/|(?:\.\./)+|\./)?(?:examples/)?media/([\w\-]+\.mp4)')
TEXT = ('.html', '.md', '.json', '.js', '.xml', '.txt', '.csv', '.jsonl')

def main():
    if not os.path.isdir(P.NEXT):
        sys.exit(f'✗ {P.NEXT} 가 없습니다 — git clone https://github.com/changgi/archive-tools-next 또는 SERIES_NEXT로 위치를 알려 주세요')
    os.makedirs(DST, exist_ok=True)
    moved = 0
    for f in sorted(glob.glob(os.path.join(SRC, '*.mp4'))):
        d = os.path.join(DST, os.path.basename(f))
        if os.path.exists(d) and not filecmp.cmp(f, d, shallow=False):
            print(f'  바뀐 영상 덮어씀: {os.path.basename(f)}')
        if not DRY:
            shutil.copy2(f, d); os.remove(f)
        moved += 1
    names = {os.path.basename(x) for x in glob.glob(os.path.join(DST, '*.mp4'))}
    files = [os.path.join(P.REPO, 'README.md')] + [p for p in glob.glob(os.path.join(EX, '**', '*'), recursive=True)
                                                  if p.endswith(TEXT) and '/tutorial/' not in p.replace(os.sep, '/')
                                                  and os.path.basename(p) not in ('record.json', 'records.jsonl', 'records-dc.csv')]  # 기록 꾸러미는 record가 직접 씀
    changed = 0; links = 0
    for p in files:
        try: s = open(p, encoding='utf-8').read()
        except (UnicodeDecodeError, IsADirectoryError): continue
        n = [0]
        def rep(m):
            if m.group(1) not in names: return m.group(0)  # 옮기지 않은 영상(따라하기 예제 등)은 그대로
            n[0] += 1; return P.NEXT_URL + m.group(1)
        t = RX.sub(rep, s)
        if t != s:
            changed += 1; links += n[0]
            if not DRY: open(p, 'w', encoding='utf-8').write(t)
    if not DRY:  # 영상 저장소 첫 화면(목록) — 사람이 열어 봐도 무엇인지 알 수 있게
        import html as H
        fs = sorted(names)
        rows = ''.join(f'<li><a href="media/{H.escape(f)}">{H.escape(f)}</a> <small>{os.path.getsize(os.path.join(DST, f)) // 1024:,} KB</small></li>' for f in fs)
        open(os.path.join(P.NEXT, 'index.html'), 'w', encoding='utf-8').write(
            '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>archive-tools-next — 「고문서 한 장」 영상</title><meta name="robots" content="noindex">'
            '<style>body{font:16px/1.6 system-ui,sans-serif;max-width:860px;margin:40px auto;padding:0 16px;color:#222}li{margin:2px 0}small{color:#777}</style></head>'
            '<body><main><h1>「고문서 한 장」 영상 저장소</h1><p>이 저장소는 <a href="https://changgi.github.io/archive-tools/examples/">「고문서 한 장」 갤러리</a>의 영상만 둡니다. '
            '영상은 갤러리에서 보세요. 고문서 이미지는 한국학중앙연구원 한국고문서자료관 소장 · 제공이며, 다시 쓰려면 소장처 동의가 필요합니다.</p>'
            f'<h2>영상 {len(fs)}개</h2><ul>{rows}</ul></main></body></html>')
        open(os.path.join(P.NEXT, '.nojekyll'), 'a').close()
    sz = sum(os.path.getsize(x) for x in glob.glob(os.path.join(DST, '*.mp4'))) / 1e6
    print(f'■ 영상 옮김 {moved}개 · archive-tools-next/media {len(names)}개 {sz:.0f}MB · 링크 {links}곳({changed}개 파일) → {P.NEXT_URL}' + (' (시험)' if DRY else ''))

if __name__ == '__main__':
    main()
