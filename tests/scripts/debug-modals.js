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
    }
  });

  console.log('=== 检查所有可见按钮 ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 点击创建按钮
  await pg.locator('button', { hasText: '创建' }).first().click();
  await pg.waitForTimeout(1500);

  // 列出所有可见的 "创建" 按钮
  const createBtns = await pg.evaluate(() => {
    const results = [];
    const btns = document.querySelectorAll('button');
    for (const b of btns) {
      const text = b.textContent.trim();
      if (text === '创建' || text.includes('创建')) {
        const rect = b.getBoundingClientRect();
        const style = window.getComputedStyle(b);
        results.push({
          text,
          onclick: b.getAttribute('@click') || '',
          x: rect.x, y: rect.y, w: rect.width, h: rect.height,
          display: style.display,
          visibility: style.visibility,
          opacity: style.opacity,
          zIndex: style.zIndex,
          offsetParent: b.offsetParent?.tagName || null,
        });
      }
    }
    return results;
  });
  console.log('All 创建 buttons:', JSON.stringify(createBtns, null, 2));

  // 检查哪些 modal 是可见的
  const modals = await pg.evaluate(() => {
    const results = [];
    const els = document.querySelectorAll('.fixed.inset-0');
    for (const el of els) {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      results.push({
        tag: el.tagName,
        display: style.display,
        visibility: style.visibility,
        opacity: style.opacity,
        w: rect.width, h: rect.height,
        childH2: [...el.querySelectorAll('h2')].map(h => h.textContent.trim()),
      });
    }
    return results;
  });
  console.log('Modals:', JSON.stringify(modals, null, 2));

  await browser.close();
})();
