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

  console.log('=== 全局规则 - force click ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 打开弹窗
  await pg.locator('button', { hasText: '创建' }).first().click();
  await pg.waitForTimeout(1500);

  // 填写
  await pg.locator('.fixed.inset-0 input[x-model="form.name"]').fill(`规则-${Date.now()}`);
  await pg.locator('.fixed.inset-0 textarea[x-model="form.content"]').fill('测试内容');
  await pg.waitForTimeout(500);

  // 提交 - force click on the createRule button
  console.log('Force clicking createRule...');
  await pg.locator('button:has-text("创建")').last().click({ force: true });
  await pg.waitForTimeout(3000);

  const isOpen = await pg.evaluate(() => {
    const modals = document.querySelectorAll('.fixed.inset-0');
    for (const m of modals) { if (m.offsetParent !== null) return true; }
    return false;
  });
  console.log('Modal still open:', isOpen);

  // 验证数据
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(2000);
  const text = await pg.textContent('body');
  console.log('Rules visible:', text.includes('规则-'));

  await browser.close();
})();
