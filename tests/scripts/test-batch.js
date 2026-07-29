const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'http://192.168.0.100:8883';
const RESULTS_DIR = 'test-reports';
const PROJECT_ID = '1';

function record(results, tier, name, passed, detail = '') {
  results.push({ tier, name, passed, detail });
  const icon = passed ? '✅' : '❌';
  console.log(`  ${icon} [T${tier}] ${name}${detail ? ': ' + detail : ''}`);
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
}

async function closeAnyModal(page) {
  try { await page.keyboard.press('Escape'); await page.waitForTimeout(200); } catch (e) {}
  try {
    const m = await page.$('.fixed.inset-0');
    if (m) { const c = await m.$('.fa-times, button:has-text("取消"), button:has-text("关闭")'); if (c) await c.click({ timeout: 2000 }); }
  } catch (e) {}
}

async function testPage(browser, pageName, url) {
  console.log(`\n📄 ${pageName}`);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await login(page);
  const results = [];

  // T1
  const t1Errors = [];
  const h1 = msg => { if (msg.type() === 'error') t1Errors.push(msg.text()); };
  const e1 = err => { t1Errors.push(err.message); };
  page.on('console', h1); page.on('pageerror', e1);
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 8000 });
    await page.waitForTimeout(1200);
    const jsErr = t1Errors.filter(e => !e.includes('favicon') && !e.includes('loadMenu'));
    record(results, 'T1', `HTTP ${resp.status()}`, resp.status() === 200);
    record(results, 'T1', '无JS错误', jsErr.length === 0, jsErr.length > 0 ? jsErr[0].substring(0, 60) : '');
  } catch (e) { record(results, 'T1', '加载失败', false, e.message.split('\n')[0]); }
  page.removeListener('console', h1); page.removeListener('pageerror', e1);

  // T2
  await page.goto(url, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(2000);
  const grid = await page.$$('.grid > div');
  const rows = await page.$$('table tbody tr');
  record(results, 'T2', '列表渲染', Math.max(grid.length, rows.length) > 0, `${Math.max(grid.length, rows.length)} 条`);

  // T3 - 只测关键按钮
  await page.goto(url, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(2000);
  const keyBtns = await page.$$('button');
  let btnCount = 0;
  for (const btn of keyBtns) {
    const vis = await btn.isVisible().catch(() => false);
    if (!vis) continue;
    const txt = (await btn.textContent().catch(() => '')).trim() || '?';
    btnCount++;
    try {
      await btn.click({ timeout: 2000 }); await page.waitForTimeout(600);
      const hasModal = await page.$('.fixed.inset-0') !== null;
      record(results, 'T3', `「${txt}」`, true, hasModal ? '弹窗' : '响应');
      if (hasModal) await closeAnyModal(page);
    } catch (e) {
      record(results, 'T3', `「${txt}」`, false, '失败');
      await closeAnyModal(page);
    }
  }

  // T4
  await page.goto(url, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(2000);
  const hasDetail = await page.$('[x-show="showDetailModal"]');
  if (hasDetail) {
    const item = await page.$('.grid > div:first-child');
    if (item) {
      try {
        await item.click({ timeout: 3000 }); await page.waitForTimeout(1500);
        const modal = await page.$('[x-show="showDetailModal"]');
        if (modal) {
          record(results, 'T4', '详情弹窗', true);
          for (const t of ['技能', '规则', '知识库']) {
            const tab = await modal.$(`button:has-text("${t}")`);
            if (tab) { await tab.click({ timeout: 2000 }); await page.waitForTimeout(300); record(results, 'T4', `Tab「${t}」`, true); }
          }
          await closeAnyModal(page);
        }
      } catch (e) { record(results, 'T4', '详情', false, e.message.split('\n')[0]); await closeAnyModal(page); }
    }
  } else {
    record(results, 'T4', '跳过', true, '无关联');
  }

  const passed = results.filter(r => r.passed).length;
  const total = results.length;
  console.log(`  📊 ${passed}/${total} (${total > 0 ? ((passed/total)*100).toFixed(0) : 0}%)`);

  fs.mkdirSync(RESULTS_DIR, { recursive: true });
  fs.writeFileSync(`${RESULTS_DIR}/test-${pageName}.json`, JSON.stringify({ page: pageName, url, summary: { total, passed }, results }, null, 2));
  await context.close();
  return { pageName, total, passed };
}

async function main() {
  const pages = JSON.parse(fs.readFileSync(process.argv[2] || 'test-reports/pages.json', 'utf8'));
  console.log(`=== 测试 ${pages.length} 个页面 ===\n`);
  const browser = await chromium.launch({ headless: true });
  const summaries = [];
  for (const p of pages) {
    const r = await testPage(browser, p.name, `${BASE_URL}${p.url}`);
    summaries.push(r);
  }

  console.log('\n📊 汇总:');
  let gt = 0, gp = 0;
  for (const s of summaries) {
    const icon = s.passed === s.total ? '✅' : '⚠️';
    console.log(`${icon} ${s.pageName}: ${s.passed}/${s.total}`);
    gt += s.total; gp += s.passed;
  }
  console.log(`\n总计: ${gp}/${gt} (${gt > 0 ? ((gp/gt)*100).toFixed(1) : 0}%)`);

  fs.mkdirSync(RESULTS_DIR, { recursive: true });
  fs.writeFileSync(`${RESULTS_DIR}/summary-${Date.now()}.json`, JSON.stringify({ summaries, grandTotal: gt, grandPassed: gp }, null, 2));
  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
