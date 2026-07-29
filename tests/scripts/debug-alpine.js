const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';

async function login(pg) { await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' }); await pg.fill('input[name="username"]', 'admin'); await pg.fill('input[name="password"]', 'admin123'); await pg.click('button[type="submit"]'); await pg.waitForTimeout(2000); }

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  await login(pg);

  // Capture ALL console output
  pg.on('console', msg => console.log(`[BROWSER] ${msg.type()}: ${msg.text()}`));
  pg.on('pageerror', err => console.log(`[ERROR] ${err.message}`));

  pg.on('response', async resp => {
    if (resp.url().includes('/api/') && !resp.url().includes('stats') && !resp.url().includes('list') && !resp.url().includes('templates')) {
      console.log(`[API] ${resp.request().method()} ${resp.url().split('?')[0]} → ${resp.status()}`);
    }
  });

  console.log('=== 全局规则 - 检查 Alpine 初始化 ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(5000);

  // 检查 Alpine 是否初始化
  const alpineStatus = await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    return {
      hasAlpine: typeof Alpine !== 'undefined',
      hasXData: !!el,
      xDataValue: el?.getAttribute('x-data'),
      hasXDataStack: !!el?._x_dataStack,
      hasXProps: !!el?._x_props,
      allKeys: el ? Object.keys(el).filter(k => k.startsWith('_x') || k.startsWith('Alpine')) : [],
      windowAlpine: typeof window.Alpine,
    };
  });
  console.log('Alpine status:', JSON.stringify(alpineStatus, null, 2));

  // 尝试直接调用 window 函数
  const fnTest = await pg.evaluate(() => {
    return {
      hasGlobalRulesPage: typeof window.globalRulesPage,
      hasCreateRule: typeof window.createRule,
    };
  });
  console.log('Functions:', fnTest);

  await browser.close();
})();
