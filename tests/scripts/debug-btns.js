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
  await pg.evaluate(() => {
    const ws = Alpine.$data(document.querySelector('[x-data="workspace()"]'));
    ws.openTab('sp', '我的技能', 'fas fa-user', '/skills/personal');
  });
  await pg.waitForTimeout(5000);
  const btns = await pg.evaluate(() => {
    const el = document.getElementById('tab-content-sp');
    if (!el) return 'no tab-content-sp';
    const buttons = el.querySelectorAll('button');
    return Array.from(buttons).slice(0, 15).map(b => ({
      text: b.textContent.trim().substring(0, 40),
      visible: b.offsetParent !== null,
      rect: b.getBoundingClientRect()
    }));
  });
  console.log(JSON.stringify(btns, null, 2));
  await browser.close();
})();
