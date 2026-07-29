const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('console', msg => { if (msg.type() === 'error') console.log('CONSOLE:', msg.text().substring(0,150)); });
  
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);
  
  // Load skills page
  await page.evaluate(() => { document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('技能库')&&b.offsetParent) b.click(); }); });
  await page.waitForTimeout(3000);
  
  // Also check for the 404
  const hasAlpineWarnings = await page.evaluate(() => {
    // Alpine 警告会被 console.warn 过滤，但在 eval 中我们可以检查 window 变量
    return {
      showDetailModalExists: 'showDetailModal' in window,
      detailExists: 'detail' in window,
      showGroupModalExists: 'showGroupModal' in window
    };
  });
  console.log('Window vars:', JSON.stringify(hasAlpineWarnings));
  
  // Now check if the skills page's Alpine component is working
  const componentWorks = await page.evaluate(() => {
    try {
      // Find the Alpine component for skills
      const tab = Array.from(document.querySelectorAll('[id^=tab-content-]')).find(el => getComputedStyle(el).display !== 'none');
      if (!tab) return 'no tab';
      const wrapper = tab.firstElementChild;
      if (!wrapper) return 'no wrapper';
      const hasXData = wrapper.hasAttribute('x-data');
      const funcName = wrapper.getAttribute('x-data');
      // Try calling the function
      if (funcName && window[funcName.replace('()', '')]) {
        return { hasXData, funcName, canCall: true };
      }
      return { hasXData, funcName, canCall: false };
    } catch(e) {
      return 'error: ' + e.message;
    }
  });
  console.log('Component:', JSON.stringify(componentWorks));
  
  await browser.close();
})();