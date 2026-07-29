const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(BASE+'/login', { waitUntil: 'networkidle' });
  await page.fill('#username','admin'); await page.fill('#password','admin123');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(3000);

  // Navigate to skills hub
  await page.evaluate(() => {
    const nav = document.querySelector('nav');
    const btns = nav.querySelectorAll('button');
    for (const b of btns) {
      if (b.textContent.includes('技能库') && b.offsetParent) { b.click(); return; }
    }
  });
  await page.waitForTimeout(5000);

  // Check the iframe content
  const iframeInfo = await page.evaluate(() => {
    const iframe = document.querySelector('iframe');
    if (!iframe) return {error: 'No iframe found', html: document.querySelector('[id^=tab-content-]')?.innerHTML?.substring(0,500)};
    try {
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      const html = doc.body?.innerHTML?.substring(0, 1000) || 'empty';
      return {
        src: iframe.src,
        hasExecConfig: html.includes('运行参数') || html.includes('execConfigStr'),
        hasReviewTab: html.includes('审核'),
        htmlPreview: html.substring(0, 400)
      };
    } catch(e) {
      return {error: e.message, src: iframe.src};
    }
  });
  console.log('Iframe info:', JSON.stringify(iframeInfo, null, 2));

  // If iframe cross-origin, check the backend response directly
  const directCheck = await page.evaluate(async () => {
    // Try loading the personal page content through the workspace
    const r = await fetch('/skills/personal?embed=1');
    const html = await r.text();
    return {
      length: html.length,
      hasExecConfig: html.includes('运行参数') || html.includes('execConfigStr'),
      hasReviewTab: html.includes('审核'),
      hasPackageDownload: html.includes('package') || html.includes('下载'),
      preview: html.substring(500, 800)
    };
  });
  console.log('Direct check:', JSON.stringify(directCheck, null, 2));

  await browser.close();
})();