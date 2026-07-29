const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const pg = await ctx.newPage();

  // Collect JS errors
  const jsErrors = [];
  pg.on('pageerror', err => jsErrors.push(err.message));
  pg.on('console', msg => {
    if (msg.type() === 'error') jsErrors.push(msg.text());
  });

  // Login
  await pg.goto(BASE + '/login');
  await pg.fill('input[name="username"]', 'admin');
  await pg.fill('input[name="password"]', 'admin123');
  await pg.click('button[type="submit"]');
  await pg.waitForURL('**/');
  console.log('Logged in');

  // Navigate to skills hub
  await pg.goto(BASE + '/hub/skills');
  await pg.waitForTimeout(2000);
  console.log('Skills hub loaded');

  // Check for Alpine
  const hasAlpine = await pg.evaluate(() => typeof window.Alpine !== 'undefined');
  console.log('Alpine loaded:', hasAlpine);

  // Check if personalSkillsPage is registered
  const hasPersonalSkillsPage = await pg.evaluate(() => {
    return typeof window.personalSkillsPage === 'function';
  });
  console.log('window.personalSkillsPage exists:', hasPersonalSkillsPage);

  // Check if element exists with x-data
  const hasXData = await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    return el ? el.getAttribute('x-data') : 'NONE';
  });
  console.log('x-data element:', hasXData);

  // Click "我的技能" tab
  const personalTab = await pg.locator('text=我的技能').first();
  await personalTab.click();
  await pg.waitForTimeout(3000);
  console.log('Clicked "我的技能" tab');

  // Check for Alpine component init
  const afterLoad = await pg.evaluate(() => {
    const el = document.querySelector('#hub-content [x-data]');
    if (!el) return 'NO x-data in content';
    const xData = el.getAttribute('x-data');
    const hasInit = el.hasAttribute('x-init');
    return { xData, hasInit };
  });
  console.log('After tab load:', JSON.stringify(afterLoad));

  // Check Alpine data on element
  const alpineData = await pg.evaluate(() => {
    const el = document.querySelector('#hub-content [x-data]');
    if (!el) return 'NO ELEMENT';
    try {
      const data = Alpine.$data(el);
      return { keys: Object.keys(data).slice(0, 10), showCreateModal: data.showCreateModal };
    } catch(e) {
      return 'Alpine.$data error: ' + e.message;
    }
  });
  console.log('Alpine data:', JSON.stringify(alpineData));

  // Try clicking "创建技能"
  const createBtn = await pg.locator('text=创建技能').first();
  await createBtn.click();
  await pg.waitForTimeout(1000);
  console.log('Clicked "创建技能"');

  // Check if modal appeared
  const modalCheck = await pg.evaluate(() => {
    const el = document.querySelector('#hub-content [x-data]');
    if (!el) return 'NO ELEMENT';
    try {
      const data = Alpine.$data(el);
      return { showCreateModal: data.showCreateModal };
    } catch(e) {
      return 'Error: ' + e.message;
    }
  });
  console.log('After create click:', JSON.stringify(modalCheck));

  console.log('JS Errors:', jsErrors.length === 0 ? 'NONE' : jsErrors.join(' | '));
  await browser.close();
})();
