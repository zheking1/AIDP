const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  const click = async (text) => {
    const btns = await page.$$('button');
    for (const b of btns) {
      if ((await b.textContent().catch(()=>'')).includes(text)) { await b.click(); break; }
    }
    await page.waitForTimeout(2000);
  };

  const pages = ['知识中心', '技能库', '记忆中心', '代码沙箱', '质量检查', '用户管理', '系统设置', '审计日志'];

  for (const name of pages) {
    await click(name);
    await page.screenshot({ path: `screenshot_${name}.png`, fullPage: false });
    console.log('截图:', name);
  }

  await browser.close();
  console.log('完成，共', pages.length, '张截图');
})();