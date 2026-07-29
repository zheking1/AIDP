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

  // Check current projects count
  let count = await p.evaluate(() => {
    const el = document.querySelector('[x-data="projectsPage()"]');
    return el ? Alpine.$data(el).projects?.length || 0 : -1;
  });
  console.log('Before create, project count:', count);

  // Log the raw component state
  const state = await p.evaluate(() => {
    const el = document.querySelector('[x-data="projectsPage()"]');
    if (!el) return { error: 'component not found' };
    const d = Alpine.$data(el);
    return {
      hasNewProject: !!d.newProject,
      newProjectKeys: d.newProject ? Object.keys(d.newProject) : [],
      hasCreateProject: typeof d.createProject === 'function',
      hasLoadProjects: typeof d.loadProjects === 'function',
    };
  });
  console.log('Component state:', JSON.stringify(state));

  // Create project via evaluate
  await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    d.newProject = { name: 'TestProj-' + Date.now(), description: 'Auto test', visibility: 'private', tech_stack: ['Python'] };
    d.createProject();
  });
  await p.waitForTimeout(4000);

  // Check result
  const result = await p.evaluate(async () => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    await new Promise(r => setTimeout(r, 2000));
    const found = d.projects?.some(p => p.name.includes('TestProj-'));
    return {
      found,
      count: d.projects?.length || 0,
      showCreateModal: d.showCreateModal,
      creating: d.creating,
    };
  });
  console.log('After create:', JSON.stringify(result));

  // Now try creating via the API directly through the browser
  const apiResult = await p.evaluate(async () => {
    const name = 'APIDirect-' + Date.now();
    const r = await fetch('/api/projects?name=' + encodeURIComponent(name) + '&description=direct', { method: 'POST' });
    if (!r.ok) return { error: r.status, body: await r.text() };
    const data = await r.json();
    // Delete it
    await fetch('/api/projects/' + data.id, { method: 'DELETE' });
    return { created: data.id, name: data.name };
  });
  console.log('API direct create:', JSON.stringify(apiResult));

  // Also test the frontend's createProject via actual button click
  const fresh = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    d.showCreateModal = true;
    return d.showCreateModal;
  });
  console.log('Modal open via data:', fresh);

  await b.close();
  console.log('Done');
})();
