const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(BASE+'/login', { waitUntil: 'networkidle' });
  await page.fill('#username','admin'); await page.fill('#password','admin123');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(3000);

  // Check via direct fetch
  const r = await page.evaluate(async () => {
    const resp = await fetch('/skills/personal?embed=1');
    const html = await resp.text();
    return {
      hasExecConfig: html.includes('运行参数') || html.includes('execConfigStr'),
      hasReviewTab: html.includes('审核'),
      hasPackage: html.includes('package'),
      sample: html.substring(html.indexOf('创建技能'), html.indexOf('创建技能') + 200)
    };
  });
  console.log(JSON.stringify(r, null, 2));

  // Also navigate through the hub in an iframe
  await page.evaluate(() => {
    document.querySelector('nav')?.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('技能库') && b.offsetParent) b.click();
    });
  });
  await page.waitForTimeout(5000);

  const iframeSrc = await page.evaluate(() => {
    const iframe = document.querySelector('iframe');
    return iframe ? iframe.src : 'NO IFRAME';
  });
  console.log('Iframe src:', iframeSrc);

  await browser.close();
})();