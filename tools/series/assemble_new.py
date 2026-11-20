import _paths as P  # 저장소 · 작업 폴더 위치(환경 변수로 바꿀 수 있음) — tools/series/_paths.py
import os, csv, json, re, subprocess, sys, glob
E=(P.REPO + '/examples'); S=P.DATA
only=sys.argv[1:]
for jp in sorted(glob.glob(S+'/new/*.json'))+sorted(glob.glob(S+'/new2/*.json'))+sorted(glob.glob(S+'/new3/*.json'))+sorted(glob.glob(S+'/new4/*.json')):
    J=json.load(open(jp,encoding='utf-8')); M=J['meta']; ep=M['id']; f=M['folder']; d=os.path.join(E,f)
    if only and ep not in only: continue
    if not os.path.exists(f'{S}/out/{ep}_wide.mp4'): continue
    big=M['ep']>50  # EP.51+는 540p·CRF34·64k (Pages 1GB 한도)
    for mode,sc in ([('reel','540:960'),('wide','960:540')] if big else [('reel','720:1280'),('wide','1280:720')]):
        src=f'{S}/out/{ep}_{mode}.mp4'; dst=os.path.join(E,'media',f'{ep}_{mode}.mp4')
        if os.path.exists(dst) and os.path.getmtime(dst)>os.path.getmtime(src): continue
        subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-vf',f'scale={sc}','-c:v','libx264','-preset','slow','-crf','34' if big else '28','-tune','stillimage','-c:a','aac','-b:a','64k' if big else '96k','-movflags','+faststart',dst+'.tmp.mp4'],check=True); os.replace(dst+'.tmp.mp4',dst)
    srt=open(f'{S}/out/{ep}.ko.srt',encoding='utf-8').read()
    open(os.path.join(E,'media',f'{ep}.ko.srt'),'w',encoding='utf-8').write(srt)
    open(os.path.join(E,'media',f'{ep}.ko.vtt'),'w',encoding='utf-8').write('WEBVTT\n\n'+re.sub(r'(\d\d:\d\d:\d\d),(\d\d\d)',r'\1.\2',srt))
    subprocess.run(['ffmpeg','-v','error','-y','-ss','1.5','-i',f'{S}/out/{ep}_reel.mp4','-frames:v','1','-vf','scale=540:960','-q:v','4',os.path.join(E,'media',f'{ep}_reel-poster.jpg')],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-ss','2.5','-i',f'{S}/out/{ep}_wide.mp4','-frames:v','1','-vf','scale=960:-2','-q:v','4',os.path.join(E,'media',f'{ep}_wide-poster.jpg')],check=True)
    sel=list(csv.DictReader(open(os.path.join(d,'selection.csv'),encoding='utf-8-sig')))
    story='\n'.join(f"> **{s['연도'] or ''} {s['문서유형']}** — {s['이야기']}" for s in sel)
    rows='\n'.join(f"| {s['순서']} | {s['연도'] or '—'} | {s['문서유형']} | {s['문서명']} | [원본 보기]({s['뷰어링크']}) |" for s in sel)
    base=f'https://changgi.github.io/archive-tools/examples/{f}/'; vb=f'https://changgi.github.io/archive-tools/examples/media/{ep}'
    full='\n\n'.join(f"### {s['순서']}. {s['문서명']}\n\n**원문 판독**\n\n```\n{s['원문'].strip()}\n```\n\n**원문 해석** {s['번역']}\n\n**해제** {s['해제']}" for s in sel)
    open(os.path.join(d,'README.md'),'w',encoding='utf-8').write(f"""# EP.{M['ep']} {M['title']}

{M['coll']} ({M['kind']}) · {M['lead']}

- 🌐 [전시 웹페이지]({base}exhibit.html) (한자 위 한글 독음 · 원문 해석) · [수업 활동지]({base}handout.html)
- 🎬 영상: [릴스 9:16]({vb}_reel.mp4) · [가로 16:9]({vb}_wide.mp4) · 홍보 글: [`promo.md`](promo.md)
- 카드뉴스: [`cards/`](cards/) · SNS 글: [`sns.txt`](sns.txt) · 판독·해석 표: [`selection.csv`](selection.csv)

## 이야기 — 사료가 말하는 대로

{J['hook']}

{story}

| 표지 | 1번 카드 | 마무리 |
|---|---|---|
| ![](cards/00_표지.jpg) | ![](cards/01.jpg) | ![](cards/99_마무리.jpg) |

## 선별 문서 ({len(sel)}점)

| # | 연도 | 유형 | 문서명 | 원본 |
|---|---|---|---|---|
{rows}

## 원문 판독과 해석

{full}

판독·해석·이야기는 이미지에 근거한 초안이며(검토 전 "초안" 표시), 정확한 판독은 원문 확인이 필요합니다. □는 읽지 못한 글자, (?)는 불확실한 글자입니다.
이미지: 한국학중앙연구원 한국고문서자료관 소장·제공. "원본" 링크를 누르면 자료관 뷰어에서 그 문서가 열립니다. 재사용은 자료관에 문의하세요(소장처 동의 필요).
""")
    print('assembled',ep)
