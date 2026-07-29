const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
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

  // Check count before
  let before = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return { count: d.projects.length, names: d.projects.map(p => p.name) };
  });
  console.log('Before:', JSON.stringify(before));

  // Simulate clicking "创建项目" button
  const btn = p.locator('#tab-content-proj button:has-text("创建项目")').first();
  await btn.click();
  await p.waitForTimeout(1000);

  // Fill form using browser's evaluate
  await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    d.newProject.name = 'UITest-' + Date.now();
    d.newProject.description = 'UI created';
    d.createProject();
  });

  // Wait extra long
  await p.waitForTimeout(8000);

  // Check after
  let after = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return {
      count: d.projects.length,
      names: d.projects.map(p => p.name),
      loading: d.loading,
      showCreateModal: d.showCreateModal,
      creating: d.creating,
    };
  });
  console.log('After:', JSON.stringify(after));

  // Also check via API directly
  let apiCheck = await p.evaluate(async () => {
    const r = await fetch('/api/projects');
    const data = await r.json();
    return {
      count: data.items.length,
      names: data.items.map(p => p.name),
    };
  });
  console.log('API check:', JSON.stringify(apiCheck));

  await b.close();
})();
