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

  // Track api calls
  const apiCalls = [];
  p.on('request', req => {
    if (req.url().includes('/api/projects')) {
      apiCalls.push({ url: req.url(), method: req.method(), headers: req.headers() });
    }
  });

  // Open projects tab  
  await p.evaluate(() => {
    Alpine.$data(document.querySelector('[x-data="workspace()"]')).openTab('proj', '项目列表', 'fas fa-folder', '/projects');
  });
  await p.waitForTimeout(4000);

  // Get the raw script that was loaded
  const scriptInfo = await p.evaluate(() => {
    const scripts = Array.from(document.querySelectorAll('#tab-content-proj script'));
    const externalScripts = Array.from(document.querySelectorAll('#tab-content-proj script[src]'));
    const inlineScripts = Array.from(document.querySelectorAll('#tab-content-proj script:not([src])'));
    return {
      total: scripts.length,
      external: externalScripts.length,
      inline: inlineScripts.length,
    };
  });
  console.log('Scripts in tab:', JSON.stringify(scriptInfo));

  // Check the projectsPage function source
  const fnCheck = await p.evaluate(() => {
    const fnStr = window.projectsPage ? window.projectsPage.toString() : 'not found';
    const hasCreate = fnStr.includes('createProject');
    const hasUrlSP = fnStr.includes('URLSearchParams');
    const urlMatch = fnStr.match(/fetch\('([^']+)'/);
    return {
      type: typeof window.projectsPage,
      hasCreate,
      hasUrlSP,
      fetchUrl: urlMatch ? urlMatch[1] : 'not found',
      snippet: fnStr.substring(fnStr.indexOf('createProject'), fnStr.indexOf('createProject') + 200),
    };
  });
  console.log('Function check:', JSON.stringify(fnCheck));

  // Also check the Alpine component data
  const compCheck = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    const createFnStr = d.createProject ? d.createProject.toString() : 'not found';
    const urlMatch = createFnStr.match(/fetch\('([^']+)'/);
    return {
      hasCreate: typeof d.createProject === 'function',
      fetchUrl: urlMatch ? urlMatch[1] : 'not found',
    };
  });
  console.log('Component check:', JSON.stringify(compCheck));

  // Now create a project and check the actual request
  const ts = Date.now();
  
  // Clear API calls
  apiCalls.length = 0;
  
  await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    d.showCreateModal = true;
  });
  await p.waitForTimeout(500);

  await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    d.newProject.name = 'DirectTest-' + Date.now();
    d.newProject.description = 'testing';
    d.createProject();
  });
  await p.waitForTimeout(3000);

  // Check the URL that was actually called
  console.log('API calls captured:', JSON.stringify(apiCalls));

  await b.close();
})();
