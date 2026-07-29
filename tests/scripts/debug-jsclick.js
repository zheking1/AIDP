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

  console.log('=== 全局规则 ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 打开弹窗 - 找 showCreateModal = true 的按钮并用 JS click
  await pg.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.getAttribute('@click') === 'showCreateModal = true') b.click();
    });
  });
  await pg.waitForTimeout(1500);

  // 填写 - 通过 input 事件
  const ts = Date.now();
  await pg.evaluate((ts) => {
    document.querySelectorAll('.fixed.inset-0 input, .fixed.inset-0 textarea').forEach(inp => {
      const model = inp.getAttribute('x-model');
      if (model === 'form.name') {
        inp.value = '规则-' + ts;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }
      if (model === 'form.content') {
        inp.value = '测试内容';
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
  }, ts);
  await pg.waitForTimeout(500);

  // 提交 - 找 createRule 按钮并用 JS click
  console.log('JS click on createRule button...');
  await pg.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.getAttribute('@click') === 'createRule()') {
        console.log('Found createRule button, clicking...');
        b.click();
      }
    });
  });
  await pg.waitForTimeout(5000);

  const isOpen = await pg.evaluate(() => {
    const modals = document.querySelectorAll('.fixed.inset-0');
    for (const m of modals) { if (m.offsetParent !== null) return true; }
    return false;
  });
  console.log('Modal still open:', isOpen);

  await browser.close();
})();
