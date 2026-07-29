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

  // Test: 全局规则 - 用 JS evaluate 直接调用
  console.log('=== 全局规则 evaluate ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 打开弹窗
  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = Alpine.$data(el);
    data.showCreateModal = true;
    data.form.name = `规则-${Date.now()}`;
    data.form.content = '测试内容';
    console.log('Set form data');
  });
  await pg.waitForTimeout(1000);

  // 提交
  console.log('Calling createRule...');
  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = Alpine.$data(el);
    data.createRule();
  });
  await pg.waitForTimeout(3000);

  // 检查结果
  const result = await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = Alpine.$data(el);
    return { modal: data.showCreateModal, rulesCount: data.rules?.length };
  });
  console.log('Result:', result);

  // Test 2: 我的技能 - evaluate
  console.log('\n=== 我的技能 evaluate ===');
  await pg.goto(`${BASE_URL}/skills/personal`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = Alpine.$data(el);
    data.showCreateModal = true;
    data.form.name = `技能-${Date.now()}`;
    data.form.description = '描述';
  });
  await pg.waitForTimeout(1000);

  console.log('Calling createSkill...');
  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = Alpine.$data(el);
    data.createSkill();
  });
  await pg.waitForTimeout(3000);

  const result2 = await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = Alpine.$data(el);
    return { modal: data.showCreateModal, skillsCount: data.skills?.length };
  });
  console.log('Result:', result2);

  await browser.close();
})();
