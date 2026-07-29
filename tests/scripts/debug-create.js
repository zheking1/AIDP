const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({headless:true});
  const ctx = await b.newContext({viewport:{width:1440,height:900}});
  const pg = await ctx.newPage();

  pg.on('response', async r => {
    if (r.url().includes('/api/projects') && r.request().method() === 'POST') {
      console.log('[POST]', r.status(), r.url());
    }
  });

  try {
    await pg.goto('http://192.168.0.100:8883/login', {timeout:10000});
    await pg.fill('input[name="username"]', 'admin');
    await pg.fill('input[name="password"]', 'admin123');
    await pg.click('button[type="submit"]');
    await pg.waitForTimeout(2000);

    await pg.goto('http://192.168.0.100:8883/', {timeout:10000});
    await pg.waitForFunction(() => typeof Alpine !== 'undefined', {timeout: 15000});
    console.log('[OK] Alpine loaded');

    await pg.evaluate(() => {
      var ws = Alpine.$data(document.querySelector('[x-data]'));
      ws.openTab('projects', '项目列表', 'fa-folder', '/projects');
    });
    await pg.waitForSelector('#tab-content-projects [x-data]', {timeout:10000});
    console.log('[OK] Projects tab loaded');

    // Check the function source
    const fnSrc = await pg.evaluate(() => {
      if (!window.projectsPage) return 'NOT FOUND';
      return window.projectsPage.toString().substring(0, 800);
    });
    console.log('[FN]:', fnSrc);

    // Direct create
    const result = await pg.evaluate(async () => {
      var el = document.querySelector('#tab-content-projects [x-data]');
      var d = Alpine.$data(el);
      d.newProject = { name: 'TestDirect-' + Date.now(), description: 'test', tech_stack: '' };
      await d.createProject();
      return { count: d.projects.length, created: d.projects.some(p => p.name.includes('TestDirect')) };
    });
    console.log('[RESULT]:', JSON.stringify(result));
  } catch(e) {
    console.error('[ERR]:', e.message);
  }
  await b.close();
})();
