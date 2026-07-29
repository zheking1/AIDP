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
    await page.waitForTimeout(1500);
  };

  // Load admin pages
  await click('用户管理');
  await click('系统设置');

  const result = await page.evaluate(() => {
    // Get all tabs
    const tabs = document.querySelectorAll('[id^="tab-content-"]');
    const info = [];
    tabs.forEach(el => {
      const id = el.id;
      const isActive = getComputedStyle(el).display !== 'none';
      const wrapper = el.firstElementChild;
      const childCount = wrapper ? wrapper.children.length : -1;
      const firstTag = wrapper && wrapper.children.length > 0 ? wrapper.children[0].tagName : 'none';
      info.push({id, isActive, childCount, firstTag});
    });
    return info;
  });
  
  console.log('ALL tabs:');
  result.forEach(r => console.log(`  ${r.id}: active=${r.isActive} children=${r.childCount} first=${r.firstTag}`));

  await browser.close();
})();