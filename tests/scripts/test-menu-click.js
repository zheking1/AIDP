const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 400 });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  async function click(text) {
    const btns = await page.$$('button');
    for (const b of btns) {
      const t = await b.textContent().catch(() => '');
      if (t.includes(text)) { await b.click(); return true; }
    }
    return false;
  }

  const pages = [
    ['知识中心', '创建知识库'],
    ['技能库', '全局技能'],
    ['记忆中心', '记忆列表'],
    ['代码沙箱', '代码沙箱'],
    ['质量检查', '质量检查'],
  ];

  let ok = 0, fail = 0;
  for (const [name, keyword] of pages) {
    console.log(`点击 "${name}"`);
    await click(name);
    await page.waitForTimeout(4000);
    const text = await page.textContent('body');
    const found = text.includes(keyword);
    if (found) ok++; else fail++;
    console.log(`  ${found ? '✅' : '❌'} "${keyword}" ${found ? '可见' : '不可见'}`);
  }

  console.log(`\n${'='.repeat(40)}\n结果: ${ok}/${ok+fail} 通过`);
  await page.waitForTimeout(2000);
  await browser.close();
})();