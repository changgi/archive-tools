# 「고문서 한 장」 가상 전시관 — examples/museum.html (three.js, 걸어 다니며 보는 3D 전시실)
#   세기별로 방을 나누고(15–16 · 17 · 18 · 19 · 20세기 · 때를 모르는 종이), 편마다 첫 문서를 액자로 건다.
#   방마다 스크린 하나 — 그 방의 릴스를 차례로 이어 재생. 액자를 누르면 확대 · 판독 · 번역 · 릴스 · 전시 웹페이지.
#   읽는 것: examples/viewer-data.json(편 · 문서 · 썸네일 크기) + examples/index.html의 IT(영상 주소). 다시 돌려도 같은 결과.
#   이미지 · 영상은 archive-tools-next(IIIF · media)에 있는 것을 그대로 쓴다 — 이 페이지는 새 이미지를 만들지 않는다.
import _paths as P
import json, re, os, collections

R = P.REPO + '/examples/'
V = json.load(open(R + 'viewer-data.json', encoding='utf-8'))
IT = json.loads(re.search(r'const IT\s*=\s*(\[.*?\]);\s*\n', open(R + 'index.html', encoding='utf-8').read(), re.S).group(1))
VBY = {i['f']: i for i in IT if i.get('f')}

def years(e):
    out = []
    for d in e['d']:
        m = re.match(r'(\d{4})', str(d.get('y') or ''))
        if m: out.append(int(m.group(1)))
    return out

ROOMS = [('15–16세기', lambda y: y is not None and y < 1600), ('17세기', lambda y: y is not None and 1600 <= y < 1700),
         ('18세기', lambda y: y is not None and 1700 <= y < 1800), ('19세기', lambda y: y is not None and 1800 <= y < 1900),
         ('20세기', lambda y: y is not None and y >= 1900), ('때를 모르는 종이', lambda y: y is None)]
rooms = [dict(name=n, eps=[]) for n, _ in ROOMS]
for e in sorted([e for e in V['eps'] if e.get('ep')], key=lambda e: e['ep']):
    ys = years(e); y0 = min(ys) if ys else None
    k = next(i for i, (_, f) in enumerate(ROOMS) if f(y0))
    it = VBY.get(e['f'], {})
    d0 = e['d'][0]
    rooms[k]['eps'].append(dict(ep=e['ep'], f=e['f'], t=e['t'], c=e.get('c', ''), k=e.get('k', ''), n=len(e['d']),
                                tw=d0.get('tw') or 300, th=d0.get('th') or 360, y=(f"{min(ys)}" if ys and min(ys) == max(ys) else (f"{min(ys)}–{max(ys)}" if ys else '')),
                                reel=it.get('reel', ''), rp=it.get('rp', ''), vtt=it.get('vtt', '')))
for r in rooms:
    ty = collections.Counter(d.get('ty') or '' for e in V['eps'] if e.get('ep') and any(x['f'] == e['f'] for x in r['eps']) for d in e['d'])
    ys = [y for x in r['eps'] for y in years(next(e for e in V['eps'] if e['f'] == x['f']))]
    r['docs'] = sum(x['n'] for x in r['eps'])
    r['types'] = [t for t, _ in ty.most_common(4) if t]
    r['span'] = f"{min(ys)}–{max(ys)}" if ys else ''
rooms = [r for r in rooms if r['eps']]
DATA = dict(base=V['base'], next=P.NEXT_URL, rooms=rooms,
            lobby=dict(reel=P.NEXT_URL + 'promo-reel-200.mp4', rp='media/promo-reel-200-poster.jpg', vtt='media/promo-reel-200.ko.vtt'))
NEPS = sum(len(r['eps']) for r in rooms); NDOCS = sum(r['docs'] for r in rooms)

PAGE = r'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>고문서 한 장 — 가상 전시관</title>
<meta name="description" content="「고문서 한 장」 __NEPS__편을 세기별 전시실에 걸었습니다. 걸어 다니며 액자를 누르면 원문 판독 · 번역 · 릴스를 볼 수 있습니다.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%2316130f'/%3E%3Crect x='14' y='10' width='36' height='44' rx='3' fill='%23efe4cc'/%3E%3C/svg%3E">
<style>
:root{--bg:#16130f;--ink:#efe4cc;--dim:#a99d86;--gold:#c4964a;--line:#4a3e2c}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font-family:'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif;overflow:hidden;-webkit-tap-highlight-color:transparent}
#c{position:fixed;inset:0;width:100vw;height:100vh;display:block;touch-action:none;cursor:grab}#c.drag{cursor:grabbing}
.hud{position:fixed;left:0;right:0;top:0;display:flex;gap:10px;align-items:center;padding:10px 14px;background:linear-gradient(#16130fee,#16130f00);pointer-events:none;z-index:5}
.hud *{pointer-events:auto}.hud a,.hud button{white-space:nowrap;color:var(--ink);background:#231d15cc;border:1px solid var(--line);border-radius:20px;padding:6px 12px;font-size:13.5px;text-decoration:none;cursor:pointer;font-family:inherit}
.hud .t{font-weight:700;font-size:15px;margin-right:auto;pointer-events:none}.hud .t em{color:var(--gold);font-style:normal;font-weight:400;margin-left:8px;font-size:13px}
.prog{position:fixed;left:14px;right:14px;top:52px;height:3px;background:#ffffff14;border-radius:3px;z-index:5;pointer-events:none}.prog i{display:block;height:100%;width:0;background:var(--gold);border-radius:3px}
.pad{position:fixed;bottom:calc(16px + env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:5}
.pad button{white-space:nowrap;min-width:54px;height:46px;border-radius:23px;border:1px solid var(--line);background:#231d15dd;color:var(--ink);font-size:15px;cursor:pointer;font-family:inherit;padding:0 14px}
.pad button:active{background:#3a3020}.pad .g{background:#3a2f1c;border-color:var(--gold)}
.tip{position:fixed;bottom:calc(74px + env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);font-size:13px;color:var(--dim);background:#16130fcc;padding:5px 12px;border-radius:14px;z-index:4;white-space:nowrap;pointer-events:none;transition:opacity .6s}
#ov{position:fixed;inset:0;background:#0b0907f2;z-index:20;display:none;grid-template-columns:minmax(0,1.25fr) minmax(320px,1fr);gap:0}
#ov.on{display:grid}#ov .im{position:relative;display:flex;align-items:center;justify-content:center;padding:54px 16px 70px;min-height:0;overflow:hidden}
#ov .im img{max-width:100%;max-height:100%;object-fit:contain;box-shadow:0 8px 40px #000a;background:#222;transform-origin:center;transition:transform .15s}
#ov .im video{max-width:100%;max-height:100%;background:#000}
#ov .tabs{position:absolute;bottom:16px;left:0;right:0;display:flex;gap:6px;justify-content:center;flex-wrap:wrap}
#ov .tabs button{border:1px solid var(--line);background:#231d15;color:var(--ink);border-radius:16px;padding:4px 11px;font-size:13px;cursor:pointer;font-family:inherit}#ov .tabs button.on{border-color:var(--gold);color:var(--gold)}
#ov .tx{overflow:auto;padding:54px 22px 30px;border-left:1px solid var(--line);background:#16130f}
#ov .tg{color:var(--gold);font-size:13px}#ov h2{font-family:'Noto Serif KR',serif;font-size:21px;line-height:1.45;margin:6px 0 4px}#ov .who{color:var(--dim);font-size:13.5px;margin-bottom:12px}
#ov h3{font-size:15px;margin:16px 0 4px;color:var(--ink)}#ov p{font-size:14.5px;line-height:1.75;margin:4px 0;color:#ddd2bb;white-space:pre-wrap}
#ov .src{font-family:'Noto Serif KR',serif;color:#efe4cc;background:#1f1a14;border:1px solid #3a3225;border-radius:10px;padding:10px 12px}
#ov .btns{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}#ov .btns a,#ov .btns button{color:var(--ink);border:1px solid var(--line);background:#231d15;border-radius:18px;padding:6px 12px;font-size:13.5px;text-decoration:none;cursor:pointer;font-family:inherit}
#ov .btns .pri{border-color:var(--gold);color:var(--gold)}
#ov .x{position:absolute;top:12px;right:14px;z-index:3;width:38px;height:38px;border-radius:19px;border:1px solid var(--line);background:#231d15;color:var(--ink);font-size:18px;cursor:pointer}
#ov .nav{position:absolute;top:12px;left:14px;z-index:3;display:flex;gap:6px}#ov .nav button{height:34px;border-radius:17px;border:1px solid var(--line);background:#231d15;color:var(--ink);padding:0 12px;cursor:pointer;font-family:inherit;font-size:13px}
#ov .note{font-size:12.5px;color:var(--dim);margin-top:18px;line-height:1.6}
#ls{position:fixed;top:0;right:0;bottom:0;width:min(420px,92vw);background:#16130ff7;border-left:1px solid var(--line);z-index:15;transform:translateX(105%);transition:transform .25s;display:flex;flex-direction:column}
#ls.on{transform:none}#ls header{padding:14px;border-bottom:1px solid var(--line);display:flex;gap:8px}#ls input{flex:1;background:#231d15;border:1px solid var(--line);color:var(--ink);border-radius:18px;padding:7px 12px;font-family:inherit;font-size:14px}
#ls header button{background:#231d15;border:1px solid var(--line);color:var(--ink);border-radius:18px;padding:0 12px;cursor:pointer}
#ls .l{overflow:auto;padding:6px 10px 30px}#ls h4{color:var(--gold);margin:14px 4px 4px;font-size:14px}#ls button.it{display:block;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid #2a241b;color:var(--ink);padding:7px 4px;font-size:13.5px;cursor:pointer;font-family:inherit;line-height:1.45}
#ls button.it b{color:var(--gold);font-weight:600;margin-right:6px}#ls button.it:hover{background:#231d15}
#help{position:fixed;inset:0;z-index:25;background:#0b0907e8;display:none;align-items:center;justify-content:center;padding:20px}#help.on{display:flex}
#help div{max-width:520px;background:#1d1812;border:1px solid var(--line);border-radius:16px;padding:22px 24px;line-height:1.75;font-size:14.5px}#help h2{margin:0 0 8px;font-family:'Noto Serif KR',serif}#help kbd{background:#2c2519;border:1px solid var(--line);border-radius:5px;padding:0 6px;font-size:13px}
#help button{margin-top:12px;border:1px solid var(--gold);color:var(--gold);background:none;border-radius:18px;padding:7px 16px;cursor:pointer;font-family:inherit}
#load{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:30;background:var(--bg);flex-direction:column;gap:10px;text-align:center;padding:20px}
#load b{font-family:'Noto Serif KR',serif;font-size:24px}#load span{color:var(--dim);font-size:14px}
@media (max-width:560px){.hud{gap:6px;padding:8px 8px}.hud .t{font-size:13px}.hud a,.hud button{padding:5px 9px;font-size:12.5px}#bHelp{display:none}.pad button{min-width:46px;padding:0 11px}}
@media (max-width:820px){#ov.on{grid-template-columns:1fr;grid-template-rows:52vh auto;overflow:auto}#ov .im{padding:50px 8px 56px}#ov .tx{border-left:0;border-top:1px solid var(--line);overflow:visible}.hud .t em{display:none}.hud a.hide-s{display:none}}
</style></head><body>
<canvas id="c" aria-label="가상 전시관 3D 화면 — 액자를 누르면 문서 정보가 열립니다"></canvas>
<div id="load"><b>고문서 한 장 — 가상 전시관</b><span>전시실을 짓는 중…</span><noscript><span>이 전시관은 JavaScript와 WebGL이 필요합니다. <a href="viewer.html" style="color:#c4964a">연속 보기 뷰어</a>로 보세요.</span></noscript></div>
<div class="hud"><span class="t">고문서 한 장 — 가상 전시관<em id="room">로비</em></span>
<button id="bList" type="button">목록</button><button id="bSnd" type="button" aria-pressed="false">🔇 소리</button><button id="bHelp" type="button">조작법</button>
<a class="hide-s" href="viewer.html">연속 보기</a><a href="index.html">← 갤러리</a></div>
<div class="prog"><i id="pg"></i></div>
<div class="tip" id="tip">끌어서 둘러보기 · W/↑ 앞으로 · ▶ 다음 작품 · 액자를 누르면 원문</div>
<div class="pad"><button type="button" id="bPrev" aria-label="이전 작품">◀</button><button type="button" id="bBack" aria-label="뒤로">▼</button><button type="button" id="bFwd" aria-label="앞으로">▲</button><button type="button" id="bNext" class="g" aria-label="다음 작품">다음 작품 ▶</button></div>
<div id="ov" role="dialog" aria-modal="true" aria-labelledby="ovT"><div class="im" id="ovIm"></div><div class="tx" id="ovTx"></div>
<div class="nav"><button type="button" id="oPrev">◀ 이전 편</button><button type="button" id="oNext">다음 편 ▶</button></div><button class="x" type="button" id="oX" aria-label="닫기">✕</button></div>
<aside id="ls" aria-label="전시 목록"><header><input id="q" type="search" placeholder="편 · 제목 · 소장처 찾기" aria-label="찾기"><button type="button" id="lsX">닫기</button></header><div class="l" id="lsL"></div></aside>
<div id="help" role="dialog" aria-modal="true"><div><h2>조작법</h2>
<b>둘러보기</b> — 화면을 끌기(마우스 · 손가락)<br><b>걷기</b> — <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> 또는 방향키 · 아래 ▲▼ 버튼을 누르고 있기 · <kbd>Shift</kbd> 빠르게<br>
<b>작품 사이 이동</b> — ◀ / 다음 작품 ▶ (또는 <kbd>Q</kbd> <kbd>E</kbd>) — 다음 액자 앞으로 데려다 줍니다<br><b>자세히 보기</b> — 액자를 누르기 · <kbd>Enter</kbd> 지금 앞에 있는 액자 열기 · <kbd>Esc</kbd> 닫기<br>
<b>릴스</b> — 방마다 왼쪽 스크린에서 그 방의 릴스가 차례로 이어집니다. 스크린을 누르면 그 편이 열리고, 위의 「소리」로 소리를 켭니다.<br>
<b>목록</b> — 편 번호 · 제목으로 찾아 바로 그 액자 앞으로 갑니다. 주소 끝에 <kbd>#ep200</kbd>처럼 붙여도 됩니다.<br>
<span style="color:#a99d86;font-size:13px">세기는 각 편 첫 문서 기준이 아니라 편 안의 가장 이른 연도로 나눴습니다. 고문서 이미지: 한국학중앙연구원 한국고문서자료관 소장 · 제공(각 소장처 기탁) — 다시 쓰려면 자료관을 통한 소장처 동의가 필요하며, 문제가 있으면 내립니다. 엮은이: Song Chang-gi (chgsong@naver.com, github.com/changgi)</span><br>
<button type="button" id="hX">전시실로 들어가기</button></div></div>
<script>window.MUSEUM=__DATA__;</script>
<script type="module">
import * as THREE from './vendor/three-0.170.0.module.min.js';
const D=window.MUSEUM, $=s=>document.getElementById(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let canGL=true;try{const t=document.createElement('canvas');canGL=!!(t.getContext('webgl2')||t.getContext('webgl'))}catch(e){canGL=false}
if(!canGL){$('load').innerHTML='<b>이 기기에서는 3D 전시관을 열 수 없습니다</b><span>WebGL을 쓸 수 없습니다. <a href="viewer.html" style="color:#c4964a">연속 보기 뷰어</a>나 <a href="index.html" style="color:#c4964a">갤러리</a>로 보세요.</span>';throw new Error('no webgl')}
// ---------- 배치 ----------
const W=9, H=4.6, S=3.4, ENT=6, GAP=2.4, SX=W/2;
const EPS=[]; const ROOMS=[]; let z=-10;            // 로비: z 4 → -10
D.rooms.forEach((r,ri)=>{const z0=z; z-=ENT; const n=r.eps.length;
  r.eps.forEach((e,k)=>{const slot=Math.floor(k/2), side=k%2?1:-1; e.z=z-slot*S-S/2; e.side=side; e.room=ri; e.i=EPS.length; EPS.push(e)});
  z-=Math.ceil(n/2)*S+GAP; ROOMS.push({...r,z0,z1:z,ri})});
const ZEND=z; const LOBBY={z0:4,z1:-10};
// ---------- 장면 ----------
const cv=$('c'); const R=new THREE.WebGLRenderer({canvas:cv,antialias:true,powerPreference:'high-performance'});
R.setPixelRatio(Math.min(devicePixelRatio,1.75)); R.setSize(innerWidth,innerHeight); R.outputColorSpace=THREE.SRGBColorSpace;
const SC=new THREE.Scene(); SC.background=new THREE.Color(0x15120e); SC.fog=new THREE.Fog(0x15120e,14,52);
const CAM=new THREE.PerspectiveCamera(62,innerWidth/innerHeight,0.05,90); CAM.rotation.order='YXZ'; CAM.position.set(0,1.62,2.2);
SC.add(new THREE.HemisphereLight(0xfff3dd,0x2a2218,1.05)); const dl=new THREE.DirectionalLight(0xffe9c4,.35); dl.position.set(2,6,3); SC.add(dl);
function ctex(w,h,draw){const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d');draw(g,w,h);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=4;return t}
const FONT='"Noto Sans KR","Apple SD Gothic Neo","Malgun Gothic",sans-serif', SERIF='"Noto Serif KR","Nanum Myeongjo",serif';
function wrap(g,text,x,y,maxW,lh,maxL){const out=[];let line='';for(const ch of String(text)){const t=line+ch;if(g.measureText(t).width>maxW&&line){out.push(line);line=ch;if(out.length>=maxL)break}else line=t}
  if(out.length<maxL&&line)out.push(line);else if(line&&out.length>=maxL){out[maxL-1]=out[maxL-1].slice(0,-1)+'…'}out.slice(0,maxL).forEach((l,i)=>g.fillText(l,x,y+i*lh));return out.length}
// 바닥 · 벽 · 천장
const total=LOBBY.z0-ZEND+2, zc=(LOBBY.z0+ZEND)/2;
const floorT=ctex(512,512,(g,w,h)=>{g.fillStyle='#3b2a1c';g.fillRect(0,0,w,h);for(let i=0;i<8;i++){const y=i*64;g.fillStyle=i%2?'#3f2e1f':'#36271a';g.fillRect(0,y,w,62);g.fillStyle='#2a1e14';g.fillRect(0,y+62,w,2);
  for(let k=0;k<40;k++){g.fillStyle=`rgba(${20+Math.random()*30},${12+Math.random()*16},6,.18)`;g.fillRect(Math.random()*w,y+Math.random()*60,30+Math.random()*120,1)}g.fillStyle='#2a1e14';g.fillRect((i*197)%w,y,2,62)}});
floorT.wrapS=floorT.wrapT=THREE.RepeatWrapping; floorT.repeat.set(W/3,total/3);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(W,total),new THREE.MeshLambertMaterial({map:floorT})); floor.rotation.x=-Math.PI/2; floor.position.set(0,0,zc); SC.add(floor);
const ceil=new THREE.Mesh(new THREE.PlaneGeometry(W,total),new THREE.MeshBasicMaterial({color:0x100d0a})); ceil.rotation.x=Math.PI/2; ceil.position.set(0,H,zc); SC.add(ceil);
const wallM=new THREE.MeshLambertMaterial({color:0x3a3128});
for(const s of [-1,1]){const w=new THREE.Mesh(new THREE.PlaneGeometry(total,H),wallM); w.rotation.y=-s*Math.PI/2; w.position.set(s*SX,H/2,zc); SC.add(w)}
const endW=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM); endW.position.set(0,H/2,ZEND-1); SC.add(endW);
const backW=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM); backW.rotation.y=Math.PI; backW.position.set(0,H/2,LOBBY.z0+1); SC.add(backW);
// 천장 조명 줄
const lampM=new THREE.MeshBasicMaterial({color:0xffe2b0}); const lampG=new THREE.BoxGeometry(.12,.04,1.2);
for(let zz=LOBBY.z0-1;zz>ZEND;zz-=S){for(const s of [-1,1]){const l=new THREE.Mesh(lampG,lampM);l.position.set(s*(SX-1.1),H-.02,zz);SC.add(l)}}
// 벽에 비치는 빛 웅덩이(공유 텍스처)
const poolT=ctex(256,256,(g,w,h)=>{const r=g.createRadialGradient(w/2,h*.38,4,w/2,h*.45,w*.5);r.addColorStop(0,'rgba(255,226,170,.55)');r.addColorStop(.55,'rgba(255,210,150,.14)');r.addColorStop(1,'rgba(255,200,140,0)');g.fillStyle=r;g.fillRect(0,0,w,h)});
const poolM=new THREE.MeshBasicMaterial({map:poolT,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending});
// 칸막이 · 문 위 간판
function sign(text,sub,z){const t=ctex(1024,200,(g,w,h)=>{g.fillStyle='#1d1812';g.fillRect(0,0,w,h);g.strokeStyle='#c4964a';g.lineWidth=4;g.strokeRect(8,8,w-16,h-16);g.fillStyle='#e9cf9c';g.font=`700 64px ${SERIF}`;g.textAlign='center';g.fillText(text,w/2,96);
  g.fillStyle='#b9ab90';g.font=`30px ${FONT}`;g.fillText(sub,w/2,150)});const m=new THREE.Mesh(new THREE.PlaneGeometry(4.6,.9),new THREE.MeshBasicMaterial({map:t}));m.position.set(0,H-.62,z);SC.add(m);
  const b=m.clone();b.rotation.y=Math.PI;b.position.z=z-.02;SC.add(b)}
const PARTS=[];
function partition(z,label,sub){const segW=(W-3.2)/2;for(const s of [-1,1]){const p=new THREE.Mesh(new THREE.BoxGeometry(segW,H,.25),wallM);p.position.set(s*(SX-segW/2),H/2,z);SC.add(p)}
  const top=new THREE.Mesh(new THREE.BoxGeometry(3.2,H-3.1,.25),wallM);top.position.set(0,3.1+(H-3.1)/2,z);SC.add(top);PARTS.push(z);if(label)sign(label,sub,z+.14)}
partition(LOBBY.z1,ROOMS[0].name,`${ROOMS[0].eps.length}편 · 문서 ${ROOMS[0].docs}건 · ${ROOMS[0].span}`);
ROOMS.forEach((r,i)=>{const nx=ROOMS[i+1];partition(r.z1,nx?nx.name:'',nx?`${nx.eps.length}편 · 문서 ${nx.docs}건${nx.span?' · '+nx.span:''}`:'')});
// 글 패널(벽에 붙임)
function panel(x,z,side,w,h,draw){const t=ctex(Math.round(w*220),Math.round(h*220),draw);const m=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map:t}));
  m.position.set(x,1.9,z);m.rotation.y=side<0?Math.PI/2:-Math.PI/2;SC.add(m);return m}
// 로비
panel(-SX+.03,-3.2,-1,3.6,2.4,(g,w,h)=>{g.fillStyle='#1d1812';g.fillRect(0,0,w,h);g.fillStyle='#c4964a';g.font=`26px ${FONT}`;g.fillText('ARCHIVE TOOLS · 「고문서 한 장」',40,64);
  g.fillStyle='#efe4cc';g.font=`700 72px ${SERIF}`;g.fillText('고문서 한 장',40,160);g.font=`700 44px ${SERIF}`;g.fillText('가상 전시관',40,224);
  g.fillStyle='#cfc3aa';g.font=`26px ${FONT}`;wrap(g,`EP.1부터 EP.${EPS.length?Math.max(...EPS.map(e=>e.ep)):200}까지 ${EPS.length}편, 문서 ${D.rooms.reduce((a,r)=>a+r.docs,0)}건. 편마다 첫 문서 한 장을 세기별 방에 걸었습니다. 액자를 누르면 원문 판독과 번역, 그 편의 릴스가 열립니다.`,40,300,w-80,40,5)});
panel(SX-.03,-3.2,1,3.6,2.4,(g,w,h)=>{g.fillStyle='#1d1812';g.fillRect(0,0,w,h);g.fillStyle='#e9cf9c';g.font=`700 40px ${SERIF}`;g.fillText('전시실 안내',40,76);g.font=`28px ${FONT}`;
  ROOMS.forEach((r,i)=>{g.fillStyle='#efe4cc';g.fillText(r.name,40,140+i*52);g.fillStyle='#a99d86';g.fillText(`${r.eps.length}편 · 문서 ${r.docs}건`,330,140+i*52)});
  g.fillStyle='#a99d86';g.font=`22px ${FONT}`;g.fillText('끌어서 둘러보기 · ▲ 걷기 · 다음 작품 ▶ · 액자 누르기',40,h-36)});
// ---------- 스크린(방마다 하나, 영상은 하나를 돌려 씀) ----------
const VID=document.createElement('video'); VID.muted=true; VID.playsInline=true; VID.crossOrigin='anonymous'; VID.preload='none'; VID.setAttribute('playsinline','');
const vtex=new THREE.VideoTexture(VID); vtex.colorSpace=THREE.SRGBColorSpace;
const SCREENS=[];
function screen(z,list,label){const g=new THREE.Group();const fr=new THREE.Mesh(new THREE.BoxGeometry(.08,2.62,1.56),new THREE.MeshLambertMaterial({color:0x111111}));g.add(fr);
  const idle=ctex(360,640,(c,w,h)=>{c.fillStyle='#0d0b09';c.fillRect(0,0,w,h);c.fillStyle='#c4964a';c.font=`700 30px ${FONT}`;c.textAlign='center';c.fillText('▶ 릴스',w/2,h/2-10);c.fillStyle='#a99d86';c.font=`22px ${FONT}`;c.fillText(label,w/2,h/2+30);c.fillText(`${list.length}편 이어 보기`,w/2,h/2+62)});
  const scr=new THREE.Mesh(new THREE.PlaneGeometry(1.4,2.49),new THREE.MeshBasicMaterial({map:idle}));scr.position.x=.05;scr.rotation.y=Math.PI/2;g.add(scr);
  const capC=document.createElement('canvas');capC.width=720;capC.height=150;const capT=new THREE.CanvasTexture(capC);capT.colorSpace=THREE.SRGBColorSpace;
  const cap=new THREE.Mesh(new THREE.PlaneGeometry(1.9,.4),new THREE.MeshBasicMaterial({map:capT,transparent:true}));cap.position.set(.05,-1.58,0);cap.rotation.y=Math.PI/2;g.add(cap);
  g.position.set(-SX+.06,1.95,z);SC.add(g);const o={scr,idle,capC,capT,list,k:0,label};scr.userData.screen=o;SCREENS.push(o);return o}
function capDraw(o,txt){const g=o.capC.getContext('2d');g.clearRect(0,0,720,150);g.fillStyle='#16130fdd';g.fillRect(0,0,720,150);g.fillStyle='#e9cf9c';g.font=`600 30px ${FONT}`;wrap(g,txt,20,52,680,42,2);o.capT.needsUpdate=true}
const lobbyScr=screen(-7.2,[{ep:null,t:'200편 기념 영상',reel:D.lobby.reel,rp:D.lobby.rp}],'200편 기념');
ROOMS.forEach(r=>{r.screen=screen(r.z0-ENT/2,r.eps.filter(e=>e.reel),r.name)});
// 방 소개 패널(오른쪽 벽, 입구)
ROOMS.forEach(r=>panel(SX-.03,r.z0-ENT/2,1,3.2,2.1,(g,w,h)=>{g.fillStyle='#1d1812';g.fillRect(0,0,w,h);g.fillStyle='#e9cf9c';g.font=`700 64px ${SERIF}`;g.fillText(r.name,40,100);
  g.fillStyle='#efe4cc';g.font=`30px ${FONT}`;g.fillText(`${r.eps.length}편 · 문서 ${r.docs}건${r.span?' · '+r.span+'년':''}`,40,160);g.fillStyle='#b9ab90';g.font=`26px ${FONT}`;
  wrap(g,'많이 나온 문서: '+(r.types.join(' · ')||'—'),40,220,w-80,38,2);wrap(g,`EP.${r.eps[0].ep}부터 — 왼쪽 스크린에서 이 방의 릴스가 차례로 이어집니다.`,40,320,w-80,38,2)}));
let curScreen=null;
function playOn(o){if(curScreen&&curScreen!==o){curScreen.scr.material.map=curScreen.idle;curScreen.scr.material.needsUpdate=true}
  curScreen=o;if(!o||!o.list.length){VID.pause();return}const e=o.list[o.k%o.list.length];if(VID.dataset.src!==e.reel){VID.dataset.src=e.reel;VID.src=e.reel;VID.load()}
  VID.play().then(()=>{o.scr.material.map=vtex;o.scr.material.needsUpdate=true}).catch(()=>{});capDraw(o,(e.ep?`EP.${e.ep} · `:'')+(e.t||'').split(' — ')[0])}
VID.addEventListener('ended',()=>{if(curScreen){curScreen.k++;playOn(curScreen)}});
// ---------- 액자 ----------
const FRAMES=[]; const frameM=new THREE.MeshLambertMaterial({color:0x6b4e2a}); const matM=new THREE.MeshLambertMaterial({color:0xe9e0cc});
const ph=ctex(64,64,(g)=>{g.fillStyle='#2c251c';g.fillRect(0,0,64,64)});
EPS.forEach(e=>{const a=e.tw/e.th;let w=2.3,h=w/a;if(h>2.1){h=2.1;w=h*a}const g=new THREE.Group();
  const fr=new THREE.Mesh(new THREE.BoxGeometry(w+.34,h+.34,.06),frameM);g.add(fr);const mt=new THREE.Mesh(new THREE.PlaneGeometry(w+.2,h+.2),matM);mt.position.z=.032;g.add(mt);
  const im=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map:ph}));im.position.z=.036;g.add(im);
  const pool=new THREE.Mesh(new THREE.PlaneGeometry(w+2.2,h+2.4),poolM);pool.position.set(0,.25,-.01);g.add(pool);
  const pl=new THREE.Mesh(new THREE.PlaneGeometry(1.5,.42),new THREE.MeshBasicMaterial({map:ph}));pl.position.set(0,-h/2-.48,.01);g.add(pl);
  g.position.set(e.side*(SX-.05),2.05,e.z);g.rotation.y=e.side<0?Math.PI/2:-Math.PI/2;SC.add(g);
  im.userData.ep=e;fr.userData.ep=e;pl.userData.ep=e;Object.assign(e,{g,im,pl,loaded:0});FRAMES.push(im,fr,pl)});
const TL=new THREE.TextureLoader(); TL.setCrossOrigin('anonymous');
function plaque(e){return ctex(480,134,(g,w,h)=>{g.fillStyle='#e9e0cc';g.fillRect(0,0,w,h);g.fillStyle='#7a5a2c';g.font=`700 26px ${FONT}`;g.fillText(`EP.${e.ep}${e.y?' · '+e.y:''}`,18,38);
  g.fillStyle='#2a2117';g.font=`600 24px ${FONT}`;wrap(g,e.t.split(' — ')[0],18,74,w-36,30,2)})}
function updLoads(){const cz=CAM.position.z;for(const e of EPS){const d=Math.abs(e.z-cz);
  if(d<30&&!e.loaded){e.loaded=1;TL.load(`${D.base}${e.f}/thumb/01.jpg`,t=>{t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=4;if(e.loaded){e.im.material.map=t;e.im.material.needsUpdate=true;e.tex=t}else t.dispose()},undefined,()=>{});
    e.ptex=plaque(e);e.pl.material.map=e.ptex;e.pl.material.needsUpdate=true}
  else if(d>48&&e.loaded){e.loaded=0;if(e.tex){e.tex.dispose();e.tex=null}if(e.ptex){e.ptex.dispose();e.ptex=null}e.im.material.map=ph;e.pl.material.map=ph;e.im.material.needsUpdate=e.pl.material.needsUpdate=true}}}
// ---------- 움직임 ----------
let yaw=0,pitch=0,tween=null;const keys={};let hold=0;
addEventListener('keydown',ev=>{if(ov.classList.contains('on')||ev.target.tagName==='INPUT'){if(ev.key==='Escape')closeOv();if(ov.classList.contains('on')&&ev.key==='ArrowRight')stepOv(1);if(ov.classList.contains('on')&&ev.key==='ArrowLeft')stepOv(-1);return}
  keys[ev.code]=1;if(ev.code==='KeyE'||ev.code==='Period')go(1);if(ev.code==='KeyQ'||ev.code==='Comma')go(-1);if(ev.code==='Enter'){const e=near();if(e)openOv(e)}if(ev.key==='Escape'){$('ls').classList.remove('on');$('help').classList.remove('on')}});
addEventListener('keyup',ev=>{keys[ev.code]=0});
let drag=null,moved=0;
cv.addEventListener('pointerdown',ev=>{drag={x:ev.clientX,y:ev.clientY,id:ev.pointerId};moved=0;cv.setPointerCapture(ev.pointerId);cv.classList.add('drag')});
cv.addEventListener('pointermove',ev=>{if(!drag||drag.id!==ev.pointerId)return;const dx=ev.clientX-drag.x,dy=ev.clientY-drag.y;moved+=Math.abs(dx)+Math.abs(dy);drag.x=ev.clientX;drag.y=ev.clientY;
  const k=ev.pointerType==='touch'?.0055:.0035;yaw+=dx*k;pitch=Math.max(-1.1,Math.min(1.1,pitch+dy*k));tween=null});
cv.addEventListener('pointerup',ev=>{cv.classList.remove('drag');if(drag&&moved<8)pick(ev);drag=null});
const RC=new THREE.Raycaster(),MV=new THREE.Vector2();
function pick(ev){MV.set(ev.clientX/innerWidth*2-1,-(ev.clientY/innerHeight)*2+1);RC.setFromCamera(MV,CAM);const hits=RC.intersectObjects([...FRAMES,...SCREENS.map(s=>s.scr)],false);
  for(const h of hits){if(h.distance>16)break;if(h.object.userData.ep){openOv(h.object.userData.ep);return}if(h.object.userData.screen){const o=h.object.userData.screen,e=o.list[o.k%o.list.length];
    if(e&&e.ep){openOv(EPS.find(x=>x.ep===e.ep),true)}else{setSnd(true);playOn(o)}return}}}
function holdBtn(id,dir){const b=$(id);const on=ev=>{ev.preventDefault();hold=dir;tween=null},off=()=>{hold=0};b.addEventListener('pointerdown',on);['pointerup','pointerleave','pointercancel'].forEach(t=>b.addEventListener(t,off))}
holdBtn('bFwd',1);holdBtn('bBack',-1);$('bNext').onclick=()=>go(1);$('bPrev').onclick=()=>go(-1);
const DIST=()=>CAM.aspect<.8?5:3.1;  // 세로 화면은 한 걸음 물러서서
function standFor(e){return{x:e.side*(SX-DIST()),z:e.z,yaw:e.side<0?Math.PI/2:-Math.PI/2}}
function near(){let best=null,bd=1e9;const p=CAM.position;for(const e of EPS){const s=standFor(e);const d=Math.hypot(p.x-s.x,p.z-s.z);if(d<bd){bd=d;best=e}}return bd<3?best:null}
let cursor=-1;
function go(dir){let i;const n=near();if(n)i=n.i+dir;else{const cz=CAM.position.z;i=dir>0?EPS.findIndex(e=>e.z<cz-.1):(()=>{let j=-1;EPS.forEach((e,k)=>{if(e.z>cz+.1)j=k});return j})()}
  if(i<0){flyTo({x:0,z:2.2,yaw:0});cursor=-1;return}if(i>=EPS.length)i=EPS.length-1;cursor=i;const e=EPS[i];flyTo(standFor(e));history.replaceState(null,'','#ep'+e.ep)}
function flyTo(t){const p=CAM.position;let dy=((t.yaw-yaw+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI;tween={sx:p.x,sz:p.z,sy:yaw,sp:pitch,tx:t.x,tz:t.z,ty:yaw+dy,t:0,d:Math.min(2.2,.6+Math.hypot(t.x-p.x,t.z-p.z)/14)}}
function crosses(z0,z1,x){for(const pz of PARTS){if((z0-pz)*(z1-pz)<=0&&Math.abs(x)>1.45)return true}return false}
const CL=new THREE.Clock();let lastRoom=-2,tipT=0;
function roomAt(z){if(z>LOBBY.z1)return -1;return ROOMS.findIndex(r=>z<=r.z0&&z>r.z1)}
function loop(){const dt=Math.min(CL.getDelta(),.05);const p=CAM.position;
  if(tween){tween.t+=dt/tween.d;const k=tween.t>=1?1:(1-Math.cos(Math.PI*tween.t))/2;p.x=tween.sx+(tween.tx-tween.sx)*k;p.z=tween.sz+(tween.tz-tween.sz)*k;yaw=tween.sy+(tween.ty-tween.sy)*k;pitch=tween.sp*(1-k);if(tween.t>=1)tween=null}
  else{let f=(keys.KeyW||keys.ArrowUp?1:0)-(keys.KeyS||keys.ArrowDown?1:0)+hold,s=(keys.KeyD?1:0)-(keys.KeyA?1:0);if(keys.ArrowLeft)yaw+=1.8*dt;if(keys.ArrowRight)yaw-=1.8*dt;
    if(f||s){const sp=(keys.ShiftLeft||keys.ShiftRight?9:4.2)*dt;const nx=p.x+(-Math.sin(yaw)*f+Math.cos(yaw)*s)*sp,nz=p.z+(-Math.cos(yaw)*f-Math.sin(yaw)*s)*sp;
      const cx=Math.max(-SX+.7,Math.min(SX-.7,nx));if(!crosses(p.z,nz,cx))p.z=Math.max(ZEND-.3,Math.min(LOBBY.z0+.3,nz));p.x=cx}}
  CAM.rotation.set(pitch,yaw,0);const ri=roomAt(p.z);
  if(ri!==lastRoom){lastRoom=ri;$('room').textContent=ri<0?'로비':`${ROOMS[ri].name} · ${ROOMS[ri].eps.length}편`;playOn(ri<0?lobbyScr:ROOMS[ri].screen)}
  $('pg').style.width=Math.max(0,Math.min(100,(LOBBY.z0-p.z)/(LOBBY.z0-ZEND)*100))+'%';
  if((tipT+=dt)>9)$('tip').style.opacity=0;
  if(((CL.elapsedTime*4)|0)%2===0)updLoads();R.render(SC,CAM);requestAnimationFrame(loop)}
function fit(){CAM.aspect=innerWidth/innerHeight;CAM.fov=CAM.aspect<.8?76:62;CAM.updateProjectionMatrix();R.setSize(innerWidth,innerHeight)}
addEventListener('resize',fit);fit();
// ---------- 소리 ----------
function setSnd(on){VID.muted=!on;$('bSnd').textContent=on?'🔊 소리':'🔇 소리';$('bSnd').setAttribute('aria-pressed',on?'true':'false');if(on&&curScreen)VID.play().catch(()=>{})}
$('bSnd').onclick=()=>setSnd(VID.muted);
// ---------- 자세히 보기 ----------
const ov=$('ov');let VD=null,curE=null,curD=0,ovVid=null;
fetch('viewer-data.json').then(r=>r.json()).then(j=>{VD={};j.eps.forEach(e=>VD[e.f]=e.d);if(curE)renderOv()}).catch(()=>{});
function openOv(e,reel){if(!e)return;curE=e;curD=0;ov.classList.add('on');VID.pause();history.replaceState(null,'','#ep'+e.ep);renderOv(reel);flyTo(standFor(e))}
function closeOv(){ov.classList.remove('on');if(ovVid){ovVid.pause();ovVid=null}$('ovIm').innerHTML='';if(curScreen)VID.play().catch(()=>{})}
function stepOv(k){const i=curE.i+k;if(i>=0&&i<EPS.length)openOv(EPS[i])}
$('oX').onclick=closeOv;$('oPrev').onclick=()=>stepOv(-1);$('oNext').onclick=()=>stepOv(1);
function renderOv(reel){const e=curE,ds=VD&&VD[e.f]||[],d=ds[curD]||{};if(ovVid){ovVid.pause();ovVid=null}
  if(reel&&e.reel){$('ovIm').innerHTML=`<video controls autoplay playsinline src="${esc(e.reel)}" poster="${esc(e.rp)}">${e.vtt?`<track kind="subtitles" srclang="ko" label="한국어" src="${esc(e.vtt)}" default>`:''}</video>`;ovVid=$('ovIm').querySelector('video')}
  else{$('ovIm').innerHTML=`<img alt="${esc(d.t||e.t)}" src="${esc(`${D.base}${e.f}/${String(curD+1).padStart(2,'0')}.jpg`)}">`+(ds.length>1?`<div class="tabs">${ds.map((x,i)=>`<button type="button" class="${i===curD?'on':''}" data-i="${i}">${i+1}. ${esc((x.y?x.y+' ':'')+(x.ty||''))}</button>`).join('')}</div>`:'');
    $('ovIm').querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{curD=+b.dataset.i;renderOv()});const img=$('ovIm').querySelector('img');let z=1;img.ondblclick=()=>{z=z>1?1:2.2;img.style.transform=`scale(${z})`}}
  const man=`${D.base}${e.f}/manifest.json`;
  $('ovTx').innerHTML=`<div class="tg">EP.${e.ep} · ${esc(e.k)} · ${esc(ROOMS[e.room].name)}</div><h2 id="ovT">${esc(e.t)}</h2><div class="who">${esc(e.c)}${e.y?' · '+esc(e.y):''} · 문서 ${e.n}건</div>
  <div class="btns">${e.reel?`<button type="button" class="pri" id="oReel">${reel?'문서 보기':'▶ 릴스 보기'}</button>`:''}<a class="pri" href="${esc(e.f)}/exhibit.html">전시 웹페이지</a><a href="viewer.html#${esc(e.f)}">연속 보기</a><a href="index.html#ep${e.ep}">갤러리</a><a href="https://projectmirador.org/embed/?iiif-content=${encodeURIComponent(man)}" target="_blank" rel="noopener">Mirador</a><a href="${esc(man)}" target="_blank" rel="noopener">IIIF manifest</a></div>
  ${d.t?`<h3>${curD+1}. ${esc(d.t)}${d.y?' ('+esc(d.y)+')':''}</h3>`:''}${d.sm?`<p>${esc(d.sm)}</p>`:''}${d.tr?`<h3>번역</h3><p>${esc(d.tr)}</p>`:''}${d.src?`<h3>원문</h3><p class="src">${esc(d.src)}</p>`:''}
  ${!VD?'<p style="color:#a99d86">원문 · 번역을 불러오는 중…</p>':''}
  <p class="note">판독 · 번역은 원본 이미지에 근거한 초안입니다(검토 전). 고문서 이미지: 한국학중앙연구원 한국고문서자료관 소장 · 제공 — 다시 쓰려면 자료관을 통한 소장처 동의가 필요하며, 문제가 있으면 내립니다. 엮은이: Song Chang-gi (chgsong@naver.com, github.com/changgi)</p>`;
  const rb=$('oReel');if(rb)rb.onclick=()=>renderOv(!reel)}
// ---------- 목록 ----------
function renderList(q){q=(q||'').trim().toLowerCase();$('lsL').innerHTML=ROOMS.map(r=>{const it=r.eps.filter(e=>!q||(`ep.${e.ep} ${e.t} ${e.c} ${e.k}`).toLowerCase().includes(q));
  return it.length?`<h4>${esc(r.name)} · ${it.length}편</h4>`+it.map(e=>`<button type="button" class="it" data-i="${e.i}"><b>EP.${e.ep}</b>${esc(e.t)}</button>`).join(''):''}).join('')||'<p style="color:#a99d86;padding:10px">찾는 편이 없습니다.</p>';
  $('lsL').querySelectorAll('.it').forEach(b=>b.onclick=()=>{const e=EPS[+b.dataset.i];$('ls').classList.remove('on');flyTo(standFor(e));history.replaceState(null,'','#ep'+e.ep)})}
$('bList').onclick=()=>{$('ls').classList.toggle('on');renderList($('q').value);if($('ls').classList.contains('on'))$('q').focus()};$('lsX').onclick=()=>$('ls').classList.remove('on');$('q').oninput=ev=>renderList(ev.target.value);
$('bHelp').onclick=()=>$('help').classList.add('on');$('hX').onclick=()=>{$('help').classList.remove('on');setSnd(false);playOn(curScreen||lobbyScr)};
// ---------- 시작 ----------
function fromHash(){const m=location.hash.match(/^#ep(\d+)$/);if(!m)return false;const e=EPS.find(x=>x.ep===+m[1]);if(!e)return false;const s=standFor(e);CAM.position.set(s.x,1.62,s.z);yaw=s.yaw;return true}
addEventListener('hashchange',()=>{const m=location.hash.match(/^#ep(\d+)$/);if(m){const e=EPS.find(x=>x.ep===+m[1]);if(e)flyTo(standFor(e))}});
const jumped=fromHash();updLoads();$('load').remove();let seen=false;try{seen=!!sessionStorage.getItem('museum-help');sessionStorage.setItem('museum-help','1')}catch(e){}if(!jumped&&!seen)$('help').classList.add('on');
window.__museum={room:i=>{const r=ROOMS[i];CAM.position.set(0,1.62,r.z0-ENT/2);yaw=Math.PI/2;pitch=0;tween=null},video:()=>({src:VID.dataset.src,paused:VID.paused,t:VID.currentTime,muted:VID.muted})};  // 점검용
loop();
</script></body></html>
'''
page = PAGE.replace('__DATA__', json.dumps(DATA, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')).replace('__NEPS__', str(NEPS))
old = open(R + 'museum.html', encoding='utf-8').read() if os.path.exists(R + 'museum.html') else ''
if old != page: open(R + 'museum.html', 'w', encoding='utf-8').write(page)
print(f'■ 가상 전시관: 방 {len(rooms)}개 · 편 {NEPS}개 · 문서 {NDOCS}건 · {len(page) / 1e3:.0f}KB · {"바뀜" if old != page else "그대로"} → examples/museum.html')
