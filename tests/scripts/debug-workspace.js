const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';

async function login(pg) { await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' }); await pg.fill('input[name="username"]', 'admin'); await pg.fill('input[name="password"]', 'admin123'); await pg.click('button[type="submit"]'); await pg.waitForTimeout(2000); }

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  
  pg.on('console', msg => { if (msg.type() === 'error') console.log(`[ERR] ${msg.text()}`); });

  await login(pg);
  console.log('=== 测试 workspace 加载 ===');
  await pg.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(5000);

  const ws = await pg.evaluate(() => ({
    hasAlpine: typeof Alpine !== 'undefined',
    hasWorkspace: typeof workspace === 'function',
    title: document.title,
    bodyLen: document.body.innerHTML.length,
  }));
  console.log('Workspace:', ws);

  if (ws.hasAlpine) {
    // 点击菜单打开规则页
    await pg.evaluate(() => {
      document.querySelectorAll('button').forEach(b => {
        if (b.textContent.includes('全局规则')) b.click();
      });
    });
    await pg.waitForTimeout(5000);

    const rules = await pg.evaluate(() => ({
      hasAlpine: typeof Alpine !== 'undefined',
      hasXData: !!document.querySelector('[x-data]'),
      xDataVal: document.querySelector('[x-data]')?.getAttribute('x-data'),
    }));
    console.log('After menu click:', rules);
  }

  await browser.close();
})();
