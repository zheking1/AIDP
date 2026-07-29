const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  
  let consoleErrors = [];

  page.on('pageerror', e => consoleErrors.push(e.message.substring(0, 120)));
  page.on('response', r => { if (r.status() >= 400) consoleErrors.push(`HTTP ${r.status()}: ${r.url().substring(0,80)}`) });

  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  const click = async (text) => {
    const btns = await page.$$('button');
    for (const b of btns) {
      if ((await b.textContent().catch(()=>'')).includes(text)) { await b.click(); break; }
    }
    await page.waitForTimeout(2000);
  };

  await click('用户管理');
  await click('系统设置');

  const detail = await page.evaluate(() => {
    const tabs = document.querySelectorAll('[id^="tab-content-admin"]');
    return Array.from(tabs).map(el => ({
      id: el.id,
      html: el.innerHTML.substring(0, 200),
      childCount: el.children.length
    }));
  });
  
  console.log('Errors:', consoleErrors);
  console.log('Tabs:', JSON.stringify(detail, null, 2));
  
  await browser.close();
})();