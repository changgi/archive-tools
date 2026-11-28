/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  // 함수 번들에 데이터 파일을 함께 싣는다(lib/core.js 가 process.cwd()/data 에서 읽는다 — 2.4MB JSON을 번들에 넣지 않는다)
  outputFileTracingIncludes: {
    '/api/**/*': ['./data/**/*'],
    '/': ['./data/**/*'],
  },
};
export default nextConfig;
