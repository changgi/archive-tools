import { DATA, DATASET_SHA256, CATALOG_COLLECTIONS } from '../lib/core.js';

const TOOLS = [
  ['curation_search', '「고문서 한 장」 200편 · 726건에서 낱말 · 인물 · 유형 · 연도로 찾기'],
  ['curation_item', '문서 한 건의 판독 · 원문 · 번역 · 해제 · 이야기 + 전시 · 활동지 · 카드뉴스 · IIIF 링크'],
  ['curation_episode', '한 편(회차)의 기획 의도 · 큐레이터 노트 · 문서 목록 · 산출물'],
  ['curation_people', '인물 258명 찾아보기'],
  ['curation_timeline', '726건 연표 — 1403~2000년'],
  ['curation_quotes', '종이에 적힌 문장 763곳 — 현대어(原文) 쌍'],
  ['doc_type', '문서 유형 사전 — 고신 · 홍패 · 준호구 · 명문 …'],
  ['curation_stats', '규모 · 분포 · 데이터 지문'],
  ['aks_catalog', '한국고문서자료관 소장처 173곳'],
  ['aks_find', '소장처 이름으로 찾기'],
  ['aks_manifest', '소장처 안의 문서 목록 실시간 읽기'],
  ['health', '서버 · 데이터 상태'],
];

export default function Page() {
  const C = DATA.counts;
  return (
    <main style={{ maxWidth: 860, margin: '0 auto', padding: '48px 22px 80px', lineHeight: 1.65 }}>
      <p style={{ letterSpacing: '.18em', fontSize: 12, color: '#8a6a2f', margin: 0 }}>ARCHIVE TOOLS · MCP</p>
      <h1 style={{ fontSize: 30, margin: '10px 0 6px', lineHeight: 1.25 }}>한국 기록·고문서 조사 커넥터</h1>
      <p style={{ color: '#555', marginTop: 0 }}>
        AI 비서에 주소 하나를 붙이면, 조선시대 고문서의 <strong>판독 · 번역 · 해제</strong>와
        한국고문서자료관 원본 탐색을 도구로 쓸 수 있습니다.
      </p>

      <h2 style={{ fontSize: 19, marginTop: 34 }}>연결 주소</h2>
      <pre style={{ background: '#fff', border: '1px solid #e6e1d6', borderRadius: 8, padding: '12px 14px', overflowX: 'auto' }}>https://archive-tools-mcp.vercel.app/api/mcp</pre>
      <p style={{ color: '#555', fontSize: 14 }}>Streamable HTTP · stateless · 프로토콜 2025-06-18 · 도구 12종(전부 읽기 전용)</p>

      <h2 style={{ fontSize: 19, marginTop: 34 }}>무엇을 할 수 있나</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
        <tbody>
          {TOOLS.map(([name, what]) => (
            <tr key={name}>
              <td style={{ borderTop: '1px solid #ece7dc', padding: '8px 10px 8px 0', whiteSpace: 'nowrap', fontFamily: 'ui-monospace, Menlo, monospace' }}>{name}</td>
              <td style={{ borderTop: '1px solid #ece7dc', padding: '8px 0', color: '#333' }}>{what}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ fontSize: 19, marginTop: 34 }}>데이터</h2>
      <ul style={{ paddingLeft: 20, color: '#333', fontSize: 15 }}>
        <li>「고문서 한 장」 — 편 {C.episodes} · 문서 {C.docs}건 · 소장처 {C.collections}곳 · {C.span[0]}–{C.span[1]}년 · 판독 한자 {C.hanja.toLocaleString('en-US')}자</li>
        <li>원문 인용 {C.quotes_series}곳 · 인물 {C.people}명 · 문서 유형 {C.types}개</li>
        <li>한국고문서자료관 소장처 {CATALOG_COLLECTIONS.length}곳(실시간 조회)</li>
      </ul>
      <p style={{ color: '#555', fontSize: 14 }}>
        출처: 한국학중앙연구원 한국고문서자료관(archive.aks.ac.kr) · 갤러리{' '}
        <a href={DATA.source.gallery} style={{ color: '#8a6a2f' }}>changgi.github.io/archive-tools/examples</a> ·{' '}
        <a href={DATA.source.repo} style={{ color: '#8a6a2f' }}>저장소</a>
      </p>
      <p style={{ color: '#777', fontSize: 13 }}>
        텍스트 CC BY 4.0 · 코드 MIT · 고문서 이미지는 소장처 동의 필요 · 데이터 지문 sha256 {DATASET_SHA256.slice(0, 16)}…
      </p>
    </main>
  );
}
