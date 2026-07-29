const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  
  const apiCalls = [];
  p.on('request', req => {
    if (req.url().includes('/api/projects')) {
      apiCalls.push({ url: req.url(), method: req.method() });
    }
  });
  const errors = [];
  p.on('pageerror', err => errors.push(err.message));
  p.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

  await p.goto('http://192.168.0.100:8883/login', { waitUntil: 'domcontentloaded' });
  await p.fill('input[name="username"]', 'admin');
  await p.fill('input[name="password"]', 'admin123');
  await p.click('button[type="submit"]');
  await p.waitForTimeout(2000);
  await p.goto('http://192.168.0.100:8883/', { waitUntil: 'networkidle' });
  await p.waitForTimeout(3000);

  // Open projects tab
  await p.evaluate(() => {
    Alpine.$data(document.querySelector('[x-data="workspace()"]')).openTab('proj', '项目列表', 'fas fa-folder', '/projects');
  });
  await p.waitForTimeout(5000);

  // Check what createProject looks like in the component
  const fnStr = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return d.createProject ? d.createProject.toString().substring(0, 300) : 'missing';
  });
  console.log('createProject source:', fnStr);

  // Click "创建项目" button
  await p.locator('#tab-content-proj button:has-text("创建项目")').first().click();
  await p.waitForTimeout(1000);
  
  // Fill form using Playwright locators (in the visible modal)
  const modal = p.locator('#tab-content-proj .fixed.inset-0:visible').last();
  const nameInput = modal.locator('input').first();
  await nameInput.fill('FreshTest-' + Date.now());
  const descInput = modal.locator('textarea').first();
  await descInput.fill('Fresh server test');
  await p.waitForTimeout(500);

  // Click create button in modal
  apiCalls.length = 0;
  await modal.locator('button:has-text("创建")').click();
  await p.waitForTimeout(3000);

  console.log('API calls:', JSON.stringify(apiCalls));
  console.log('Errors:', errors);

  // Check if project appears
  const state = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return { count: d.projects.length, showCreateModal: d.showCreateModal, loading: d.loading };
  });
  console.log('Final state:', JSON.stringify(state));

  await b.close();
})();
