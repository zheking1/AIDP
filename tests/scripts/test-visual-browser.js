const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  
  // 打开 DevTools Console
  await context.newCDPSession(page);
  
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);
  
  // 点击技能库
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('技能库') && b.offsetParent) b.click();
    });
  });
  await page.waitForTimeout(5000);
  
  console.log('浏览器已打开，请查看控制台。5秒后关闭...');
  await page.waitForTimeout(5000);
  
  await browser.close();
})();