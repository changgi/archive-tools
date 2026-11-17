// 예시 사이트 접근성 검사(axe-core, WCAG 2 A·AA + 권장 규칙) — 심각(critical · serious)이 있으면 실패
//   npm i --no-save playwright axe-core && npx playwright install chromium
//   node tools/check_a11y.js            # 주요 페이지 + 편별 전시 · 활동지 앞 3편
//   node tools/check_a11y.js --all      # 편별 전시 · 활동지 전부
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const AXE = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const R = path.join(__dirname, '..', 'examples');
const all = process.argv.includes('--all');
const hubs = fs.readdirSync(R).filter(f => f.endsWith('.html')).sort();
const tut = fs.readdirSync(path.join(R, 'tutorial', 'site')).filter(f => f.endsWith('.html')).sort().map(f => 'tutorial/site/' + f);
const eps = fs.readdirSync(R).filter(d => fs.existsSync(path.join(R, d, 'exhibit.html'))).sort();
const epPages = (all ? eps : eps.slice(0, 3)).flatMap(d => [d + '/exhibit.html', d + '/handout.html']);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  let bad = 0, warn = 0;
  for (const f of [...hubs, ...tut, ...epPages]) {
    await p.goto('file://' + path.join(R, f)); await p.waitForTimeout(200);
    await p.addScriptTag({ content: AXE });
    const v = await p.evaluate(async () => (await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'best-practice'] }))
      .violations.map(x => ({ id: x.id, imp: x.impact, n: x.nodes.length, ex: x.nodes[0].html.slice(0, 120) })));
    for (const x of v) {
      const hard = x.imp === 'critical' || x.imp === 'serious'; hard ? bad++ : warn++;
      console.log(`${hard ? '✗' : '·'} ${f}  ${x.imp} ${x.id} ×${x.n}  ${x.ex}`);
    }
  }
  await b.close();
  console.log(`페이지 ${hubs.length + tut.length + epPages.length}쪽 · 심각 ${bad} · 참고 ${warn}`);
  process.exit(bad ? 1 : 0);
})();
