const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();

  // Login
  await p.goto('http://192.168.0.100:8883/login', { waitUntil: 'domcontentloaded' });
  await p.fill('input[name="username"]', 'admin');
  await p.fill('input[name="password"]', 'admin123');
  await p.click('button[type="submit"]');
  await p.waitForTimeout(2000);

  // Fetch the raw partial content and check the script
  const rawContent = await p.evaluate(async () => {
    const r = await fetch('/projects?partial=1');
    return await r.text();
  });
  
  // Extract script content
  const scriptMatch = rawContent.match(/<script>([\s\S]*?)<\/script>/);
  if (scriptMatch) {
    const scriptContent = scriptMatch[1];
    const createMatch = scriptContent.match(/createProject[\s\S]{0,300}/);
    if (createMatch) {
      console.log('Script createProject:', createMatch[0]);
    }
    const hasUrlSP = scriptContent.includes('URLSearchParams');
    console.log('Has URLSearchParams in script:', hasUrlSP);
    const hasJson = scriptContent.includes('JSON.stringify');
    console.log('Has JSON.stringify in script:', hasJson);
  }

  // Also check what the workspace loads
  await p.goto('http://192.168.0.100:8883/', { waitUntil: 'networkidle' });
  await p.waitForTimeout(3000);

  // Intercept the network request for the partial
  const requests = [];
  p.on('response', resp => {
    if (resp.url().includes('/projects?partial=1')) {
      requests.push({ status: resp.status(), url: resp.url() });
    }
  });

  await p.evaluate(() => {
    Alpine.$data(document.querySelector('[x-data="workspace()"]')).openTab('proj2', '项目列表', 'fas fa-folder', '/projects');
  });
  await p.waitForTimeout(5000);

  // Now check the rendered function
  const fnSrc = await p.evaluate(() => {
    const d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    const fn = d.createProject ? d.createProject.toString() : 'missing';
    return { 
      fn: fn.substring(0, 200),
      url: window.location.href
    };
  });
  console.log('Browser createProject:', fnSrc.fn);
  console.log('Network requests:', JSON.stringify(requests));

  await b.close();
})();
