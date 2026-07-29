const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';

async function login(pg) { await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' }); await pg.fill('input[name="username"]', 'admin'); await pg.fill('input[name="password"]', 'admin123'); await pg.click('button[type="submit"]'); await pg.waitForTimeout(2000); }

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  await login(pg);

  // Log ALL network
  pg.on('response', async resp => {
    const url = resp.url();
    if (url.includes('/api/') && !url.includes('stats') && !url.includes('list') && !url.includes('templates')) {
      console.log(`[API] ${resp.request().method()} ${url.split('?')[0]} → ${resp.status()}`);
      try { const t = await resp.text(); if (t.length < 500) console.log(`  → ${t}`); } catch (e) {}
    }
  });
  pg.on('requestfailed', req => console.log(`[FAIL] ${req.url()} → ${req.failure()?.errorText}`));

  // Test: 我的技能创建
  console.log('=== 我的技能创建 ===');
  await pg.goto(`${BASE_URL}/skills/personal`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 打开弹窗
  const btn = await pg.$('button:has-text("创建技能")');
  await btn.dispatchEvent('click');
  await pg.waitForTimeout(1500);

  // 填写
  await pg.fill('.fixed.inset-0 [x-model="form.name"]', `测试技能-${Date.now()}`);
  await pg.fill('.fixed.inset-0 [x-model="form.description"]', '描述');
  await pg.waitForTimeout(500);

  // 提交
  const btns = await pg.$$('.fixed.inset-0 button');
  for (const b of btns) {
    const oc = await b.evaluate(el => el.getAttribute('@click') || '');
    const vis = await b.isVisible().catch(() => false);
    if (vis && oc.includes('createSkill')) {
      console.log('Clicking createSkill...');
      await b.dispatchEvent('click');
      break;
    }
  }

  await pg.waitForTimeout(5000);
  console.log('Done waiting');

  await browser.close();
})();
