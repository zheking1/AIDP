const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // Ensure test project
  await page.evaluate(async () => {
    const r = await fetch('/api/projects');
    const d = await r.json();
    const exists = (d.items || []).find(p => p.name === 'LayoutTest');
    if (!exists) {
      await fetch('/api/projects', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:'LayoutTest',description:'t',tech_stack:[]}) });
    }
  });
  await page.waitForTimeout(1000);

  // Go to workspace
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // Check: are there project options in the select?
  const selectInfo = await page.evaluate(() => {
    const sel = document.querySelector('select');
    if (!sel) return 'NO SELECT';
    return Array.from(sel.options).map(o => ({ val: o.value, text: o.text }));
  });
  console.log('Project options:', JSON.stringify(selectInfo));

  // Select the LayoutTest project
  await page.evaluate(() => {
    const sel = document.querySelector('select');
    if (!sel) return;
    for (const opt of sel.options) {
      if (opt.text.includes('LayoutTest')) {
        sel.value = opt.value;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        break;
      }
    }
  });
  await page.waitForTimeout(3000);

  // Click 项目仪表盘 button
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('仪表盘') && b.offsetParent !== null) { b.click(); }
    });
  });
  await page.waitForTimeout(3000);

  // Now inspect the RENDERED layout (inside workspace with Tailwind)
  const dashboardLayout = await page.evaluate(() => {
    const tab = Array.from(document.querySelectorAll('[id^="tab-content-"]')).find(el => getComputedStyle(el).display !== 'none');
    if (!tab) return 'NO TAB';
    const wrapper = tab.firstElementChild;
    if (!wrapper) return 'NO WRAPPER, first=' + (tab.firstChild?.nodeName || 'none');
    const firstDiv = wrapper.querySelector(':scope > div:first-of-type');
    if (!firstDiv) return 'NO HEADER, wrapperTag=' + wrapper.tagName + ' wrapperChildren=' + wrapper.children.length;
    const s = getComputedStyle(firstDiv);
    return {
      headerDisplay: s.display,
      headerJustify: s.justifyContent,
      headerPT: s.paddingTop,
      headerPB: s.paddingBottom,
      headerBB: s.borderBottomWidth,
      headerFlex: s.display === 'flex' && s.justifyContent === 'space-between' ? 'OK' : 'MISMATCH'
    };
  });
  console.log('Dashboard layout:', JSON.stringify(dashboardLayout));

  // Also check: admin users page (should have same layout)
  await page.evaluate(() => { document.querySelector('nav')?.scrollTo(0, 9999); });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('用户管理') && b.offsetParent !== null) { b.click(); }
    });
  });
  await page.waitForTimeout(3000);
  const adminLayout = await page.evaluate(() => {
    const tab = Array.from(document.querySelectorAll('[id^="tab-content-"]')).find(el => getComputedStyle(el).display !== 'none');
    if (!tab) return 'NO TAB';
    const wrapper = tab.firstElementChild;
    if (!wrapper) return 'NO WRAPPER';
    const firstDiv = wrapper.querySelector(':scope > div:first-of-type');
    if (!firstDiv) return 'NO HEADER';
    const s = getComputedStyle(firstDiv);
    return {
      headerDisplay: s.display,
      headerJustify: s.justifyContent,
      headerPT: s.paddingTop,
      headerPB: s.paddingBottom,
      headerFlex: s.display === 'flex' && s.justifyContent === 'space-between' ? 'OK' : 'DIFF'
    };
  });
  console.log('Admin users layout:', JSON.stringify(adminLayout));

  // Load knowledge center for comparison
  await page.evaluate(() => { document.querySelector('nav')?.scrollTo(0, 0); });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('知识中心') && b.offsetParent !== null) { b.click(); }
    });
  });
  await page.waitForTimeout(3000);
  const kbLayout = await page.evaluate(() => {
    const tab = Array.from(document.querySelectorAll('[id^="tab-content-"]')).find(el => getComputedStyle(el).display !== 'none');
    if (!tab) return 'NO TAB';
    const wrapper = tab.firstElementChild;
    if (!wrapper) return 'NO WRAPPER';
    const firstDiv = wrapper.querySelector(':scope > div:first-of-type');
    if (!firstDiv) return 'NO HEADER';
    const s = getComputedStyle(firstDiv);
    return {
      headerDisplay: s.display,
      headerJustify: s.justifyContent,
      headerPT: s.paddingTop,
      headerPB: s.paddingBottom,
      headerBB: s.borderBottomWidth,
      headerFlex: s.display === 'flex' && s.justifyContent === 'space-between' ? 'OK' : 'DIFF'
    };
  });
  console.log('Knowledge center layout:', JSON.stringify(kbLayout));

  await browser.close();
})();