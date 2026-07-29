const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const pg = await browser.newPage();
  pg.on('response', async r => { if (r.url().includes('/api/projects')) console.log('[API]', r.url().split('?')[0], r.status()); });
  await pg.goto('http://192.168.0.100:8883/login', { waitUntil: 'domcontentloaded' });
  await pg.fill('input[name="username"]', 'admin');
  await pg.fill('input[name="password"]', 'admin123');
  await pg.click('button[type="submit"]');
  await pg.waitForTimeout(2000);
  await pg.goto('http://192.168.0.100:8883/', { waitUntil: 'networkidle' });
  await pg.waitForTimeout(5000);
  await pg.evaluate(() => {
    const ws = Alpine.$data(document.querySelector('[x-data="workspace()"]'));
    ws.openTab('proj', '项目', 'fas fa-folder', '/projects');
  });
  await pg.waitForTimeout(5000);
  await pg.evaluate(() => {
    var d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    d.showCreateModal = true;
    d.newProject = { name: 'TestProjDebug-' + Date.now(), description: 'debug', type: 'python', nas_path: '' };
    d.createProject();
  });
  await pg.waitForTimeout(5000);
  const after = await pg.evaluate(() => {
    var d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return { count: d.projects?.length, modal: d.showCreateModal, loading: d.loading };
  });
  console.log('After:', after);
  await browser.close();
})();
