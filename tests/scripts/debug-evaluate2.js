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

  // Test: 全局规则
  console.log('=== 全局规则 ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 方法1: 通过 _x_dataStack 访问 Alpine 数据
  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    if (el._x_dataStack) {
      const data = el._x_dataStack[0];
      console.log('Found Alpine data, keys:', Object.keys(data));
      data.showCreateModal = true;
      data.form.name = '测试规则';
      data.form.content = '测试内容';
    } else {
      console.log('No _x_dataStack');
    }
  });
  await pg.waitForTimeout(1000);

  // 提交
  console.log('Calling createRule via _x_dataStack...');
  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = el._x_dataStack[0];
    data.createRule();
  });
  await pg.waitForTimeout(3000);

  const result = await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = el._x_dataStack[0];
    return { modal: data.showCreateModal, count: data.rules?.length };
  });
  console.log('Result:', result);

  // Test 2: 我的技能
  console.log('\n=== 我的技能 ===');
  await pg.goto(`${BASE_URL}/skills/personal`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = el._x_dataStack[0];
    data.showCreateModal = true;
    data.form.name = '测试技能';
    data.form.description = '描述';
  });
  await pg.waitForTimeout(1000);

  console.log('Calling createSkill...');
  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = el._x_dataStack[0];
    data.createSkill();
  });
  await pg.waitForTimeout(3000);

  const result2 = await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    const data = el._x_dataStack[0];
    return { modal: data.showCreateModal, count: data.skills?.length };
  });
  console.log('Result:', result2);

  await browser.close();
})();
