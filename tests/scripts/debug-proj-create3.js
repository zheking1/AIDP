const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  const errors = [];
  p.on('pageerror', err => errors.push(err.message));
  p.on('console', msg => { if (msg.type() === 'error') errors.push('console:' + msg.text()); });

  await p.goto('http://192.168.0.100:8883/login', { waitUntil: 'domcontentloaded' });
  await p.fill('input[name="username"]', 'admin');
  await p.fill('input[name="password"]', 'admin123');
  await p.click('button[type="submit"]');
  await p.waitForTimeout(2000);
  await p.goto('http://192.168.0.100:8883/', { waitUntil: 'networkidle' });
  await p.waitForTimeout(3000);

  // Open projects tab
  await p.evaluate(() => {
    const el = document.querySelector('[x-data="workspace()"]');
    Alpine.$data(el).openTab('proj', '项目列表', 'fas fa-folder', '/projects');
  });
  await p.waitForTimeout(4000);

  // Intercept network requests to see what happens
  const apiCalls = [];
  p.on('response', resp => {
    if (resp.url().includes('/api/projects')) {
      apiCalls.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
    }
  });

  // Click create button
  const btn = p.locator('#tab-content-proj button:has-text("创建项目")').first();
  await btn.click();
  await p.waitForTimeout(1000);

  // Check modal state
  let state1 = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return { showCreateModal: d.showCreateModal, creating: d.creating, name: d.newProject.name };
  });
  console.log('After click:', JSON.stringify(state1));

  // Create project via evaluate
  const ts = Date.now();
  await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    d.newProject.name = 'UITest-' + Date.now();
    d.newProject.description = 'UI created via eval';
    d.createProject();
  });

  await p.waitForTimeout(8000);

  // Check state
  let state2 = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return {
      showCreateModal: d.showCreateModal,
      creating: d.creating,
      projectCount: d.projects.length,
      loading: d.loading,
      errors: d.errors,
    };
  });
  console.log('After create:', JSON.stringify(state2));
  console.log('API calls:', JSON.stringify(apiCalls));
  console.log('JS errors:', errors);

  await b.close();
})();
