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
    ws.openTab('proj', '项目', 'fas fa-folder', '/projects');
  });
  await pg.waitForTimeout(5000);
  const btns = await pg.evaluate(() => {
    const el = document.getElementById('tab-content-proj');
    if (!el) return 'no tab';
    return Array.from(el.querySelectorAll('button')).slice(0, 15).map(b => ({
      text: b.textContent.trim().substring(0, 40),
      visible: b.offsetParent !== null
    }));
  });
  console.log(JSON.stringify(btns, null, 2));
  await browser.close();
})();
