# 「고문서 한 장」 전체 산출물을 드라이브용 폴더 구조로 묶는다(ZIP 여러 개, 풀면 같은 archive-tool/ 폴더로 합쳐짐)
#   archive-tool/
#     00_읽어보기.txt · 전체목록.csv
#     01_원본사진/EP.xxx_소장처/01_문서명/001.jpg … + 출처.csv     (자료관 확대 조각을 이어 붙인 최대 해상도)
#     02_영상/EP.xxx_소장처/릴스_9x16.mp4 · 가로_16x9.mp4 · 자막.srt · 포스터   (렌더 원본 화질, 없으면 웹용)
#     03_카드뉴스/EP.xxx_소장처/*.jpg
#     04_비하인드카드/EP.xxx_소장처/*.jpg
#     05_전시·활동지·검토지/EP.xxx_소장처/전시.html · 활동지.html · 검토지.html
#     06_글·데이터/EP.xxx_소장처/README.md · 홍보글.md · 채널별홍보.md · 큐레이터노트.md · 전달에디팅.md · SNS.txt · 판독번역표.csv
#     06_글·데이터/_시리즈 전체/ 분석 데이터 · 데이터 묶음 · 릴스 홍보 문구
#     02_영상/_시리즈 홍보영상/
#   usage: python3 drive_pack.py <종류> [최대MB]   종류: 원본사진 | 영상 | 나머지
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import csv, glob, json, os, re, sys, zipfile
E = (P.REPO + '/examples/'); OUT = (P.DATA + '/out/'); R = 'archive-tool/'
DST = (P.STATE + '/drivepack/'); os.makedirs(DST, exist_ok=True)
IT = [i for i in json.loads(re.search(r'const IT=(\[.*?\]);\n', open(E + 'index.html', encoding='utf-8').read(), re.S).group(1)) if i.get('f')]
C = json.load(open((P.STATE + '/collect.json'), encoding='utf-8'))
safe = lambda s: re.sub(r'[\\/:*?"<>|]', '_', s).strip()


def label(i):
    if not i.get('ep'): return safe('예시_' + re.sub(r'\s*\(.*$', '', i.get('t', i['f'])))[:70]
    coll = (i.get('who') or '').split(' · ')[0] or i['f']
    return safe(f"EP.{i['ep']:03d}_" + coll)[:70]


ORDER = sorted(IT, key=lambda i: (i.get('ep') is not None, i.get('ep') or 0))
LAB = {i['f']: label(i) for i in ORDER}
ID = {i['f']: os.path.basename(i['reel']).split('_reel')[0] for i in ORDER if i.get('reel')}


def items(kind):
    """(압축 안 경로, 실제 파일) 목록"""
    out = []
    for i in ORDER:
        f = i['f']; L = LAB[f]; d = E + f + '/'
        if kind == '원본사진':
            rows = [];  sel = {r['순서']: r for r in csv.DictReader(open(d + 'selection.csv', encoding='utf-8-sig'))}
            for x in [x for x in C if x['folder'] == f]:
                dn = safe(f"{int(x['n']):02d}_{x['name']}")[:80]
                for p in x['pages']:
                    out.append((f'{R}01_원본사진/{L}/{dn}/{os.path.basename(p)}', p))
                    rows.append([f'{dn}/{os.path.basename(p)}', x['name'], sel.get(x['n'], {}).get('연도', ''), sel.get(x['n'], {}).get('자료ID', ''), x.get('link', '')])
            if rows:
                import io; s = io.StringIO(); w = csv.writer(s); w.writerow(['파일', '문서명', '연도', '자료ID', '원본 뷰어']); w.writerows(rows)
                out.append((f'{R}01_원본사진/{L}/출처.csv', ('﻿' + s.getvalue()).encode('utf-8')))
        elif kind == '영상' and f in ID:
            e = ID[f]
            for m, nm in (('reel', '릴스_9x16.mp4'), ('wide', '가로_16x9.mp4')):
                src = OUT + f'{e}_{m}.mp4' if os.path.exists(OUT + f'{e}_{m}.mp4') else P.media_file(f'{e}_{m}.mp4')
                if os.path.exists(src): out.append((f'{R}02_영상/{L}/{nm}', src))
            for src, nm in ((E + f'media/{e}.ko.srt', '자막.srt'), (E + f'media/{e}_reel-poster.jpg', '포스터_릴스.jpg'), (E + f'media/{e}_wide-poster.jpg', '포스터_가로.jpg')):
                if os.path.exists(src): out.append((f'{R}02_영상/{L}/{nm}', src))
        elif kind == '나머지':
            for p in sorted(glob.glob(d + 'cards/*.jpg')): out.append((f'{R}03_카드뉴스/{L}/{os.path.basename(p)}', p))
            for p in sorted(glob.glob(d + 'behind/*.jpg')): out.append((f'{R}04_비하인드카드/{L}/{os.path.basename(p)}', p))
            for a, nm in (('exhibit.html', '전시.html'), ('handout.html', '활동지.html'), ('proof.html', '검토지.html')):
                if os.path.exists(d + a): out.append((f'{R}05_전시·활동지·검토지/{L}/{nm}', d + a))
            for a, nm in (('README.md', 'README.md'), ('promo.md', '홍보글.md'), ('channels.md', '채널별홍보.md'), ('curator.md', '큐레이터노트.md'),
                          ('delivery.md', '전달에디팅.md'), ('sns.txt', 'SNS.txt'), ('selection.csv', '판독번역표.csv')):
                if os.path.exists(d + a): out.append((f'{R}06_글·데이터/{L}/{nm}', d + a))
    if kind == '영상':
        for p in sorted(glob.glob(E + 'media/promo-reel*.mp4') + glob.glob(E + 'media/series-*_reel.mp4') + glob.glob(P.NEXT + '/media/promo-reel*.mp4') + glob.glob(P.NEXT + '/media/series-*_reel.mp4')):
            out.append((f'{R}02_영상/_시리즈 홍보영상/{os.path.basename(p)}', p))
    if kind == '나머지':
        for a in ('analysis-data.json', 'analysis-episodes.csv', 'data.zip', 'media/reels-captions.md', 'README.md', 'CURATOR-NOTE.md', 'PROMOTE.md', 'USE.md'):
            if os.path.exists(E + a): out.append((f'{R}06_글·데이터/_시리즈 전체/{os.path.basename(a)}', E + a))
        rows = [[LAB[i['f']], i.get('t', ''), (i.get('who') or ''), f"https://changgi.github.io/archive-tools/examples/{i['f']}/exhibit.html"] for i in ORDER]
        import io; s = io.StringIO(); w = csv.writer(s); w.writerow(['폴더', '제목', '소장처 · 연대 · 점수', '온라인 전시']); w.writerows(rows)
        out.append((f'{R}전체목록.csv', ('﻿' + s.getvalue()).encode('utf-8')))
        out.append((f'{R}00_읽어보기.txt', README.encode('utf-8')))
    return out


README = f"""「고문서 한 장」 전체 산출물 — {len(ORDER)}편 (편 폴더 이름: EP.번호_소장처)

ZIP을 모두 같은 곳에 풀면 archive-tool/ 폴더 하나로 합쳐집니다. 그 안의 폴더를 구글 드라이브 archive-tool 폴더의 같은 이름 폴더에 끌어다 놓으세요.

01_원본사진        한국고문서자료관 뷰어의 확대 조각을 이어 붙인 최대 해상도 JPG(문서 전체 면). 편마다 출처.csv
02_영상            릴스(9:16) · 가로(16:9) 렌더 원본, 한국어 자막(.srt), 포스터. _시리즈 홍보영상
03_카드뉴스        1080×1350 카드(표지 · 문서별 · 마무리)
04_비하인드카드    큐레이터 노트 카드 3장
05_전시·활동지·검토지  한 파일로 열리는 웹페이지(사진 포함) — 전시 · 수업 활동지(A4 인쇄) · 원본 대조 검토지
06_글·데이터       편 README(판독 · 번역 · 해제 전문) · 홍보 글 · 채널별 홍보안 · 큐레이터 노트 · 전달 에디팅 · SNS 글 · 판독번역표(CSV)
                   _시리즈 전체: 통합 분석 데이터 · 데이터 묶음 · 릴스 홍보 문구 · 기획 노트

이용 조건
- 고문서 이미지(원본사진 · 카드 · 영상 · 웹페이지 속 사진): 한국학중앙연구원 한국고문서자료관 소장 · 제공, 각 소장처. 개인 연구 · 보관은 괜찮지만,
  재사용 · 재배포(게시 · 출판 · 전시 · 공유 링크)는 자료관을 통해 소장처 동의가 필요합니다(031-730-8873, 8876). 문제가 있으면 내립니다.
  → 드라이브 폴더의 공유 범위를 「링크가 있는 모든 사용자」로 바꾸기 전에 동의를 받으세요.
- 판독 · 번역 · 해제 · 이야기 · 노트 · 분석 데이터(텍스트): CC BY 4.0 — Song Chang-gi (chgsong@naver.com · github.com/changgi)
- 판독 · 번역은 이미지에 근거한 초안이며 아직 원본 대조(검토)를 마치지 않았습니다. □ 못 읽은 글자 · (?) 불확실

온라인: https://changgi.github.io/archive-tools/examples/
"""

part = 0
if __name__ == '__main__':
    kind = sys.argv[1]; cap = int(sys.argv[2] if len(sys.argv) > 2 else 380) * 1024 * 1024
    its = items(kind); part, size, z, made = 0, 0, None, []
    import shutil
    FIN = '/mnt/user-data/outputs/드라이브용/'; os.makedirs(FIN, exist_ok=True)
    def done(zz):  # 다 쓴 묶음은 출력 폴더로 옮겨 디스크를 비움
        zz.close(); p = made[-1]; shutil.copy(p, FIN + os.path.basename(p)); os.remove(p); print(os.path.basename(p), round(os.path.getsize(FIN + os.path.basename(p)) / 1e6, 1), 'MB', flush=True)
    def openz():
        global part
        part += 1; p = f'{DST}고문서한장_{kind}_{part:02d}.zip'; made.append(p)
        return zipfile.ZipFile(p, 'w', zipfile.ZIP_STORED)
    for arc, src in its:
        n = len(src) if isinstance(src, bytes) else os.path.getsize(src)
        if z is None or (size + n > cap and size > 0):
            if z: done(z)
            z = openz(); size = 0
        (z.writestr(arc, src) if isinstance(src, bytes) else z.write(src, arc)); size += n
    z and done(z)
    print(kind, len(its), 'files')
