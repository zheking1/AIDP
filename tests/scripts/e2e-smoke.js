const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const BASE = 'http://192.168.0.100:8883';
const R = path.join(__dirname, '..', 'reports');
const S = path.join(__dirname, '..', 'screenshots');
const results = [];
let browser, page;

function ok(n, s, d = '') { console.log(`  ${s==='PASS'?'✅':'❌'} ${n}: ${d}`); results.push({ n, s, d }); }

async function smoke(url, name) {
  let jsErrors = [];
  const onError = e => { jsErrors.push(e.message); };
  page.on('pageerror', onError);
  await page.goto(`${BASE}${url}`, { waitUntil: 'networkidle', timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2000);
  const text = await page.textContent('body').catch(() => '');
  const has500 = text.includes('Internal Server Error');
  ok(`${name}`, text.length > 200 && !has500 ? 'PASS' : 'FAIL', has500 ? '500错误' : `${text.length}b`);
  if (jsErrors.length) ok(`${name} JS`, 'FAIL', jsErrors[0].slice(0, 80));
  page.removeListener('pageerror', onError);
}

const PAGES = [
  '/hub/knowledge', '/hub/skills', '/hub/memory',
  '/knowledge/bases', '/knowledge/documents', '/knowledge/search', '/knowledge/templates',
  '/skills/global', '/skills/personal', '/rules/global', '/rules/personal',
  '/agents', '/workflows',
  '/memory/memories', '/memory/graph', '/memory/search',
  '/assets', '/sandbox', '/quality',
  '/admin/projects', '/admin/skills', '/admin/rules',
];

(async () => {
  console.log('=== AIDP E2E 冒烟测试 ===');
  browser = await chromium.launch({ headless: false, slowMo: 200 });
  page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  console.log(`\n测试 ${PAGES.length} 个页面...`);
  for (const url of PAGES) {
    await smoke(url, url.replace(/^\//, '').replace(/\//g, ' ').trim() || 'home');
  }

  const passed = results.filter(r => r.s === 'PASS').length;
  const failed = results.filter(r => r.s === 'FAIL').length;
  console.log(`\n${'='.repeat(50)}`);
  console.log(`  结果: ${results.length}项 | ✅${passed} ❌${failed} | ${(passed/results.length*100).toFixed(1)}%`);
  if (failed) {
    console.log(`\n失败:`);
    results.filter(r => r.s === 'FAIL').forEach(r => console.log(`  ❌ ${r.n}: ${r.d}`));
  }
  fs.mkdirSync(R, { recursive: true });
  fs.writeFileSync(path.join(R, 'e2e-smoke.json'), JSON.stringify(results, null, 2));

  await browser.close();
})();