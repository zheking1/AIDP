const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  const result = await page.evaluate(async () => {
    const r = await fetch('/project/1/dashboard?partial=1');
    const text = await r.text();
    return { status: r.status, start: text.substring(0, 150) };
  });
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})();