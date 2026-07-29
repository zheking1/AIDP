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

  // Test 1: 全局规则 - page.click
  console.log('=== 全局规则 page.click ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 打开弹窗 - 用 page.click
  await pg.click('button:has-text("创建")');
  await pg.waitForTimeout(1500);

  // 填写
  await pg.fill('.fixed.inset-0 [x-model="form.name"]', `规则-${Date.now()}`);
  await pg.fill('.fixed.inset-0 [x-model="form.content"]', '测试内容');
  await pg.waitForTimeout(500);

  // 提交 - 用 page.click
  console.log('Clicking 创建 in modal...');
  await pg.click('.fixed.inset-0 button:has-text("创建")');
  await pg.waitForTimeout(3000);

  // Test 2: 我的技能 - page.click
  console.log('\n=== 我的技能 page.click ===');
  await pg.goto(`${BASE_URL}/skills/personal`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  await pg.click('button:has-text("创建技能")');
  await pg.waitForTimeout(1500);

  await pg.fill('.fixed.inset-0 [x-model="form.name"]', `技能-${Date.now()}`);
  await pg.fill('.fixed.inset-0 [x-model="form.description"]', '描述');
  await pg.waitForTimeout(500);

  console.log('Clicking 创建 in modal...');
  await pg.click('.fixed.inset-0 button:has-text("创建")');
  await pg.waitForTimeout(3000);

  await browser.close();
})();
