export const metadata = {
  title: 'archive-tools MCP — 한국 기록·고문서 조사 커넥터',
  description:
    '「고문서 한 장」 200편 · 726건의 판독·번역·해제·이야기와 한국고문서자료관(archive.aks.ac.kr) 실시간 탐색을 MCP 도구로 여는 원격 서버.',
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body style={{ margin: 0, fontFamily: 'system-ui, -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif', color: '#1a1a1a', background: '#fbfaf7' }}>
        {children}
      </body>
    </html>
  );
}
