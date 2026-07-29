const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const pg = await browser.newPage();
  await pg.goto('http://192.168.0.100:8883/login', { waitUntil: 'domcontentloaded' });
  await pg.fill('input[name="username"]', 'admin');
  await pg.fill('input[name="password"]', 'admin123');
  await pg.click('button[type="submit"]');
  await pg.waitForTimeout(2000);
  await pg.goto('http://192.168.0.100:8883/', { waitUntil: 'networkidle' });
  await pg.waitForTimeout(5000);

  // 打开个人技能
  await pg.evaluate(() => {
    const ws = Alpine.$data(document.querySelector('[x-data="workspace()"]'));
    ws.openTab('sp', '我的技能', 'fas fa-user', '/skills/personal');
  });
  await pg.waitForTimeout(5000);

  // 检查 x-data 是否存在
  const status = await pg.evaluate(() => {
    const el = document.querySelector('#tab-content-sp [x-data]');
    if (!el) return { found: false };
    return {
      found: true,
      xData: el.getAttribute('x-data'),
      hasAlpineData: !!el._x_dataStack,
      hasAlpine: typeof Alpine !== 'undefined',
    };
  });
  console.log('Status:', JSON.stringify(status));

  // 尝试直接用 page.click 点击
  try {
    await pg.locator('#tab-content-sp button:has-text("创建技能")').first().click({ timeout: 3000 });
    console.log('Click succeeded');
  } catch(e) {
    console.log('Click failed:', e.message.substring(0, 100));
  }

  // 检查弹窗
  await pg.waitForTimeout(1000);
  const modalCheck = await pg.evaluate(() => {
    const el = document.querySelector('#tab-content-sp [x-data]');
    if (!el) return 'no element';
    const data = Alpine.$data(el);
    return { showCreateModal: data.showCreateModal };
  });
  console.log('Modal state:', JSON.stringify(modalCheck));

  await browser.close();
})();
