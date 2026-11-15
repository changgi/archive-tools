#!/usr/bin/env python3
"""영상 — 테마 하나로 릴스(9:16)·가로(16:9) 영상과 자막을 만든다.

  python3 video.py --work W --theme T [--format both|reel|wide] [--ep 7] [--url 전시주소]
                   [--voice ko-KR-SunHiNeural] [--no-tts] [--max-docs 6] [--web]

장면: 열기(전달 에디팅 '열기' 또는 제목) → 소개 → 문서마다 이미지 + 원문 인용 → 절정(원문 한 줄)
      → 비하인드(큐레이터 노트) → 질문 · 출처.  내레이션은 edge-tts(설치되어 있으면), 없으면
      글 길이로 시간을 정한 무음 영상. 자막은 화면에 넣고 .srt로도 저장.
결과: WORK/mediate/<테마>/video/<id>_reel.mp4 · _wide.mp4 · .ko.srt · .ko.vtt  (--web: 540p 압축본도)
필요: ffmpeg, Pillow (+ 선택: pip install edge-tts)
"""
import argparse, asyncio, csv, glob, json, os, re, shutil, subprocess, sys

for _s in (sys.stdout, sys.stderr):  # Windows에서 출력을 파일·파이프로 보낼 때(cp949) 기호 때문에 멈추지 않게
    try: _s.reconfigure(errors='replace')
    except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio as ST
from PIL import Image, ImageDraw

BG = (22, 19, 15)


def wide_frame(img, label, big, sub, out, foot):
    W, H = 1920, 1080; c = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(c)
    if img and os.path.exists(img):
        im = Image.open(img).convert('RGB'); im.thumbnail((860, 740)); c.paste(im, (90 + (860 - im.width) // 2, 80 + (740 - im.height) // 2))
        x0 = 1000
    else:
        x0 = 160
    tw = W - x0 - 110; y = 230
    d.text((x0, y), label, font=ST.font(34, 'bold'), fill=ST.GOLD); y += 70
    fb = ST.font(66 if len(big) < 40 else 54, 'serif')
    for ln in ST.wrap(d, big, fb, tw)[:5]: d.text((x0, y), ln, font=fb, fill=ST.PAPER); y += int(fb.size * 1.35)
    _sub(c, d, sub, W, H - 95, 1500)
    d.text((90, H - 62), foot[:110], font=ST.font(24), fill=(150, 140, 120))
    d.text((90, 44), 'ARCHIVE TOOLS', font=ST.font(26, 'bold'), fill=ST.GOLD)
    c.save(out)


def reel_frame(img, label, big, sub, out, foot):
    ST.note_card(label, big, [], out, img=img, foot=foot, size=(1080, 1920), big_size=72 if len(big) < 30 else 58, center=True)
    c = Image.open(out); d = ImageDraw.Draw(c); _sub(c, d, sub, 1080, 1560, 940)
    d.text((70, 110), 'ARCHIVE TOOLS', font=ST.font(28, 'bold'), fill=ST.GOLD); c.save(out)


def _sub(c, d, text, W, ybot, width):
    if not text: return
    f = ST.font(40); ls = ST.wrap(d, text, f, width)[:3]; h = len(ls) * 58 + 36
    box = Image.new('RGBA', (width + 60, h), (0, 0, 0, 175)); c.paste(box, ((W - width - 60) // 2, ybot - h), box)
    for k, ln in enumerate(ls): d.text((W // 2, ybot - h + 18 + k * 58), ln, font=f, fill=(250, 245, 235), anchor='ma')


def scenes(work, theme, ep, url, max_docs):
    ed = os.path.join(work, 'edit', theme)
    if not os.path.exists(os.path.join(ed, 'selection.csv')):
        sys.exit(f'{ed}/selection.csv가 없습니다. 테마 이름을 확인하거나 먼저 studio.py edit 를 실행하세요.')
    sel = list(csv.DictReader(open(os.path.join(ed, 'selection.csv'), encoding='utf-8-sig')))
    if not sel: sys.exit('selection.csv에 문서가 없습니다.')
    th = json.load(open(os.path.join(ed, 'theme.json'), encoding='utf-8')) if os.path.exists(os.path.join(ed, 'theme.json')) else {}
    cj = os.path.join(work, 'collection.json')
    coll = json.load(open(cj, encoding='utf-8'))['name'] if os.path.exists(cj) else os.path.basename(os.path.abspath(work))
    title = th.get('title') or theme
    cur, dv = ST.read_curator(ed), ST.read_delivery(ed)
    ys = sorted(int(s['연도']) for s in sel if str(s.get('연도', '')).isdigit())
    span = (f'{ys[0]}–{ys[-1]}' if ys[0] != ys[-1] else str(ys[0])) if ys else ''
    img = lambda s: os.path.join(ed, s['이미지']) if s.get('이미지') and os.path.exists(os.path.join(ed, s['이미지'])) else None
    tag = (f'EP.{ep:02d} · ' if ep else '') + '고문서 한 장'
    S = []
    opener = (dv.get('open') or '').split(' — ')[0] or title
    S.append((img(sel[0]) if sel else None, tag, opener, opener))
    S.append((None, coll + (f' · {span}' if span else ''), title, f'{coll}에 남은 문서 {len(sel)}건을 원문으로 읽었습니다.'))
    for s in sel[:max_docs]:
        story = (s.get('이야기') or s.get('캡션') or '').strip()
        fq = ST.find_quotes(story)
        big = f'"{fq[0][0]}"' if fq else (s.get('문서명') or '')
        sents = re.split(r'(?<=[.?!다])\s+', story); narr = ' '.join(sents[:3])[:220] or s.get('문서명', '')
        S.append((img(s), f"{s.get('연도') or ''} {s.get('문서유형') or ''}".strip(), big, re.sub(r'\([^)]*[一-鿿][^)]*\)', '', narr)))
    if dv.get('climax'):
        cl = dv['climax'].split(' — ')[0]; m = re.match(r'"([^"(]+)', cl)
        S.append((img(sel[-1]) if sel else None, '절정 — 종이에 적힌 한 줄', cl, (m.group(1) if m else cl)))
    if cur.get('message'):
        S.append((None, '비하인드 — 이 이야기를 만든 이유', cur['message'], cur['message']))
    q = cur.get('question') or '여러분이라면 이 문서에서 어떤 한 줄이 가장 오래 남을까요?'
    S.append((None, '여러분의 생각은?', q, q + (' 전시 웹페이지에서 원문을 더 볼 수 있습니다.' if url else '')))
    foot = f'이미지: 한국학중앙연구원 한국고문서자료관 소장·제공 · {coll}' + (f' · {url}' if url else '')
    return S, foot, title


async def _tts(text, path, voice):
    import edge_tts
    for k in range(6):
        try: await edge_tts.Communicate(text, voice, rate='+5%').save(path); return True
        except Exception:
            if k == 5: raise
            await asyncio.sleep(10 * (k + 1))


def dur(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).decode())


def ts(x):
    h, r = divmod(x, 3600); m, s = divmod(r, 60); return f'{int(h):02d}:{int(m):02d}:{s:06.3f}'.replace('.', ',')


def build(S, foot, fmt, od, base, voice, tts):
    tmp = os.path.join(od, f'.{fmt}'); os.makedirs(tmp, exist_ok=True)
    size = (1080, 1920) if fmt == 'reel' else (1920, 1080); parts, srt, t = [], [], 0
    for i, (img, label, big, sub) in enumerate(S):
        png = f'{tmp}/s{i:02d}.png'
        (reel_frame if fmt == 'reel' else wide_frame)(img, label, big, sub, png, foot)
        os.makedirs(os.path.join(od, '.tts'), exist_ok=True); mp3 = os.path.join(od, '.tts', f's{i:02d}.mp3'); L = max(3.0, len(sub) / 7.5)
        if tts:
            if not os.path.exists(mp3) or os.path.getsize(mp3) == 0:
                try: asyncio.run(_tts(sub, mp3, voice))
                except Exception as e: sys.exit(f'내레이션 생성 실패({type(e).__name__}): 네트워크·인증서를 확인하거나 --no-tts 로 무음 영상을 만드세요. 자체 인증서 환경이면 AKS_CA_BUNDLE=<인증서 파일>.')
            L = dur(mp3) + 0.6
        sc = f'{int(size[0]*1.04)}:{int(size[1]*1.04)}'
        vf = f"[0:v]scale={sc},zoompan=z='min(zoom+0.0003,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(L*30)}:s={size[0]}x{size[1]}:fps=30,format=yuv420p[v]"
        cmd = ['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-i', png]
        if tts: cmd += ['-i', mp3, '-filter_complex', vf + ';[1:a]apad[a]', '-map', '[v]', '-map', '[a]']
        else: cmd += ['-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-filter_complex', vf, '-map', '[v]', '-map', '1:a']
        cmd += ['-t', f'{L:.2f}', '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-c:a', 'aac', '-b:a', '128k', f'{tmp}/s{i:02d}.mp4']
        subprocess.run(cmd, check=True); parts.append(f'{tmp}/s{i:02d}.mp4')
        srt.append(f'{i+1}\n{ts(t)} --> {ts(t+L-0.4)}\n{sub}\n'); t += L
    open(f'{tmp}/list.txt', 'w', encoding='utf-8').write(''.join("file '" + os.path.abspath(p).replace(os.sep, '/').replace("'", "'\\''") + "'\n" for p in parts))  # Windows 경로·작은따옴표 대비
    out = os.path.join(od, f'{base}_{fmt}.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{tmp}/list.txt', '-c', 'copy', '-movflags', '+faststart', out], check=True)
    open(os.path.join(od, f'{base}.ko.srt'), 'w', encoding='utf-8').write('\n'.join(srt))
    vtt = 'WEBVTT\n\n' + '\n'.join(re.sub(r'(\d\d:\d\d:\d\d),(\d\d\d)', r'\1.\2', x) for x in srt)  # 웹 플레이어·접근성용
    open(os.path.join(od, f'{base}.ko.vtt'), 'w', encoding='utf-8').write(vtt)
    return out, t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--work', required=True); ap.add_argument('--theme', required=True)
    ap.add_argument('--format', choices=['both', 'reel', 'wide'], default='both'); ap.add_argument('--ep', type=int)
    ap.add_argument('--url', help='전시 웹페이지 주소(마지막 장면·자막에)'); ap.add_argument('--voice', default='ko-KR-SunHiNeural')
    ap.add_argument('--no-tts', action='store_true', help='내레이션 없이(글 길이로 시간 계산)'); ap.add_argument('--max-docs', type=int, default=6)
    ap.add_argument('--web', action='store_true', help='웹용 540p 압축본(_web.mp4)도 만들기'); ap.add_argument('--keep', action='store_true', help='장면 조각 남기기')
    a = ap.parse_args()
    if not shutil.which('ffmpeg'): sys.exit('ffmpeg이 필요합니다.')
    tts = not a.no_tts
    if os.environ.get('AKS_CA_BUNDLE'):  # 사내 프록시 등 자체 인증서 환경: edge-tts를 불러오기 전에 지정
        try:
            import certifi; certifi.where = lambda: os.environ['AKS_CA_BUNDLE']
        except Exception: pass
    if tts:
        try: import edge_tts  # noqa
        except Exception: print('edge-tts가 없어 무음 영상으로 만듭니다 (pip install edge-tts)'); tts = False
    if not shutil.which('ffprobe') and tts: sys.exit('ffprobe가 필요합니다(ffmpeg과 함께 설치됩니다).')
    S, foot, title = scenes(a.work, a.theme, a.ep, a.url, a.max_docs)
    od = os.path.join(a.work, 'mediate', a.theme, 'video'); os.makedirs(od, exist_ok=True)
    base = (f'ep{a.ep:02d}-' if a.ep else '') + a.theme
    for fmt in (['reel', 'wide'] if a.format == 'both' else [a.format]):
        out, t = build(S, foot, fmt, od, base, a.voice, tts)
        print(f'{os.path.basename(out)}\t{t:.0f}초\t장면 {len(S)}개')
        if a.web:
            sc = '540:960' if fmt == 'reel' else '960:540'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out, '-vf', f'scale={sc}', '-c:v', 'libx264', '-preset', 'slow', '-crf', '32', '-tune', 'stillimage', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', out.replace('.mp4', '_web.mp4')], check=True)
        if not a.keep: shutil.rmtree(os.path.join(od, f'.{fmt}'), ignore_errors=True)
    if not a.keep: shutil.rmtree(os.path.join(od, '.tts'), ignore_errors=True)
    print('→', od)
    if os.path.exists(os.path.join(a.work, 'mediate', a.theme, 'index.html')):
        print('  첫 페이지(index.html)에 영상을 넣으려면 studio.py mediate 를 다시 실행하세요.')


if __name__ == '__main__':
    main()
