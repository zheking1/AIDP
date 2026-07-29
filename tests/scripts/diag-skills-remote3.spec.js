const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const pg = await browser.newContext().then(c => c.newPage());

  await pg.goto('http://192.168.0.100:8883/login');
  await pg.fill('input[name="username"]', 'admin');
  await pg.fill('input[name="password"]', 'admin123');
  await pg.click('button[type="submit"]');
  await pg.waitForURL('**/');

  // Go to skills hub
  await pg.goto('http://192.168.0.100:8883/hub/skills');
  await pg.waitForTimeout(2000);

  // Click "我的技能" tab
  await pg.locator('button:has-text("我的技能")').first().click();
  await pg.waitForTimeout(3000);

  // Check state BEFORE clicking
  const beforeClick = await pg.evaluate(() => {
    const el = document.querySelector('#hub-content [x-data]');
    if (!el) return { error: 'no x-data element' };
    try {
      const d = Alpine.$data(el);
      // Check MODAL exists in DOM
      const modal = el.querySelector('[x-show="showCreateModal"]');
      return {
        showCreateModal: d.showCreateModal,
        modalInDOM: modal !== null,
        modalVisible: modal ? window.getComputedStyle(modal).display !== 'none' : 'N/A',
        modalClass: modal ? modal.getAttribute('class') : 'N/A',
      };
    } catch(e) {
      return { error: e.message };
    }
  });
  console.log('BEFORE click:', JSON.stringify(beforeClick));

  // Click "创建技能"
  const createBtn = await pg.locator('#hub-content button:has-text("创建技能")').first();
  await createBtn.click();
  await pg.waitForTimeout(500);

  // Check state AFTER clicking
  const afterClick = await pg.evaluate(() => {
    const el = document.querySelector('#hub-content [x-data]');
    if (!el) return { error: 'no x-data element' };
    try {
      const d = Alpine.$data(el);
      const modal = el.querySelector('[x-show="showCreateModal"]');
      return {
        showCreateModal: d.showCreateModal,
        modalInDOM: modal !== null,
        modalVisible: modal ? window.getComputedStyle(modal).display !== 'none' : 'N/A',
      };
    } catch(e) {
      return { error: e.message };
    }
  });
  console.log('AFTER click:', JSON.stringify(afterClick));

  // Check globalSkillsPage behavior (for comparison)
  await pg.locator('button:has-text("全局技能")').first().click();
  await pg.waitForTimeout(3000);

  const globalTab = await pg.evaluate(() => {
    const el = document.querySelector('#hub-content [x-data]');
    if (!el) return { error: 'no element' };
    try {
      const d = Alpine.$data(el);
      return {
        xData: el.getAttribute('x-data'),
        hasCreateBtn: el.innerHTML.includes('@click="showCreateModal = true"'),
        showCreateModal: d.showCreateModal,
        keys: Object.keys(d).slice(0, 5),
      };
    } catch(e) {
      return { error: e.message };
    }
  });
  console.log('GLOBAL tab:', JSON.stringify(globalTab));

  await browser.close();
})();
