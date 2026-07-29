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

  // Try creating a project via API
  const result = await page.evaluate(async () => {
    try {
      const r = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'test-proj', description: 'test', tech_stack: ['Python'] })
      });
      const text = await r.text();
      return { status: r.status, body: text.substring(0, 500) };
    } catch(e) {
      return { status: 0, error: e.message };
    }
  });
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})();