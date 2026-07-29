const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const pg = await ctx.newPage();

  pg.on('pageerror', err => console.log('PAGE_ERROR:', err.message));
  pg.on('console', msg => {
    if (msg.type() === 'error') console.log('CONSOLE_ERROR:', msg.text().substring(0, 200));
    if (msg.text().includes('Script eval') || msg.text().includes('personal') || msg.text().includes('Load failed')) console.log('HUB_LOG:', msg.text());
  });

  // Login
  await pg.goto('http://192.168.0.100:8883/login');
  await pg.fill('input[name="username"]', 'admin');
  await pg.fill('input[name="password"]', 'admin123');
  await pg.click('button[type="submit"]');
  await pg.waitForURL('**/');
  console.log('--- Logged in ---');

  // Go directly to skills hub
  await pg.goto('http://192.168.0.100:8883/hub/skills');
  await pg.waitForTimeout(3000);
  console.log('--- Hub loaded ---');

  // Click "我的技能" tab
  const tabs = await pg.locator('button:has-text("我的技能")');
  console.log('Tab found:', await tabs.count() > 0);
  await tabs.first().click();
  await pg.waitForTimeout(5000);
  console.log('--- Tab clicked ---');

  // Check window.personalSkillsPage after tab load
  const check = await pg.evaluate(() => {
    return {
      personalSkillsPageExists: typeof window.personalSkillsPage !== 'undefined',
      personalSkillsPageType: typeof window.personalSkillsPage,
      windowKeys: Object.keys(window).filter(k => k.toLowerCase().includes('personal') || k.toLowerCase().includes('skill')).slice(0, 5),
      hasScopedEval: typeof window.globalSkillsPage !== 'undefined',
    };
  });
  console.log('After tab load:', JSON.stringify(check, null, 2));

  // Check the hub-content area
  const hubContent = await pg.evaluate(() => {
    const el = document.getElementById('hub-content');
    if (!el) return { error: 'no hub-content' };
    const inner = el.innerHTML.substring(0, 500);
    return {
      hasXData: el.querySelector('[x-data]') !== null,
      xDataValue: el.querySelector('[x-data]')?.getAttribute('x-data'),
      hasScript: inner.includes('<script>') || inner.includes('window.personal'),
      innerStart: inner.substring(0, 200),
    };
  });
  console.log('Hub content:', JSON.stringify(hubContent, null, 2));

  // Check Alpine state
  const alpineState = await pg.evaluate(() => {
    try {
      const el = document.querySelector('#hub-content [x-data]');
      if (!el) return { error: 'no x-data element' };
      const data = Alpine.$data(el);
      return {
        keys: Object.keys(data),
        showCreateModal: data.showCreateModal,
        showImportModal: data.showImportModal,
      };
    } catch(e) {
      return { error: e.message, stack: e.stack?.substring(0, 300) };
    }
  });
  console.log('Alpine state:', JSON.stringify(alpineState, null, 2));

  // Try clicking create
  try {
    await pg.locator('#hub-content button:has-text("创建技能")').first().click();
    await pg.waitForTimeout(1000);
    const after = await pg.evaluate(() => {
      const el = document.querySelector('#hub-content [x-data]');
      if (!el) return 'no element';
      try {
        return Alpine.$data(el).showCreateModal;
      } catch(e) {
        return 'error: ' + e.message;
      }
    });
    console.log('After create click:', after);
  } catch(e) {
    console.log('Create click failed:', e.message);
  }

  await browser.close();
})();
