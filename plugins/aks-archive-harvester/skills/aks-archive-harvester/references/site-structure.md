# archive.aks.ac.kr 뷰어 구조 (2026-11 확인)

## 1. 분류 트리 — `treeAjax.do`

- 뷰어 왼쪽 트리는 jQuery simpleTree. 접힌 폴더 안에 `<ul class="ajax"><li>{url:./treeAjax.do?...}</li></ul>`만 있고 펼칠 때 불러온다(지연 로딩).
- 노드의 `data-url`을 그대로 붙이면 그 노드의 하위 목록이 HTML 조각으로 온다.

```
GET /viewer/treeAjax.do?itemId=book&gubun=booktree&depth=3&upPath=01%5E0130&dataId=L013001&itemType=
→ <li data-dataId='L013001F02'  data-url ='?itemId=...&depth=4&upPath=01%5E0130%5EL013001&dataId=L013001F02&itemType=' ><span title='고문서'>고문서</span> ...
```

- `upPath`: 상위 ID들을 `^`(%5E)로 이은 경로. `depth`: 트리 깊이.
- 문서 노드: `data-dataId`가 `G002+AKS+...`로 시작, `<span class='nochild' title='...'>`.
- 폴더 노드: `L…` / `L…F02` / `L…F0201` 형식.

예: 대전 회덕 은진송씨 동춘당 송준길 후손가 = `L013001` (upPath `01^0130`)
- 고문서 `L013001F02` → 교령류 F0201, 소차계장류 F0202, 첩관통보류 F0203, 증빙류 F0204, 서간통고류 F0206, 치부기록류 F0207, 시문류 F0208

## 2. 페이지 목록 — `imgnode.do` (JSON)

```
GET /viewer/imgnode.do?itemId=book&gubun=booktree&depth=6&upPath=...&dataId=G002%2BAKS%2B...&itemType=
→ {"infoTitle": "...", "dataUCI": "...", "imgItems": [{"dzi": "/dzi/<계열>/<UCI>/<UCI>-IMG.001.xml", "filename": "...-IMG.001.jpg", "thumb": ".../_files/8/0_0.jpg"}, ...]}
```

## 3. 이미지 — DZI (Deep Zoom)

```xml
<Image TileSize="256" Overlap="1" Format="jpg"><Size Width="3887" Height="3363"/></Image>
```

- 타일 주소: `<xml에서 .xml 제거>_files/<레벨>/<열>_<행>.jpg`
- 원본 레벨 `L = ceil(log2(max(W,H)))`. 레벨이 하나 내려갈 때마다 가로·세로 1/2.
- 열 수 = ceil(W/256), 행 수 = ceil(H/256).
- 붙이는 위치: x = 열×256 − (열>0 ? 1 : 0), y도 같은 방식 (Overlap 1픽셀 보정).
- 일부 페이지는 최고 레벨 타일이 생성돼 있지 않음 → 아래 레벨로 대체.

## 4. 요청 헤더

- `User-Agent`(일반 브라우저), `Referer: https://archive.aks.ac.kr/viewer/viewer.do`만 보낸다.
- `X-Requested-With: XMLHttpRequest`를 보내면 `WEBFIREWALL BLOCK!!!` 응답(문의 031-779-2791).
