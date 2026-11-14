# aks-archive-harvester

한국학중앙연구원 **한국고문서자료관**(archive.aks.ac.kr)에서 소장처(문중·후손가)나 분류 아래의 모든 문서 이미지를 원본 해상도로 받아 정리하는 Cowork 플러그인입니다.

## 할 수 있는 일

- 분류 트리를 끝까지 따라 내려가 문서와 페이지 목록 만들기
- 확대용 DZI 타일을 받아 원본 크기 JPG로 이어붙이기 (이어받기 지원)
- 서버에 없는 장, 저해상도로 대체한 장 기록
- 문서목록 CSV 만들기, 분류별 ZIP으로 묶기 (350MB 단위 분할)

## 사용 예

> "한국고문서자료관에서 대전 회덕 은진송씨 동춘당 송준길 후손가 하위 문서 전부 받아줘"

## 직접 실행 (터미널)

```bash
pip install requests pillow
S=skills/aks-archive-harvester/scripts/harvest.py
python3 $S manifest --work W --data-url '?itemId=book&gubun=booktree&depth=3&upPath=01%5E0130&dataId=L013001&itemType='
python3 $S download --work W --time 540      # STATUS: DONE이 나올 때까지 반복
python3 $S report   --work W --out 목록.csv
python3 $S pack     --work W --dest zips --prefix 동춘당 --max-mb 350
```

## 이용 시 유의

- 공공 연구기관 사이트이므로 기본 동시 요청 수(타일 16개, 페이지 2장)를 올리지 마세요.
- 수집한 이미지의 이용 조건은 한국고문서자료관 이용 안내를 따르세요. 대량 이용이나 재배포가 목적이면 기관(031-779-2791)에 원본 제공을 요청하는 편이 확실합니다.

제작: Song Chang-gi · chgsong@naver.com · https://github.com/changgi
