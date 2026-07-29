const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  page.on('pageerror', e => console.log('  ERROR:', e.message.substring(0, 80)));

  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
  console.log('=== 登录后 ===');

  // 点击知识中心
  const click = async (name) => {
    const btns = await page.$$('button');
    for (const b of btns) {
      if ((await b.textContent().catch(()=>'')).includes(name)) { await b.click(); break; }
    }
    await page.waitForTimeout(500);
    console.log('=== 点击 ' + name + ' 后(500ms) ===');
    await page.waitForTimeout(2500);
    console.log('=== 点击 ' + name + ' 后(3s) ===');
  };

  await click('知识中心');
  await click('技能库');

  await browser.close();
})();