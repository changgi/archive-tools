#!/usr/bin/env python3
"""배포 파일 만들기 — dist/aks-archive-harvester.plugin(플러그인) · dist/aks-archive-harvester-skill.zip(스킬만)

  python3 tools/build_dist.py            # 만들기
  python3 tools/build_dist.py --check    # 지금 dist가 소스와 같은지 확인(다르면 종료 코드 1)

같은 소스면 늘 같은 바이트가 나오도록(파일 순서 · 날짜 고정) 만들어, 고칠 때마다 패치 · 저장소가 불필요하게 커지지 않게 합니다.
"""
import io, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUG = os.path.join(ROOT, 'plugins', 'aks-archive-harvester')
SKIP_DIRS = {'__pycache__', '.git'}
SKIP_EXT = ('.pyc', '.pyo')


def files(base, rels):
    out = []
    for rel in rels:
        p = os.path.join(base, rel)
        if os.path.isfile(p): out.append(rel); continue
        for d, ds, fs in os.walk(p):
            ds[:] = sorted(x for x in ds if x not in SKIP_DIRS)
            for f in sorted(fs):
                if f.endswith(SKIP_EXT) or f == '.DS_Store': continue
                out.append(os.path.relpath(os.path.join(d, f), base).replace(os.sep, '/'))
    return sorted(out)


def build(base, rels):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in files(base, rels):
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = (0o755 if rel.endswith('.py') else 0o644) << 16
            zi.flag_bits |= 0x800  # 파일 이름 UTF-8
            z.writestr(zi, open(os.path.join(base, rel), 'rb').read())
    return bio.getvalue()


def main():
    targets = {
        'aks-archive-harvester.plugin': build(PLUG, ['skills', '.claude-plugin', 'README.md']),
        'aks-archive-harvester-skill.zip': build(os.path.join(PLUG, 'skills'), ['aks-archive-harvester']),
    }
    dist = os.path.join(ROOT, 'dist'); os.makedirs(dist, exist_ok=True)
    bad = []
    for name, data in targets.items():
        p = os.path.join(dist, name)
        if '--check' in sys.argv:
            if not os.path.exists(p) or open(p, 'rb').read() != data: bad.append(name)
        else:
            open(p, 'wb').write(data); print(f'→ dist/{name}  {len(data) / 1024:.0f}KB')
    if '--check' in sys.argv:
        print('dist가 소스와 같습니다' if not bad else 'dist가 소스와 다릅니다(python3 tools/build_dist.py): ' + ', '.join(bad))
        sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
