# 워크플로 두 개 — `.github/workflows/`에 두는 파일

이 폴더의 파일은 GitHub Actions 워크플로입니다. 저장소의 `.github/workflows/`에 있어야 동작합니다.

```
mcp-verify.yml      → .github/workflows/mcp-verify.yml      (mcp/** CI: 데이터 재생성 대조 · 정적 검증 · 빌드 · 엔드포인트 실측)
deploy-prebuilt.yml → .github/workflows/deploy-prebuilt.yml (main push 시 GitHub 러너 빌드 → Vercel prebuilt 배포)
```

## 왜 이 폴더에 있나

Pickle의 GitHub 연결에 **워크플로 파일 쓰기(`workflows`) 권한이 없어** 자동 커밋이
`.github/workflows/*` 를 만들 수 없습니다(`refusing to allow a GitHub App to create or update workflow … without workflows permission`).
권한을 켜지 않고도 코드·데이터·문서는 그대로 커밋되도록, 워크플로만 여기에 두었습니다.

## 옮기는 법 (둘 중 하나)

1. **GitHub 웹 화면에서** — `.github/workflows/` 폴더에서 *Add file → Create new file* 로 위 이름의 파일을 만들고
   이 폴더의 내용을 붙여넣습니다.
2. **Pickle GitHub 연결에 `workflows` 권한을 준 뒤** —
   ```bash
   git mv mcp/ci/mcp-verify.yml .github/workflows/mcp-verify.yml
   git mv mcp/ci/deploy-prebuilt.yml .github/workflows/deploy-prebuilt.yml
   git commit -m "ci(mcp): 워크플로를 .github/workflows 로 옮김" && git push
   ```

배포 워크플로가 돌려면 저장소 secret **`VERCEL_TOKEN`** 하나가 필요합니다
(Settings → Secrets and variables → Actions). 값은 로그·파일에 남기지 않습니다.
