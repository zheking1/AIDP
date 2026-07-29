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

  await p.goto('http://192.168.0.100:8883/login', { waitUntil: 'domcontentloaded' });
  await p.fill('input[name="username"]', 'admin');
  await p.fill('input[name="password"]', 'admin123');
  await p.click('button[type="submit"]');
  await p.waitForTimeout(2000);

  // Load the content template directly
  const partialHtml = await p.evaluate(async () => {
    const r = await fetch('/projects?partial=1');
    return (await r.text()).substring(0, 500);
  });
  console.log('Partial HTML snippet:', partialHtml);

  await p.goto('http://192.168.0.100:8883/', { waitUntil: 'networkidle' });
  await p.waitForTimeout(3000);

  await p.evaluate(() => {
    Alpine.$data(document.querySelector('[x-data="workspace()"]')).openTab('proj', '项目列表', 'fas fa-folder', '/projects');
  });
  await p.waitForTimeout(5000);

  // Check the createProject source
  const fnSrc = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return d.createProject ? d.createProject.toString().substring(0, 300) : 'missing';
  });
  console.log('createProject source:', fnSrc);

  // Create project using actual button click
  await p.locator('#tab-content-proj button:has-text("创建项目")').first().click();
  await p.waitForTimeout(1000);
  
  const modal = p.locator('#tab-content-proj .fixed.inset-0:visible').last();
  await modal.locator('input').first().fill('FreshTest-' + Date.now());
  await modal.locator('textarea').first().fill('Fresh server test');
  await p.waitForTimeout(500);
  
  apiCalls.length = 0;
  await modal.locator('button:has-text("创建")').click();
  await p.waitForTimeout(3000);

  console.log('API calls:', JSON.stringify(apiCalls));

  const state = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return { count: d.projects.length, showCreateModal: d.showCreateModal };
  });
  console.log('Final state:', JSON.stringify(state));

  await b.close();
})();
