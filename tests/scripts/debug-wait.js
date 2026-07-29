const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';

async function login(pg) { await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' }); await pg.fill('input[name="username"]', 'admin'); await pg.fill('input[name="password"]', 'admin123'); await pg.click('button[type="submit"]'); await pg.waitForTimeout(2000); }

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  await login(pg);

  pg.on('response', async resp => {
    if (resp.url().includes('/api/') && !resp.url().includes('stats') && !resp.url().includes('list') && !resp.url().includes('templates')) {
      console.log(`[API] ${resp.request().method()} ${resp.url().split('?')[0]} → ${resp.status()}`);
      try { const t = await resp.text(); if (t.length < 300) console.log(`  → ${t}`); } catch (e) {}
    }
  });

  console.log('=== 全局规则 - 等待 Alpine 加载 ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(8000); // 长时间等待 CDN 加载

  // 检查 Alpine
  const status = await pg.evaluate(() => ({
    hasAlpine: typeof Alpine !== 'undefined',
    hasXDataStack: !!document.querySelector('[x-data]')?._x_dataStack,
  }));
  console.log('After 8s wait:', status);

  if (status.hasAlpine) {
    // Alpine 已加载，尝试操作
    await pg.evaluate(() => {
      const el = document.querySelector('[x-data]');
      const data = Alpine.$data(el);
      data.showCreateModal = true;
      data.form.name = '测试规则';
      data.form.content = '测试内容';
    });
    await pg.waitForTimeout(1000);

    await pg.evaluate(() => {
      const el = document.querySelector('[x-data]');
      const data = Alpine.$data(el);
      data.createRule();
    });
    await pg.waitForTimeout(3000);

    const result = await pg.evaluate(() => {
      const el = document.querySelector('[x-data]');
      const data = Alpine.$data(el);
      return { modal: data.showCreateModal, count: data.rules?.length };
    });
    console.log('Result:', result);
  } else {
    console.log('Alpine still not loaded after 8s');
  }

  await browser.close();
})();
