#!/usr/bin/env python3
"""예제 쇼케이스 영상 템플릿 — 한 예제 설정(JSON)으로 릴스(9:16)와 가로 영상(16:9)을 만든다.
usage: showcase.py CONFIG.json [reel|wide|both] [--preview]
"""
import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import json, os, subprocess, sys, csv, glob, asyncio
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS = 30
FD = '/usr/share/fonts/opentype/noto/'
def F(n, s): return ImageFont.truetype(FD + n, s, index=1)
SERIFB = lambda s: F('NotoSerifCJK-Black.ttc', s); SERIF = lambda s: F('NotoSerifCJK-Bold.ttc', s)
BLACK = lambda s: F('NotoSansCJK-Black.ttc', s); BOLD = lambda s: F('NotoSansCJK-Bold.ttc', s)
MED = lambda s: F('NotoSansCJK-Medium.ttc', s); REG = lambda s: F('NotoSansCJK-Regular.ttc', s)
INK = (18, 16, 12); PAPER = (236, 226, 204); WHITE = (246, 242, 234); DIM = (170, 160, 140)

def ease(x): x = max(0., min(1., x)); return x * x * (3 - 2 * x)
def eout(x): x = max(0., min(1., x)); return 1 - (1 - x) ** 3
def prog(t, a, b): return max(0., min(1., (t - a) / (b - a))) if b > a else float(t >= a)
def lerp(a, b, x): return a + (b - a) * x

ONLY = None
if '@' in sys.argv[1]:  # 큐에서 'ep28-x@reel' → 세로만 다시 렌더
    a_, ONLY = sys.argv[1][:-5].split('@'); sys.argv[1] = a_ + '.json'
CFG = json.load(open(sys.argv[1], encoding='utf-8'))
HERE = os.path.dirname(os.path.abspath(sys.argv[1]))
ACC = tuple(CFG.get('accent', [214, 168, 87]))
AUD = os.path.join(HERE, 'aud', CFG['id']); os.makedirs(AUD, exist_ok=True)

# ---------------------------------------------------------------- narration (edge-tts, cached)
def tts_all():
    import certifi
    if os.environ.get('SSL_CERT_FILE') and os.path.exists(os.environ['SSL_CERT_FILE']): certifi.where = lambda: os.environ['SSL_CERT_FILE']  # 프록시 뒤에서 edge-tts
    import edge_tts
    async def go():
        for i, ln in enumerate(CFG['lines']):
            wav = os.path.join(AUD, f'{i:02d}.wav')
            if os.path.exists(wav): continue
            mp3 = wav[:-4] + '.mp3'
            for k in range(8):  # 일시 오류 대비 재시도
                try:
                    await edge_tts.Communicate(ln['tts'], CFG['voice'], rate=CFG.get('rate', '+7%')).save(mp3); break
                except Exception:
                    if k == 7: raise
                    await asyncio.sleep(20 * (k + 1))
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', mp3, '-af', 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse', '-ar', '48000', '-ac', '1', wav], check=True)
    asyncio.run(go())
tts_all()
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))
# 장면 = 대사 하나 (scene 키가 같은 연속 대사는 한 장면으로 묶음)
TL = []; t = 0.0
for i, ln in enumerate(CFG['lines']):
    d = dur(os.path.join(AUD, f'{i:02d}.wav'))
    if TL and TL[-1]['scene'] == ln['scene'] and TL[-1].get('key') == ln.get('key'):
        sc = TL[-1]
    else:
        if TL: t += 0.08
        sc = dict(scene=ln['scene'], key=ln.get('key'), start=t, lines=[], data=ln); TL.append(sc); t += 0.1
    sc['lines'].append((t - sc['start'], t - sc['start'] + d, ln['text'], i)); t += d + 0.16
    sc['dur'] = t - sc['start']
TL[-1]['dur'] += 1.8; TOTAL = TL[-1]['start'] + TL[-1]['dur']

# ---------------------------------------------------------------- assets
def load(p, maxw=1800):
    im = Image.open(p).convert('RGB'); im.thumbnail((maxw, maxw)); return im
for _k, _v in list(CFG.items()):  # 렌더 설정 속 $WORK · $DATA · $REPO · $CAND · $STATE를 실제 폴더로
    if isinstance(_v, str) and '$' in _v:
        for _n in ('WORK', 'CAND', 'DATA', 'REPO', 'STATE'): _v = _v.replace('$' + _n, getattr(P, _n))
        CFG[_k] = _v
SEL = list(csv.DictReader(open(CFG['selection'], encoding='utf-8-sig')))
EDIR = os.path.dirname(CFG['selection'])
IMG = {s['순서']: load(os.path.join(EDIR, s['이미지'])) for s in SEL}
CARDS = [load(p, 900) for p in sorted(glob.glob(os.path.join(CFG['mediate'], 'cards', '*.png')))]
EXH = Image.open(CFG['exhibit_cap']).convert('RGB')
HERO = IMG[str(CFG['hero'])]

# ---------------------------------------------------------------- layout
LAY = {
 'reel': dict(W=1080, H=1920, media=(60, 300, 1020, 1300), title_y=200, cap_y=1610, cap_w=820, cap_f=50, big=96, mid=46),
 'wide': dict(W=1920, H=1080, media=(90, 120, 1110, 900), title_y=150, cap_y=1010, cap_w=1500, cap_f=40, big=84, mid=38,
              panel=(1180, 140, 1840, 880)),
}

class R:
    def __init__(s, mode):
        s.m = mode; s.L = LAY[mode]; s.W, s.H = s.L['W'], s.L['H']
        rng = np.random.default_rng(7); g = (rng.normal(0, 1, (s.H // 2, s.W // 2)) * 6).astype(np.int16)
        yy, xx = np.mgrid[0:s.H // 2, 0:s.W // 2]
        dd = np.sqrt(((xx - s.W / 4) / (s.W / 2)) ** 2 + ((yy - s.H / 2 * .42) / (s.H / 2.2)) ** 2); v = np.clip(1 - dd, 0, 1) ** 1.6
        base = CFG.get('bg', [20, 17, 13]); glow = CFG.get('glow', [70, 52, 28]); a = np.zeros((s.H // 2, s.W // 2, 3), np.int16)
        for c in range(3): a[..., c] = base[c] + (glow[c] * v).astype(np.int16) + g
        s.BG = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((s.W, s.H), Image.BILINEAR)

    # helpers
    def lay(s): return Image.new('RGBA', (s.W, s.H), (0, 0, 0, 0))
    def over(s, base, lay, a=1.0):
        if a <= 0: return
        if a < 1: lay = lay.copy(); lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
        base.paste(lay, (0, 0), lay)
    def fit(s, im, w, h):
        k = min(w / im.width, h / im.height); return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.BILINEAR)
    def card(s, img, im, cx, cy, w, h, a=1.0, rot=0, border=8):
        t = s.fit(im, w - 2 * border, h - 2 * border)
        b = Image.new('RGB', (t.width + 2 * border, t.height + 2 * border), PAPER); b.paste(t, (border, border)); t = b.convert('RGBA')
        if rot: t = t.rotate(rot, Image.BICUBIC, expand=True)
        if a < 1: t.putalpha(t.split()[3].point(lambda v: int(v * a)))
        x, y = int(cx - t.width / 2), int(cy - t.height / 2)
        sh = Image.new('RGBA', t.size, (0, 0, 0, 0)); sh.putalpha(t.split()[3].point(lambda v: int(v * .5 * a))); sh = sh.filter(ImageFilter.GaussianBlur(20))
        img.paste(sh, (x + 10, y + 24), sh); img.paste(t, (x, y), t)
        return (x, y, x + t.width, y + t.height)
    def zoom(s, im, z, cx, cy, w, h):
        k = max(w / im.width, h / im.height) * z; cw, ch = w / k, h / k
        x0, y0 = cx * im.width - cw / 2, cy * im.height - ch / 2
        return im.transform((int(w), int(h)), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BILINEAR, fillcolor=INK)
    def wrap(s, d, txt, f, w):
        if '\n' in txt:
            out = []
            for part in txt.split('\n'): out += s.wrap(d, part, f, w)
            return out
        rows = ['']
        for word in txt.split(' '):
            tst = (rows[-1] + ' ' + word).strip()
            if d.textlength(tst, font=f) > w and rows[-1]: rows.append(word)
            else: rows[-1] = tst
        out = []
        for r_ in rows:  # 긴 낱말 강제 줄바꿈
            while d.textlength(r_, font=f) > w:
                k = len(r_)
                while d.textlength(r_[:k], font=f) > w: k -= 1
                out.append(r_[:k]); r_ = r_[k:]
            out.append(r_)
        return out

    def fitf(s, d, txt, ff, size, maxw, minr=.62, lines=2):
        """화면 폭에 맞게: 글자를 줄이고(최소 minr배), 그래도 길면 lines줄까지 나눔"""
        lo = max(12, int(size * minr)); sz = size
        tl = lambda f: max(d.textlength(x, font=f) for x in txt.split('\n'))
        while sz > lo and tl(ff(sz)) > maxw: sz -= 2
        f = ff(sz); rows = s.wrap(d, txt, f, maxw)
        while len(rows) > lines and sz > 12:
            sz -= 2; f = ff(sz); rows = s.wrap(d, txt, f, maxw)
        return f, rows

    def ctext(s, d, x, y, txt, ff, size, maxw, fill, anchor='ms', lines=2, minr=.62, lh=1.25):
        """가운데 정렬 글자를 폭 안에 맞춰 그리고, 그린 높이(추가 줄 만큼)를 돌려줌"""
        f, rows = s.fitf(d, txt, ff, size, maxw, minr, lines)
        step = int(f.size * lh)
        for j, r_ in enumerate(rows): d.text((x, y + j * step), r_, font=f, fill=fill, anchor=anchor)
        return step * (len(rows) - 1)

    def chrome(s, img, gt):
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, s.W, 6), fill=(40, 36, 30)); d.rectangle((0, 0, int(s.W * gt / TOTAL), 6), fill=ACC)
        d.text((60, 56), 'ARCHIVE TOOLS', font=BOLD(26), fill=(200, 190, 170))
        f, _ = s.fitf(d, f"{CFG['series']} · {CFG['kind']}", MED, 26, s.W - 420, .5, 1)
        d.text((s.W - 60, 56), f"{CFG['series']} · {CFG['kind']}", font=f, fill=(170, 160, 140), anchor='ra')

    def caption(s, img, sc, lt):
        L = s.L
        for (a, b, txt, _) in sc['lines']:
            if a - .05 <= lt <= b + .12:
                k = min(prog(lt, a - .05, a + .15), 1 - prog(lt, b + .02, b + .12))
                lay = s.lay(); d = ImageDraw.Draw(lay); f = BOLD(L['cap_f'])
                rows = s.wrap(d, txt, f, L['cap_w']); lh = int(L['cap_f'] * 1.45)
                yb = L['cap_y']; top = yb - lh * len(rows) - 24; mw = max(d.textlength(r_, font=f) for r_ in rows)
                d.rounded_rectangle((s.W / 2 - mw / 2 - 34, top, s.W / 2 + mw / 2 + 34, yb + 6), 20, fill=(8, 7, 5, 205))
                for j, r_ in enumerate(rows): d.text((s.W / 2, top + 24 + lh * j + int(L['cap_f'] * 1.08)), r_, font=f, fill=WHITE, anchor='ms')
                s.over(img, lay, k)

    # ---------------- scenes
    def sc_hook(s, img, sc, lt):
        L = s.L; mx0, my0, mx1, my1 = L['media']; p = ease(prog(lt, 0, sc['dur']))
        if s.m == 'reel': box = (0, 0, s.W, 1360)
        else: box = (0, 0, s.W, s.H)
        z = lerp(1.0, 1.35, p); fr = s.zoom(HERO, z, lerp(.5, CFG.get('hero_cx', .55), p), lerp(.5, CFG.get('hero_cy', .45), p), box[2] - box[0], box[3] - box[1])
        img.paste(fr, (box[0], box[1]))
        lay = s.lay(); d = ImageDraw.Draw(lay)
        for i in range(260):
            a = int(235 * (i / 260) ** 1.4); y = box[3] - 260 + i; d.line((0, y, s.W, y), fill=(18, 16, 12, a))
        if s.m == 'wide':
            for i in range(700): d.line((i, 0, i, s.H), fill=(18, 16, 12, int(200 * (1 - i / 700) ** 1.2)))
        s.over(img, lay)
        lay = s.lay(); d = ImageDraw.Draw(lay); a = eout(prog(lt, .2, .9))
        q = sc['data'].get('q', '')
        if s.m == 'reel':
            f, rows = s.fitf(d, q, SERIFB, L['big'] - 10, 900, .6, 4); lh = int(f.size * 1.3); y0 = 1080 - len(rows) * lh
            d.rounded_rectangle((50, y0 - 120, s.W - 50, y0 + len(rows) * lh + 10), 36, fill=(14, 12, 9, int(215 * a)))
            for j, r_ in enumerate(rows): d.text((s.W / 2, y0 + j * lh + 40 * (1 - a)), r_, font=f, fill=(255, 250, 240, int(255 * a)), anchor='ms')
        else:
            f, rows = s.fitf(d, q, SERIFB, L['big'], 720, .6, 4); lh = int(f.size * 1.3)
            d.rounded_rectangle((70, 370, 900, 420 + len(rows) * lh + 50), 36, fill=(14, 12, 9, int(205 * a)))
            for j, r_ in enumerate(rows): d.text((110, 420 + j * lh + 30 * (1 - a)), r_, font=f, fill=(255, 250, 240, int(255 * a)))
        s.over(img, lay)

    def sc_intro(s, img, sc, lt):
        L = s.L
        cats = CFG['cats']; mx = max(v for _, v in cats)
        if s.m == 'reel':
            tx, ty, bx0, bx1, by0, bh = s.W / 2, 330, 300, 960, 560, 92
        else:
            tx, ty, bx0, bx1, by0, bh = s.W / 2, 230, 760, 1640, 420, 80
        lay = s.lay(); d = ImageDraw.Draw(lay); a = eout(prog(lt, 0, .6))
        MW = s.W - 120
        s.ctext(d, tx, ty - 80, CFG['kind_long'], BOLD, L['mid'] - 6, MW, ACC + (int(255 * a),), lines=1)
        f, rows = s.fitf(d, CFG['collection'], SERIFB, L['big'] - 16, MW, .6, 2)
        lh_ = int(f.size * 1.18); top = ty + 20 - lh_ * (len(rows) - 1)  # 두 줄이면 위로 올려 막대와 겹치지 않게
        for j, r_ in enumerate(rows): d.text((tx, top + j * lh_), r_, font=f, fill=WHITE + (int(255 * a),), anchor='ms')
        s.ctext(d, tx, ty + 100, (f"문서 {CFG['n_docs']:,}건 · {CFG['n_pages']:,}장" if CFG['n_pages'] >= CFG['n_docs'] else f"문서 {CFG['n_docs']:,}건"), BOLD, L['mid'], MW, (220, 210, 190, int(255 * a)), lines=1)
        s.over(img, lay)
        d = ImageDraw.Draw(img)
        lx = bx0 - 30 if s.m == 'reel' else bx0 - 40
        for i, (k, v) in enumerate(cats[:7]):
            p = eout(prog(lt, .5 + i * .14, 1.4 + i * .14)); y = by0 + i * bh
            d.text((lx, y + bh * .55), k, font=BOLD(int(bh * .38)), fill=(230, 220, 200), anchor='rm')
            w = (bx1 - bx0) * v / mx * p
            d.rounded_rectangle((bx0, y + bh * .25, bx0 + max(w, 6), y + bh * .75), 10, fill=ACC)
            d.text((bx0 + w + 14, y + bh * .55), f'{int(v * p)}', font=BOLD(int(bh * .34)), fill=WHITE, anchor='lm')

    def sc_doc(s, img, sc, lt):
        L = s.L; dd = sc['data']; im = IMG[str(dd['doc'])]; row = next(r for r in SEL if r['순서'] == str(dd['doc']))
        e = eout(prog(lt, 0, .5)); p = ease(prog(lt, 0, sc['dur']))
        mx0, my0, mx1, my1 = L['media']
        if s.m == 'reel':
            cx, cy, w, h = s.W / 2 + 60 * (1 - e), (my0 + my1) / 2 + 20, 960, 940
            if dd.get('src'): cy, h = 680, 680
        else:
            cx, cy, w, h = (mx0 + mx1) / 2 + 40 * (1 - e), (my0 + my1) / 2, mx1 - mx0, my1 - my0
        # 천천히 확대되는 문서 카드
        zim = s.zoom(im, lerp(1.0, 1.12, p), .5, .5, im.width, im.height)
        s.card(img, zim, cx, cy, w, h, a=e, rot=lerp(1.5, 0, e))
        lay = s.lay(); d = ImageDraw.Draw(lay)
        chip = f"{row['연도'] + ' · ' if row['연도'] else ''}{row['문서유형']}"
        if s.m == 'reel':
            f, _ = s.fitf(d, chip, BLACK, 44, s.W - 200, .5, 1); tw = d.textlength(chip, font=f)
            d.rounded_rectangle((s.W / 2 - tw / 2 - 30, 190, s.W / 2 + tw / 2 + 30, 268), 39, fill=ACC + (int(245 * e),))
            d.text((s.W / 2, 245), chip, font=f, fill=INK + (int(255 * e),), anchor='ms')
        else:
            x0, y0, x1, y1 = L['panel']
            d.text((x0, y0 + 40), chip, font=s.fitf(d, chip, BLACK, 56, x1 - x0, .5, 1)[0], fill=ACC + (int(255 * e),))
            rows = s.wrap(d, row['문서명'], MED(30), x1 - x0)
            for j, r_ in enumerate(rows[:3]): d.text((x0, y0 + 150 + j * 46), r_, font=MED(30), fill=(220, 210, 190, int(255 * e)))
            g = row.get('유형설명', '')
            if g:
                yy = y0 + 170 + len(rows[:3]) * 46
                d.text((x0, yy), '어떤 문서?', font=BOLD(28), fill=ACC + (int(255 * e),))
                for j, r_ in enumerate(s.wrap(d, g, REG(30), x1 - x0)[:3]): d.text((x0, yy + 48 + j * 44), r_, font=REG(30), fill=(200, 190, 170, int(255 * e)))
            if not dd.get('src'): d.text((x0, y1 - 20), '자료: 한국학중앙연구원 한국고문서자료관', font=REG(22), fill=(150, 140, 120, int(255 * e)))
        s.over(img, lay)
        if dd.get('src'): s.src_quote(img, dd, lt)

    def src_quote(s, img, dd, lt):
        """원문 인용: 한자 구절 + 한글 독음/뜻 (사료가 직접 말하게)"""
        a = eout(prog(lt, .6, 1.2)); lay = s.lay(); d = ImageDraw.Draw(lay)
        if s.m == 'reel':
            box = (60, 1040, s.W - 60, 1040 + 250); fz, gz = 46, 30
        else:
            x0, y0, x1, y1 = s.L['panel']; box = (x0, y1 - 330, x1, y1 - 10); fz, gz = 46, 28
        d.rounded_rectangle(box, 18, fill=(20, 16, 11, int(225 * a)), outline=ACC + (int(200 * a),), width=3)
        bw = box[2] - box[0] - 60
        rows = s.wrap(d, dd['src'], SERIF(fz), bw)[:(1 if s.m == 'reel' else 2)]
        yy = box[1] + 26
        d.text((box[0] + 30, yy - 4), '원문', font=BOLD(gz - 4), fill=ACC + (int(255 * a),)); yy += gz + 6
        for r_ in rows: d.text((box[0] + 30, yy), r_, font=SERIF(fz), fill=(245, 236, 216, int(255 * a))); yy += int(fz * 1.3)
        if dd.get('src_rd'):
            d.text((box[0] + 30, yy - 4), s.wrap(d, dd['src_rd'], BOLD(gz - 2), bw)[0], font=BOLD(gz - 2), fill=ACC + (int(255 * a),)); yy += int(gz * 1.4)
        if dd.get('src_ko'):
            for r_ in s.wrap(d, dd['src_ko'], MED(gz), bw)[:(1 if s.m == 'reel' else 2)]: d.text((box[0] + 30, yy), r_, font=MED(gz), fill=(215, 200, 170, int(255 * a))); yy += int(gz * 1.35)
        s.over(img, lay)

    def sc_quote(s, img, sc, lt):
        L = s.L; dd = sc['data']
        im = IMG[str(dd.get('doc', CFG['hero']))]
        bgim = s.zoom(im, 1.15 + .1 * prog(lt, 0, sc['dur']), .5, .5, s.W, s.H).filter(ImageFilter.GaussianBlur(6))
        img.paste(bgim, (0, 0))
        lay = s.lay(); d = ImageDraw.Draw(lay); d.rectangle((0, 0, s.W, s.H), fill=(14, 12, 9, 190)); s.over(img, lay)
        lay = s.lay(); d = ImageDraw.Draw(lay); a = eout(prog(lt, .1, .9))
        sz = L['big'] - (14 if s.m == 'reel' else 6); mw_ = s.W - (160 if s.m == 'reel' else 500)
        while True:  # 화면 높이의 60% 안에 들 때까지 글자를 줄임
            f = SERIFB(sz); rows = []
            for part in dd['big'].split('\n'): rows += s.wrap(d, part, f, mw_)
            if len(rows) * f.size * 1.35 <= s.H * .6 or sz <= 30: break
            sz -= 4
        lh = int(f.size * 1.35); y0 = (s.H * (.42 if s.m == 'reel' else .45)) - lh * len(rows) / 2
        for j, r_ in enumerate(rows):
            d.text((s.W / 2, y0 + j * lh + 30 * (1 - a)), r_, font=f, fill=(ACC if j == len(rows) - 1 else WHITE) + (int(255 * a),), anchor='ms')
        s.over(img, lay)

    def sc_outputs(s, img, sc, lt):
        dur_ = sc['dur']
        if s.m == 'reel':
            px, py, pw, ph = 90, 230, 440, 880; cards_x = [760, 800]
        else:
            px, py, pw, ph = 240, 130, 440, 780; cards_x = [1000, 1240, 1480]
        ex = s.fit(EXH, pw, 99999); y = lerp(0, max(0, ex.height - ph) * .55, ease(prog(lt, .2, dur_)))
        view = ex.crop((0, int(y), pw, int(y) + ph))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((px - 16, py - 16, px + pw + 16, py + ph + 16), 46, fill=(8, 8, 8)); img.paste(view, (int(px), int(py)))
        lab = [('전시 웹페이지', px + pw / 2, py + ph + 70)]
        picks = [CARDS[0], CARDS[2], CARDS[-1]] if len(CARDS) > 3 else CARDS
        if s.m == 'reel':
            for i, c in enumerate(picks[:2]):
                e = eout(prog(lt, .5 + i * .35, 1.1 + i * .35))
                s.card(img, c, cards_x[i] + 60 * (1 - e), 480 + i * 440, 400, 500, a=e, rot=(-4 if i == 0 else 3), border=0)
            lab.append(('카드뉴스', 780, 1290))
        else:
            for i, c in enumerate(picks[:3]):
                e = eout(prog(lt, .5 + i * .3, 1.1 + i * .3))
                s.card(img, c, cards_x[i], 470 + 50 * (1 - e), 340, 425, a=e, rot=[-4, 2, 5][i], border=0)
            lab.append(('카드뉴스 · 수업 활동지 · SNS 글', 1240, 780))
        lay = s.lay(); dl = ImageDraw.Draw(lay)
        for (t_, x_, y_) in lab:
            f = BOLD(30); tw = dl.textlength(t_, font=f)
            dl.rounded_rectangle((x_ - tw / 2 - 24, y_ - 36, x_ + tw / 2 + 24, y_ + 14), 25, fill=ACC + (235,))
            dl.text((x_, y_ + 2), t_, font=f, fill=INK + (255,), anchor='ms')
        s.over(img, lay)

    def sc_cta(s, img, sc, lt):
        L = s.L; lay = s.lay(); d = ImageDraw.Draw(lay)
        a = eout(prog(lt, .1, .8)); b = eout(prog(lt, sc['lines'][-1][0], sc['lines'][-1][0] + .8))
        # 배경에 카드 모자이크
        if s.m == 'reel': cols, cw, ch, oy = 3, 360, 450, 160
        else: cols, cw, ch, oy = 6, 320, 400, 80
        for i, c in enumerate(CARDS[:cols * 2]):
            t = s.fit(c, cw - 10, ch - 10).convert('RGBA'); t.putalpha(int(70 * a))
            lay.paste(t, (int((i % cols) * cw + 5), int(oy + (i // cols) * ch)), t)
        s.over(img, lay)
        lay = s.lay(); d = ImageDraw.Draw(lay)
        cy = 820 if s.m == 'reel' else 380
        t1, t2 = CFG['tagline']
        MW = s.W - 120
        s.ctext(d, s.W / 2, cy, t1, SERIFB, L['big'] - 20, MW, WHITE + (int(255 * a),), lines=1, minr=.5)
        s.ctext(d, s.W / 2, cy + int(L['big'] * 1.15), t2, SERIFB, L['big'] - 20, MW, ACC + (int(255 * a),), lines=1, minr=.5)
        u = 'github.com/changgi/archive-tools'; f, _ = s.fitf(d, u, BOLD, L['mid'], MW - 70, .5, 1); tw = d.textlength(u, font=f)
        uy = cy + int(L['big'] * 2.4)
        d.rounded_rectangle((s.W / 2 - tw / 2 - 34, uy - 52, s.W / 2 + tw / 2 + 34, uy + 22), 36, fill=ACC + (int(245 * b),))
        d.text((s.W / 2, uy), u, font=f, fill=INK + (int(255 * b),), anchor='ms')
        s.ctext(d, s.W / 2, uy + 70, '무료 · 오픈소스 · Claude 플러그인 aks-archive-harvester', MED, L['mid'] - 14, MW, (220, 210, 190, int(255 * b)), lines=1, minr=.5)
        cr = f"이미지: 한국학중앙연구원 한국고문서자료관 소장·제공 · {CFG['collection']}"
        fcr, rcr = s.fitf(d, cr, REG, 22, MW, .8, 2)
        for j, r_ in enumerate(rcr): d.text((s.W / 2, s.H - 40 - (len(rcr) - 1 - j) * int(fcr.size * 1.3)), r_, font=fcr, fill=(150, 140, 120, int(255 * b)), anchor='ms')
        s.over(img, lay)

    def frame(s, i, lt):
        sc = TL[i]; img = s.BG.copy()
        getattr(s, 'sc_' + sc['scene'])(img, sc, lt); s.chrome(img, sc['start'] + lt); return img

    def render(s, outpath, preview=False):
        if preview:
            ims = []
            for i, sc in enumerate(TL):
                im = s.frame(i, sc['dur'] * .7); s.caption(im, sc, sc['dur'] * .7); ims.append(im)
            return ims
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{s.W}x{s.H}', '-r', str(FPS), '-i', '-',
                              '-i', os.path.join(AUD, 'mix.m4a'), '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                              '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', outpath + '.tmp.mp4'], stdin=subprocess.PIPE)
        prev = None
        for i, sc in enumerate(TL):
            n = int(round(sc['dur'] * FPS))
            for k in range(n):
                lt = k / FPS; im = s.frame(i, lt)
                if prev is not None and lt < .3: im = Image.blend(prev, im, ease(lt / .3))
                s.caption(im, sc, lt); p.stdin.write(im.tobytes())
            prev = s.frame(i, sc['dur'] - 1 / FPS)
        p.stdin.close(); assert p.wait() == 0; os.replace(outpath + '.tmp.mp4', outpath)

# ---------------------------------------------------------------- music + mix
def mix():
    SR = 48000; N = int((TOTAL + 1) * SR); t = np.arange(N) / SR
    voice = np.zeros(N, np.float32)
    for sc in TL:
        for a, b, _, i in sc['lines']:
            raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', os.path.join(AUD, f'{i:02d}.wav'), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'])
            w = np.frombuffer(raw, np.float32); j = int((sc['start'] + a) * SR); voice[j:j + len(w)] += w[:max(0, N - j)]
    voice = voice / max(1e-6, np.abs(voice).max()) * .89
    bpm = CFG.get('bpm', 84); beat = 60 / bpm; bar = beat * 4; root = CFG.get('root', 57)
    prog_ = CFG.get('chords', [[0, 3, 7], [-4, 0, 3], [-9, -5, -2], [-2, 2, 5]])
    nt = lambda m: 440 * 2 ** ((m - 69) / 12); mus = np.zeros(N, np.float32)
    for k in range(int(TOTAL / (bar * 2)) + 2):
        ch = prog_[k % len(prog_)]; s0 = k * bar * 2; i0 = int(s0 * SR); i1 = min(N, int((s0 + bar * 2 + .6) * SR))
        if i0 >= N: break
        tt = t[i0:i1] - s0; env = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, bar * 2 + .6 - tt))
        for m in ch:
            for det in (-.08, .08): mus[i0:i1] += .034 * env * np.sin(2 * np.pi * nt(root - 12 + m) * (1 + det / 100) * tt)
        mus[i0:i1] += .05 * env * np.sin(2 * np.pi * nt(root - 24 + ch[0]) * tt)
    pent = [0, 3, 5, 7, 10, 12, 15]; tt0 = 0.4; k = 0
    while tt0 < TOTAL - 1.5:
        m = root + pent[[0, 2, 4, 3, 1, 4, 5, 2][k % 8]]; i0 = int(tt0 * SR); seg = np.arange(min(int(1.2 * SR), N - i0)) / SR
        mus[i0:i0 + len(seg)] += .04 * np.exp(-seg * 3.5) * (np.sin(2 * np.pi * nt(m) * seg) + .3 * np.sin(4 * np.pi * nt(m) * seg)); tt0 += beat / 2; k += 1
    tt0 = TL[1]['start'] if len(TL) > 1 else 0
    while tt0 < TOTAL - 2:
        i0 = int(tt0 * SR); seg = np.arange(int(.35 * SR)) / SR; f = 50 + 90 * np.exp(-seg * 30)
        mus[i0:i0 + len(seg)] += .14 * np.exp(-seg * 9) * np.sin(2 * np.pi * np.cumsum(f) / SR); tt0 += beat
    mus *= np.clip((TOTAL + .2 - t) / 2.5, 0, 1)
    sfx = np.zeros(N, np.float32)
    for sc in TL[1:]:
        i0 = int((sc['start'] - .25) * SR); L_ = int(.6 * SR); seg = np.arange(L_) / SR
        n = np.convolve(np.random.default_rng(int(sc['start'] * 10)).normal(0, 1, L_), np.ones(24) / 24, 'same')
        sfx[i0:i0 + L_] += .3 * n * np.sin(np.pi * seg / .6) ** 2
    env = np.convolve(np.abs(voice), np.ones(int(.25 * SR)) / int(.25 * SR), 'same'); env = np.clip(env / .05, 0, 1)
    out = voice + mus * (1 - .55 * env) + sfx * .6; out /= max(1.0, np.abs(out).max() / .95)
    f32 = os.path.join(AUD, 'mix.f32'); out[:int(TOTAL * SR)].astype(np.float32).tofile(f32)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', f32, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',
                    '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k', os.path.join(AUD, 'mix.m4a')], check=True)

def srt(path):
    def ts(x): return f"00:{int(x // 60):02d}:{int(x % 60):02d},{int((x - int(x)) * 1000):03d}"
    out = []; n = 1
    for sc in TL:
        for a, b, txt, _ in sc['lines']: out.append(f"{n}\n{ts(sc['start'] + a)} --> {ts(sc['start'] + b)}\n{txt}\n"); n += 1
    open(path, 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    what = ONLY or (sys.argv[2] if len(sys.argv) > 2 else 'both'); pv = '--preview' in sys.argv
    OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
    print(CFG['id'], 'TOTAL', round(TOTAL, 1), 's', [s['scene'] for s in TL])
    modes = ['reel', 'wide'] if what == 'both' else [what]
    if pv:
        for m in modes:
            ims = R(m).render(None, preview=True); w = 540 if m == 'reel' else 640; h = int(w * ims[0].height / ims[0].width)
            sheet = Image.new('RGB', (w * len(ims), h))
            for i, im in enumerate(ims): sheet.paste(im.resize((w, h)), (i * w, 0))
            sheet.save(os.path.join(OUT, f"{CFG['id']}_{m}_preview.jpg"), quality=82)
        sys.exit()
    if not os.path.exists(os.path.join(AUD, 'mix.m4a')): mix()
    srt(os.path.join(OUT, f"{CFG['id']}.ko.srt"))
    for m in modes:
        R(m).render(os.path.join(OUT, f"{CFG['id']}_{m}.mp4")); print('done', m)
