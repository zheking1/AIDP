const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 200 });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];

  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      errors.push({ type: msg.type(), text: msg.text().substring(0, 150) });
    }
  });
  page.on('pageerror', e => errors.push({ type: 'pageerror', text: e.message.substring(0, 150) }));

  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // 点击每个菜单并记录控制台
  const menus = ['知识中心', '技能库', '记忆中心', '代码沙箱', '质量检查'];
  for (const menu of menus) {
    errors.length = 0;
    const btns = await page.$$('button');
    for (const b of btns) {
      const t = await b.textContent().catch(() => '');
      if (t.includes(menu)) { await b.click(); break; }
    }
    await page.waitForTimeout(3000);
    console.log(`\n=== ${menu} ===`);
    if (errors.length === 0) {
      console.log('  ✅ 无控制台错误');
    } else {
      errors.forEach(e => console.log(`  ${e.type === 'error' ? '❌' : '⚠️'} ${e.text}`));
    }
  }

  await browser.close();
})();