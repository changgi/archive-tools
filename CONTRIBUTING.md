# 함께 고치기 · 기여하기

이 저장소의 판독 · 번역 · 해제는 **이미지에 근거한 초안**입니다. 완성품이 아니라 함께 고쳐 가는 기록입니다.

## 판독 · 번역이 틀린 곳을 봤다면

| 어디서 | 어떻게 |
|---|---|
| 갤러리 「원문 읽기」 · 전시 웹페이지 | 문서마다 있는 **「판독 고침 제보 ↗」** 를 누르면 문서명 · 자료 ID · 원본 링크가 채워진 이슈가 열립니다 |
| GitHub | [이슈 → 판독 고침 제보](../../issues/new/choose) 양식 |
| 메일 | chgsong@naver.com |

근거(원본 사진의 몇째 줄, 참고 자료)를 함께 적어 주시면 바로 확인합니다.

## 제보를 반영하는 방법(관리자)

```bash
S=plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts
python3 $S/studio.py fix --work W --theme T --issue 12 --repo changgi/archive-tools        # 제보 읽기
python3 $S/studio.py fix --work W --theme T --n 3 --field 번역 --replace-part "初八日" --text "初九日" --note "제보 #12 · 셋째 줄"   # 미리 보기
python3 $S/studio.py fix … --apply                                                          # 반영 → corrections.csv
python3 $S/studio.py mediate --work W --theme T --url <전시 주소> --issues https://github.com/changgi/archive-tools
```

원본 사진에서 그 줄을 확인한 뒤 반영합니다. 고친 기록(날짜 · 이전 · 이후 · 근거 · 제보)은 `corrections.csv`에 쌓이고 전시 웹페이지 「함께 고친 곳」에 나옵니다. 이슈에는 반영한 버전을 답글로 남기고 닫습니다.

## 도구(코드)를 고치려면

1. `python3 $S/selftest.py` — 인터넷 없이 전 과정 시험(영상까지: `--video`)
2. `python3 tools/check_links.py --all` — 예시 사이트 깨진 링크
   그리고 `python3 -m pyflakes plugins/aks-archive-harvester/skills/aks-archive-harvester/scripts tools` — 정의 안 된 이름 · 쓰지 않는 import
3. 바꾼 내용을 `CHANGELOG.md`에, 쓰는 법이 바뀌면 `SKILL.md` · README에. 버전은 세 곳(plugin.json · marketplace.json 두 곳)과 CHANGELOG 맨 위를 함께 — `python3 tools/check_version.py`
4. `python3 tools/build_dist.py` — 배포 파일(`dist/`)을 다시 만듦. 같은 소스면 같은 바이트가 나옵니다(`--check`로 확인)
5. 파이썬 3.10에서도 돌아야 합니다 — f-string 안에 같은 따옴표를 겹쳐 쓰거나 `\`를 넣지 않기(3.12부터만 됨)
6. 파일은 늘 UTF-8로 읽고 씁니다(`encoding='utf-8'`) — 한국어 Windows 기본 인코딩(cp949)에서도 돌아야 합니다
7. 한국고문서자료관 서버 동시 접속 수(기본값)를 올리지 않습니다

푸시하면 GitHub Actions가 Windows · macOS · Linux에서 selftest와 링크 · 버전 · dist 검사를 돌립니다(`.github/workflows/selftest.yml`).

## 릴리스

`v1.7.2`처럼 버전과 같은 태그를 올리면(`git tag v1.7.2 && git push origin v1.7.2`) `.github/workflows/release.yml`이 버전을 확인하고 배포 파일을 만들어, CHANGELOG의 그 버전 기록과 함께 GitHub 릴리스로 올립니다.

## 지켜 주세요

- 이미지 재사용 · 재배포는 소장처 동의가 필요합니다(한국고문서자료관 031-730-8873, 8876). 출처: "한국학중앙연구원 한국고문서자료관 소장·제공 · 소장처"
- 민감한 기록(기근 · 노비 · 자매 · 형벌)은 존엄을 먼저, 근대 명부의 실명 등 개인정보에 배려
- 추정은 추정이라고, 못 읽은 글자는 □, 불확실한 글자는 (?)로

코드는 MIT 라이선스(LICENSE)입니다. 판독 · 번역 텍스트의 재사용 조건은 따로 정할 예정입니다.
