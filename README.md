# archive-tools

기록·고문서 아카이브 조사와 수집을 위한 Claude 플러그인 모음입니다.

| 플러그인 | 하는 일 |
|---|---|
| [aks-archive-harvester](plugins/aks-archive-harvester) | 한국고문서자료관 고문서 ① 수집 ② 큐레이션 ③ 에디팅 ④ 매개(전시 웹페이지·카드뉴스·수업 활동지) ⑤ 연구 패키지·여러 문중 비교 연구 |

## 예시 보기

▶ **https://changgi.github.io/archive-tools/examples/** — 실제로 만든 전시 웹페이지·카드뉴스·수업 활동지·비교 리포트

| 혼인과 호적 (에디팅 후) | 송준길의 생애 (에디팅 전) | 땅과 관청 사이 (다른 소장처) |
|---|---|---|
| [![](examples/dongchundang-marriage/cards/00_표지.jpg)](examples/dongchundang-marriage/) | [![](examples/dongchundang-songjungil/cards/00_표지.jpg)](examples/dongchundang-songjungil/) | [![](examples/yuhoedang-land/cards/00_표지.jpg)](examples/yuhoedang-land/) |

명령을 하나씩 따라 하는 예제는 [`examples/README.md`](examples/README.md)에 있습니다.

🎬 **홍보 영상:** [EP.1 흩어진 기록을, 다시 이야기로(83초)](https://changgi.github.io/archive-tools/examples/media/promo-reel.mp4) · [EP.2 만든 것 보기(48초)](https://changgi.github.io/archive-tools/examples/media/promo-reel-ep2.mp4) · 이미지 출처: 한국학중앙연구원 한국고문서자료관(이미지 재사용은 자료관 문의, 소장처 동의 필요)

## 설치

### Claude Code / Cowork (권장, 업데이트 자동 반영)

```
/plugin marketplace add changgi/archive-tools
/plugin install aks-archive-harvester@changgi-archive-tools
```

새 버전이 나오면:

```
/plugin marketplace update changgi-archive-tools
```

### 파일로 설치

[Releases](../../releases) 또는 `dist/`에서 받으세요.

- `aks-archive-harvester.plugin`: Claude Cowork에 올려 설치
- `aks-archive-harvester-skill.zip`: claude.ai 스킬 설정에서 업로드

### 파이썬만 쓰기

```bash
pip install requests pillow
python3 plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/harvest.py --help
python3 plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts/studio.py --help
```

## 사용 예

> 한국고문서자료관에서 동춘당 송준길 후손가 문서 전부 받아줘
>
> 혼인과 호적 테마로 전시 웹페이지랑 카드뉴스 만들어줘
>
> 충청도 문중들을 비교 연구할 수 있게 패키지로 묶어줘

## 이용 시 유의

- 공공 연구기관 서버입니다. 기본 동시 요청 수(타일 16개, 페이지 2장)를 올리지 마세요.
- 수집한 이미지의 이용·재배포는 한국고문서자료관 이용 조건을 따르세요. 대량 이용은 기관(031-779-2791)에 원본 제공을 요청하는 것이 확실합니다.
- 이 도구는 한국학중앙연구원과 관계없는 개인 제작물입니다.

## 만든 사람

Song Chang-gi · chgsong@naver.com · https://github.com/changgi
