const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin'); await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]'); await page.waitForTimeout(3000);

  // Load documents page directly
  await page.goto(BASE + '/knowledge/documents?partial=1', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  const layout = await page.evaluate(() => {
    const body = document.body;
    const firstDiv = body.firstElementChild;
    if (!firstDiv) return 'no div';
    const header = firstDiv.querySelector(':scope > div:first-of-type');
    if (!header) return 'no header';
    const s = getComputedStyle(header);
    const bodySection = firstDiv.querySelector(':scope > div:nth-of-type(2)');
    const bs = bodySection ? getComputedStyle(bodySection) : null;
    return {
      header: `${s.display} ${s.justifyContent} pt=${s.paddingTop} pb=${s.paddingBottom} bb=${s.borderBottomWidth}`,
      body: bs ? `pt=${bs.paddingTop}` : 'none',
      children: firstDiv.children.length,
      headerHTML: header.innerHTML.replace(/\s+/g,' ').substring(0,200)
    };
  });
  console.log(JSON.stringify(layout, null, 2));
  await browser.close();
})();