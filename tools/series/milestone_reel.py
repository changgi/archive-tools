#!/usr/bin/env python3
"""「고문서 한 장」 200편 기념 홍보 영상 — 릴스(9:16) · 가로(16:9)
usage: milestone_reel.py [reel|wide|both] [--preview]
  이미지: archive-tools-next/iiif (전시 웹페이지와 같은 이미지) · 숫자: examples/analysis-data.json
  결과: $SERIES_DATA/out/promo-reel-200_{reel,wide}.mp4 (원본) → archive-tools-next/media 에 복사
"""
import _paths as P
import json, os, subprocess, sys, asyncio
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS = 30
FD = '/usr/share/fonts/opentype/noto/'
def F(n, s): return ImageFont.truetype(FD + n, s, index=1)
SERIFB = lambda s: F('NotoSerifCJK-Black.ttc', s); SERIF = lambda s: F('NotoSerifCJK-Bold.ttc', s)
BOLD = lambda s: F('NotoSansCJK-Bold.ttc', s); MED = lambda s: F('NotoSansCJK-Medium.ttc', s); REG = lambda s: F('NotoSansCJK-Regular.ttc', s)
BG = (22, 19, 15); GOLD = (196, 150, 74); PAPER = (239, 230, 212); DIM = (185, 173, 150)
def ease(x): x = max(0., min(1., x)); return x * x * (3 - 2 * x)
def prog(t, a, b): return max(0., min(1., (t - a) / (b - a))) if b > a else float(t >= a)

ID = 'promo-reel-200'
IIIF = os.path.join(P.NEXT, 'iiif')
A = json.load(open(P.REPO + '/examples/analysis-data.json', encoding='utf-8'))
VD = json.load(open(P.REPO + '/examples/viewer-data.json', encoding='utf-8'))
AUD = os.path.join(P.DATA, 'aud', ID); os.makedirs(AUD, exist_ok=True)
OUT = os.path.join(P.DATA, 'out'); os.makedirs(OUT, exist_ok=True)
VOICE = 'ko-KR-InJoonNeural'

# 장면 · 대사 (text = 자막, tts = 읽는 말)
TH = [  # (자막, 읽기, 보여 줄 편 폴더 두 개)
    ('임명장과 합격증,', '임명장과 합격증,', ['yeonan-kim-yuji', 'cheonsang-hongpae']),
    ('혼서와 분재기와 호적,', '혼서와 분재기와 호적,', ['jangheung-im-honseo', 'gyeongju-lee-cw-hojeok']),
    ('땅을 지키려 쓴 소지와 산도,', '땅을 지키려 쓴 소지와 산도,', ['jangheung-im-sansong', 'cheonsang-sanrim']),
    ('그리고 근대의 인쇄된 서식까지.', '그리고 근대의 인쇄된 서식까지.', ['gyeongseongdang-gamok', 'chunghyo-bak-imya']),
]
QU = [  # (편 폴더, 문서 번호, 현대어, 원문, 편)
    ('yeonan-kim-yuji', 1, '서둘러 역마를 타고 올라오라', '爾其斯速乘馹上來事', 'EP.174 · 1763'),
    ('gujwa-jeong-chacheop', 1, '가볍지 않게 살펴 맡을 일', '不輕察任向事', 'EP.179 · 1766'),
    ('cheonsang-gyehu', 4, '주는 사람은 있는데 받을 사람이 없어', '與者有之而受者無人', 'EP.183 · 1759'),
]
D, C, Y0, Y1, H = A['docs'], A['colls'], A['span'][0], A['span'][1], A['reading']['hanja']
def kn(n):
    """숫자 → 한자어 수 읽기(만 단위까지) — tts용"""
    D1 = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
    def four(x):
        o = ''
        for v, u in ((1000, '천'), (100, '백'), (10, '십'), (1, '')):
            q = x // v % 10
            if q: o += ('' if q == 1 and u else D1[q]) + u
        return o
    if n == 0: return '영'
    m, r = divmod(n, 10000)
    return ((four(m) if m > 1 else '') + '만 ' if m else '') + four(r)
LINES = [
    dict(scene='title', text='옛 문서 한 장을, 원문으로 읽었습니다.', tts='옛 문서 한 장을, 원문으로 읽었습니다.'),
    dict(scene='mosaic', text='그렇게 200편.', tts='그렇게, 이백 편.'),
    dict(scene='mosaic', text=f'문중과 서원, 향교와 사찰 — 소장처 {C}곳.', tts=f'문중과 서원, 향교와 사찰. 소장처 {kn(C)} 곳.'),
    dict(scene='nums', text=f'문서 {D}건, {Y0}년부터 {Y1}년까지.', tts=f'문서 {kn(D)} 건. {kn(Y0)} 년부터, {kn(Y1)} 년까지.'),
    dict(scene='nums', text=f'읽은 한자 {H:,}자.', tts=f'읽은 한자, {kn(H)} 자.'),
] + [dict(scene='theme', key=i, text=t, tts=s) for i, (t, s, _) in enumerate(TH)] + [
    dict(scene='quote', key=i, text=f'"{q[2]}"', tts=q[2] + '.') for i, q in enumerate(QU)] + [
    dict(scene='end', text='못 읽은 글자는 □로, 모르는 것은 모른다고 남겼습니다.', tts='못 읽은 글자는 네모로, 모르는 것은, 모른다고 남겼습니다.'),
    dict(scene='end', text='다음 종이는, 어느 집 서랍에서 나올까요?', tts='다음 종이는, 어느 집 서랍에서 나올까요?'),
]

def tts_all():
    import certifi
    if os.environ.get('SSL_CERT_FILE') and os.path.exists(os.environ['SSL_CERT_FILE']): certifi.where = lambda: os.environ['SSL_CERT_FILE']
    import edge_tts
    async def go():
        for i, ln in enumerate(LINES):
            wav = os.path.join(AUD, f'{i:02d}.wav')
            if os.path.exists(wav): continue
            mp3 = wav[:-4] + '.mp3'
            for k in range(8):
                try: await edge_tts.Communicate(ln['tts'], VOICE, rate='+4%').save(mp3); break
                except Exception:
                    if k == 7: raise
                    await asyncio.sleep(20 * (k + 1))
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', mp3, '-af', 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse', '-ar', '48000', '-ac', '1', wav], check=True)
    asyncio.run(go())
tts_all()
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))
TL = []; t = 0.6
for i, ln in enumerate(LINES):
    d = dur(os.path.join(AUD, f'{i:02d}.wav'))
    if TL and TL[-1]['scene'] == ln['scene'] and TL[-1].get('key') == ln.get('key'): sc = TL[-1]
    else:
        if TL: t += 0.15
        sc = dict(scene=ln['scene'], key=ln.get('key'), start=t, lines=[]); TL.append(sc); t += 0.15
    sc['lines'].append((t - sc['start'], t - sc['start'] + d, ln['text'], i)); t += d + 0.35
    sc['dur'] = t - sc['start']
TL[0]['start'] = 0; TL[0]['dur'] += 0.6
TL[0]['lines'] = [(a + .6, b + .6, x, i) for a, b, x, i in TL[0]['lines']]
TL[-1]['dur'] += 3.2; TOTAL = TL[-1]['start'] + TL[-1]['dur']

# ---- 이미지
EPS = sorted([e for e in VD['eps'] if e.get('ep')], key=lambda e: e['ep'])  # EP.1–EP.200
def thumb(f, n=1): return Image.open(f'{IIIF}/{f}/thumb/{n:02d}.jpg').convert('RGB')
def full(f, n=1): return Image.open(f'{IIIF}/{f}/{n:02d}.jpg').convert('RGB')
THUMBS = [thumb(e['f']) for e in EPS]
HERO = full('sangnyeong-choi-baekhong', 1)

def cover(im, w, h, fy=.3):
    r = max(w / im.width, h / im.height); im2 = im.resize((max(w, int(im.width * r + .5)), max(h, int(im.height * r + .5))), Image.LANCZOS)
    x = (im2.width - w) // 2; y = int((im2.height - h) * fy); return im2.crop((x, y, x + w, y + h))
def contain(im, w, h):
    r = min(w / im.width, h / im.height); return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)

class R:
    def __init__(s, mode):
        s.mode = mode; s.W, s.H = (1080, 1920) if mode == 'reel' else (1920, 1080); s.reel = mode == 'reel'
        # 모자이크 격자
        cols, rows = (12, 17) if s.reel else (25, 8)
        top = 230 if s.reel else 110; bottom = 330 if s.reel else 170
        cw = s.W // cols; ch = (s.H - top - bottom) // rows
        s.grid = []; s.gimg = []
        for i in range(min(len(THUMBS), cols * rows)):
            r_, c_ = divmod(i, cols); s.grid.append((c_ * cw + (s.W - cw * cols) // 2, top + r_ * ch, cw - 4, ch - 4))
        for i, (x, y, w, h) in enumerate(s.grid): s.gimg.append(cover(THUMBS[i], w, h))
        s.cache = {}
        s.fT = SERIFB(120 if s.reel else 110); s.fS = SERIF(56 if s.reel else 50); s.fCap = MED(50 if s.reel else 44)
        s.fNum = SERIFB(150 if s.reel else 120); s.fLab = MED(44 if s.reel else 38); s.fQ = SERIFB(78 if s.reel else 70); s.fH = SERIF(48 if s.reel else 44)
        s.fSmall = REG(30 if s.reel else 28)

    def wrap(s, d, txt, f, maxw):
        out, cur = [], ''
        for ch in txt:
            if d.textlength(cur + ch, font=f) > maxw and cur: out.append(cur); cur = ch
            else: cur += ch
        if cur: out.append(cur)
        return out
    def ctext(s, d, cx, y, txt, f, fill, maxw, lh=1.3):
        lines = s.wrap(d, txt, f, maxw); hh = f.size * lh
        for i, ln in enumerate(lines): d.text((cx, y + i * hh), ln, font=f, fill=fill, anchor='mm')
        return len(lines) * hh

    def mosaic(s, img, n, alpha=1.0, dim=0.0):
        lay = Image.new('RGB', (s.W, s.H), BG)
        for i in range(min(n, len(s.grid))):
            x, y, w, h = s.grid[i]; lay.paste(s.gimg[i], (x, y))
        if dim: lay = Image.blend(lay, Image.new('RGB', lay.size, BG), dim)
        return Image.blend(img, lay, alpha) if alpha < 1 else lay

    def caption(s, img, sc, lt):
        d = ImageDraw.Draw(img)
        for a, b, txt, _ in sc['lines']:
            if a - .05 <= lt <= b + .3:
                y = s.H - (210 if s.reel else 110)
                lines = s.wrap(d, txt, s.fCap, s.W - 160); hh = s.fCap.size * 1.35
                y0 = y - (len(lines) - 1) * hh / 2
                box = Image.new('RGBA', (s.W, int(len(lines) * hh + 40)), (10, 9, 7, 170)); img.paste(box, (0, int(y0 - hh / 2 - 20)), box)
                for i, ln in enumerate(lines): d.text((s.W / 2, y0 + i * hh), ln, font=s.fCap, fill=PAPER, anchor='mm')
                break

    def sc_title(s, img, sc, lt, T):
        z = 1.0 + 0.06 * lt / T
        w, h = int(s.W * z), int(s.H * z); im = cover(HERO, w, h, .2).crop(((w - s.W) // 2, (h - s.H) // 2, (w - s.W) // 2 + s.W, (h - s.H) // 2 + s.H))
        im = Image.blend(im, Image.new('RGB', im.size, BG), .72); img.paste(im)
        d = ImageDraw.Draw(img); a = ease(prog(lt, .3, 1.3))
        col = tuple(int(BG[i] + (PAPER[i] - BG[i]) * a) for i in range(3)); colg = tuple(int(BG[i] + (GOLD[i] - BG[i]) * a) for i in range(3))
        cy = s.H * (.40 if s.reel else .42)
        d.text((s.W / 2, cy - 120), 'ARCHIVE TOOLS', font=s.fSmall, fill=colg, anchor='mm')
        d.text((s.W / 2, cy), '고문서 한 장', font=s.fT, fill=col, anchor='mm')
        d.text((s.W / 2, cy + 130), '200편', font=s.fS, fill=colg, anchor='mm')

    def sc_mosaic(s, img, sc, lt, T):
        n = int(len(s.grid) * ease(prog(lt, 0, T * .7)))
        img.paste(s.mosaic(img, n))
        d = ImageDraw.Draw(img)
        d.text((s.W / 2, (120 if s.reel else 58)), f'{n}편', font=s.fS, fill=GOLD, anchor='mm')

    def sc_nums(s, img, sc, lt, T):
        img.paste(s.mosaic(img, len(s.grid), dim=.82))
        d = ImageDraw.Draw(img)
        items = [(D, '건의 문서'), (Y1 - Y0, f'년 · {Y0}–{Y1}'), (H, '자 판독 한자')]
        for k, (v, lab) in enumerate(items):
            a = prog(lt, .2 + k * 1.1, 1.4 + k * 1.1); vv = int(v * ease(a))
            if s.reel: cx, cy = s.W / 2, 470 + k * 390
            else: cx, cy = s.W * (k + .5) / 3, s.H * .44
            d.text((cx, cy), f'{vv:,}', font=s.fNum, fill=GOLD if a > 0 else BG, anchor='mm')
            d.text((cx, cy + (110 if s.reel else 100)), lab, font=s.fLab, fill=DIM if a > 0 else BG, anchor='mm')

    def doc_pair(s, k):
        if ('pair', k) in s.cache: return s.cache[('pair', k)]
        fs = TH[k][2]; out = []
        for f in fs:
            im = full(f, 1); out.append(im)
        s.cache[('pair', k)] = out; return out

    def sc_theme(s, img, sc, lt, T):
        img.paste(Image.new('RGB', (s.W, s.H), BG))
        ims = s.doc_pair(sc['key'])
        for j, im in enumerate(ims):
            a = ease(prog(lt, .1 + j * .35, .8 + j * .35))
            if s.reel: bw, bh = 920, 600; x0, y0 = (s.W - bw) // 2, 260 + j * 660
            else: bw, bh = 820, 640; x0, y0 = 120 + j * 880, 150
            c = contain(im, bw, bh) if (bw, bh, id(im)) not in s.cache else s.cache[(bw, bh, id(im))]
            s.cache[(bw, bh, id(im))] = c
            dx = int((1 - a) * (80 if j == 0 else -80))
            px, py = x0 + (bw - c.width) // 2 + dx, y0 + (bh - c.height) // 2
            if a > 0:
                region = img.crop((px, py, px + c.width, py + c.height))
                img.paste(Image.blend(region, c, a), (px, py))
        d = ImageDraw.Draw(img)
        name = ['부르고 맡기다 · 시험을 치르다', '가족이 되다', '땅을 지키다', '근대의 종이'][sc['key']]
        d.text((s.W / 2, (150 if s.reel else 70)), name, font=s.fS, fill=GOLD, anchor='mm')

    def sc_quote(s, img, sc, lt, T):
        f, n, q, h, ep = QU[sc['key']]
        key = ('q', sc['key'])
        if key not in s.cache:
            im = cover(full(f, n), s.W, s.H, .3).filter(ImageFilter.GaussianBlur(2)); s.cache[key] = Image.blend(im, Image.new('RGB', im.size, BG), .84)
        img.paste(s.cache[key]); d = ImageDraw.Draw(img); a = ease(prog(lt, .1, .9))
        col = tuple(int(BG[i] + (PAPER[i] - BG[i]) * a) for i in range(3)); colg = tuple(int(BG[i] + (GOLD[i] - BG[i]) * a) for i in range(3))
        cy = s.H * (.38 if s.reel else .38)
        hgt = s.ctext(d, s.W / 2, cy, f'"{q}"', s.fQ, col, s.W - (160 if s.reel else 400))
        s.ctext(d, s.W / 2, cy + hgt + 40, h, s.fH, colg, s.W - 160)
        d.text((s.W / 2, cy + hgt + 150), ep, font=s.fSmall, fill=DIM, anchor='mm')

    def sc_end(s, img, sc, lt, T):
        img.paste(s.mosaic(img, len(s.grid), dim=.9)); d = ImageDraw.Draw(img)
        a = ease(prog(lt, T - 3.4, T - 2.4))
        cy = s.H * (.36 if s.reel else .34)
        d.text((s.W / 2, cy), '고문서 한 장 · 200편', font=s.fS, fill=GOLD, anchor='mm')
        if a > 0:
            col = tuple(int(BG[i] + (PAPER[i] - BG[i]) * a) for i in range(3)); colg = tuple(int(BG[i] + (DIM[i] - BG[i]) * a) for i in range(3))
            d.text((s.W / 2, cy + 120), 'changgi.github.io/archive-tools/examples/200.html', font=s.fSmall, fill=col, anchor='mm')
            y = cy + 200
            for ln in ['고문서 이미지: 한국학중앙연구원 한국고문서자료관 소장 · 제공(각 소장처 기탁)',
                       '다시 쓰려면 자료관을 통한 소장처 동의 필요 · 문제가 있으면 내립니다',
                       '판독 · 번역은 초안(사람 검토 전) · 엮은이 Song Chang-gi · chgsong@naver.com']:
                y += s.ctext(d, s.W / 2, y, ln, REG(26 if s.reel else 24), colg, s.W - 120, 1.35) + 6

    def frame(s, i):
        tt = i / FPS; img = Image.new('RGB', (s.W, s.H), BG)
        sc = next((x for x in TL if x['start'] <= tt < x['start'] + x['dur']), TL[-1]); lt = tt - sc['start']
        getattr(s, 'sc_' + sc['scene'])(img, sc, lt, sc['dur'])
        fi = min(1, (tt + .001) / .5, (TOTAL - tt) / .6) if True else 1
        if fi < 1: img = Image.blend(Image.new('RGB', img.size, (0, 0, 0)), img, max(0, fi))
        if sc['scene'] != 'quote': s.caption(img, sc, lt)
        return img

    def render(s, path, preview=False):
        if preview:
            return [s.frame(int((x['start'] + x['dur'] * .7) * FPS)) for x in TL]
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{s.W}x{s.H}', '-r', str(FPS), '-i', '-',
                              '-i', os.path.join(AUD, 'mix.m4a'), '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                              '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', path + '.tmp.mp4'], stdin=subprocess.PIPE)
        for i in range(int(TOTAL * FPS)): p.stdin.write(s.frame(i).tobytes())
        p.stdin.close(); p.wait(); os.replace(path + '.tmp.mp4', path)

def mix():
    SR = 48000; N = int((TOTAL + 1) * SR); t = np.arange(N) / SR
    voice = np.zeros(N, np.float32)
    for sc in TL:
        for a, b, _, i in sc['lines']:
            raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', os.path.join(AUD, f'{i:02d}.wav'), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'])
            w = np.frombuffer(raw, np.float32); j = int((sc['start'] + a) * SR); voice[j:j + len(w)] += w[:max(0, N - j)]
    voice = voice / max(1e-6, np.abs(voice).max()) * .89
    bpm = 76; beat = 60 / bpm; bar = beat * 4; root = 57; prog_ = [[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]]
    nt = lambda m: 440 * 2 ** ((m - 69) / 12); mus = np.zeros(N, np.float32)
    for k in range(int(TOTAL / (bar * 2)) + 2):
        ch = prog_[k % len(prog_)]; s0 = k * bar * 2; i0 = int(s0 * SR); i1 = min(N, int((s0 + bar * 2 + .6) * SR))
        if i0 >= N: break
        tt = t[i0:i1] - s0; env = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, bar * 2 + .6 - tt))
        for m in ch:
            for det in (-.08, .08): mus[i0:i1] += .034 * env * np.sin(2 * np.pi * nt(root - 12 + m) * (1 + det / 100) * tt)
        mus[i0:i1] += .05 * env * np.sin(2 * np.pi * nt(root - 24 + ch[0]) * tt)
    pent = [0, 2, 4, 7, 9, 12, 14]; tt0 = 0.4; k = 0
    while tt0 < TOTAL - 1.5:
        m = root + pent[[0, 2, 4, 3, 1, 4, 5, 2][k % 8]]; i0 = int(tt0 * SR); seg = np.arange(min(int(1.2 * SR), N - i0)) / SR
        mus[i0:i0 + len(seg)] += .035 * np.exp(-seg * 3.5) * (np.sin(2 * np.pi * nt(m) * seg) + .3 * np.sin(4 * np.pi * nt(m) * seg)); tt0 += beat / 2; k += 1
    mus *= np.clip((TOTAL + .2 - t) / 3.0, 0, 1)
    env = np.convolve(np.abs(voice), np.ones(int(.25 * SR)) / int(.25 * SR), 'same'); env = np.clip(env / .05, 0, 1)
    out = voice + mus * (1 - .55 * env); out /= max(1.0, np.abs(out).max() / .95)
    f32 = os.path.join(AUD, 'mix.f32'); out[:int(TOTAL * SR)].astype(np.float32).tofile(f32)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', f32, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',
                    '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k', os.path.join(AUD, 'mix.m4a')], check=True)
    os.remove(f32)

def subs():
    def ts(x, sep=','): return f"00:{int(x // 60):02d}:{int(x % 60):02d}{sep}{int((x - int(x)) * 1000):03d}"
    srt, vtt = [], ['WEBVTT', '']; n = 1
    for sc in TL:
        for a, b, txt, _ in sc['lines']:
            srt.append(f"{n}\n{ts(sc['start'] + a)} --> {ts(sc['start'] + b)}\n{txt}\n"); vtt.append(f"{ts(sc['start'] + a, '.')} --> {ts(sc['start'] + b, '.')}\n{txt}\n"); n += 1
    return '\n'.join(srt), '\n'.join(vtt)

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'both'
    modes = ['reel', 'wide'] if what == 'both' else [what]
    print(ID, 'TOTAL', round(TOTAL, 1), 's', [(x['scene'], round(x['dur'], 1)) for x in TL])
    if '--preview' in sys.argv:
        for m in modes:
            ims = R(m).render(None, True); w = 360 if m == 'reel' else 640; h = int(w * ims[0].height / ims[0].width)
            sheet = Image.new('RGB', (w * len(ims), h))
            for i, im in enumerate(ims): sheet.paste(im.resize((w, h)), (i * w, 0))
            sheet.save(os.path.join(OUT, f'{ID}_{m}_preview.jpg'), quality=82)
        sys.exit()
    if not os.path.exists(os.path.join(AUD, 'mix.m4a')): mix()
    srt, vtt = subs()
    open(os.path.join(OUT, f'{ID}.ko.srt'), 'w', encoding='utf-8').write(srt)
    MED_ = os.path.join(P.NEXT, 'media'); EXM = P.REPO + '/examples/media'
    for m in modes:
        path = os.path.join(OUT, f'{ID}_{m}.mp4'); R(m).render(path); print('done', m)
    # 웹용: 릴스 = promo-reel-200.mp4, 가로 = promo-reel-200-wide.mp4 (archive-tools-next/media) · 포스터 · 자막 (examples/media)
    for m, name in (('reel', f'{ID}.mp4'), ('wide', f'{ID}-wide.mp4')):
        src = os.path.join(OUT, f'{ID}_{m}.mp4')
        if os.path.exists(src):
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-c:v', 'libx264', '-preset', 'slow', '-crf', '28', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', os.path.join(MED_, name)], check=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(TL[1]['start'] + TL[1]['dur'] * .9), '-i', os.path.join(OUT, f'{ID}_reel.mp4'), '-frames:v', '1', '-q:v', '3', os.path.join(EXM, f'{ID}-poster.jpg')], check=True)
    open(os.path.join(EXM, f'{ID}.ko.srt'), 'w', encoding='utf-8').write(srt); open(os.path.join(EXM, f'{ID}.ko.vtt'), 'w', encoding='utf-8').write(vtt)
    print('web', os.path.getsize(os.path.join(MED_, f'{ID}.mp4')) // 1024, 'KB')
