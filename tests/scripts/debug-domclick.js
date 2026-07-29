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

  // 方法: 用 evaluate 直接 DOM click
  console.log('=== 全局规则 DOM click ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 打开弹窗
  await pg.evaluate(() => {
    const btns = document.querySelectorAll('button');
    for (const b of btns) {
      const oc = b.getAttribute('@click');
      if (oc === 'showCreateModal = true') { b.click(); break; }
    }
  });
  await pg.waitForTimeout(1500);

  // 填写
  await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    // Alpine v3 stores data on _x_dataStack
    const stack = el._x_dataStack;
    console.log('Stack:', stack);
    if (stack && stack[0]) {
      stack[0].form.name = '测试规则-' + Date.now();
      stack[0].form.content = '测试内容';
    }
  });
  await pg.waitForTimeout(500);

  // 提交
  console.log('Clicking createRule via DOM...');
  await pg.evaluate(() => {
    const btns = document.querySelectorAll('button');
    for (const b of btns) {
      const oc = b.getAttribute('@click');
      if (oc === 'createRule()') { b.click(); break; }
    }
  });
  await pg.waitForTimeout(3000);

  // 检查弹窗状态
  const isOpen = await pg.evaluate(() => {
    const modals = document.querySelectorAll('.fixed.inset-0');
    for (const m of modals) {
      const style = window.getComputedStyle(m);
      if (style.display !== 'none' && m.offsetParent !== null) return true;
    }
    return false;
  });
  console.log('Modal still open:', isOpen);

  await browser.close();
})();
