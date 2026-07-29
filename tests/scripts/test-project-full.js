const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  let errors = [];
  page.on('pageerror', e => errors.push({ type:'pageerror', msg: e.message.substring(0,100) }));
  page.on('console', msg => { if (msg.type() === 'error' || msg.type() === 'warning') errors.push({ type:msg.type(), msg: msg.text().substring(0,100) }); });
  page.on('response', r => { if (r.status() >= 400) errors.push({ type:'http', msg: r.status()+' '+r.url().substring(0,80) }); });

  const check = async (label) => {
    const errs = [...errors]; errors = [];
    return { label, errs };
  };

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // Create test project if needed
  const projectId = await page.evaluate(async () => {
    const r = await fetch('/api/projects');
    const d = await r.json();
    let p = (d.items || []).find(x => x.name === 'E2E-Test-Project');
    if (!p) {
      const r2 = await fetch('/api/projects', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:'E2E-Test-Project',description:'e2e test'}) });
      if (r2.ok) { const d2 = await r2.json(); p = d2; }
    }
    return p ? p.id : null;
  });
  if (!projectId) { console.log('无法创建项目'); process.exit(1); }
  console.log('项目 ID:', projectId);

  // Navigate to workspace without losing cookies
  await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(3000);

  // Debug: check workspace loaded correctly
  let wsCheck = await page.evaluate(() => ({
    hasSelect: !!document.querySelector('select'),
    url: window.location.href,
    selects: document.querySelectorAll('select').length
  }));
  
  if (!wsCheck.hasSelect) {
    console.log('Workspace not ready, URL:', wsCheck.url);
    // If still on login, try waiting more
    await page.waitForTimeout(3000);
    wsCheck = await page.evaluate(() => ({
      hasSelect: !!document.querySelector('select'),
      url: window.location.href
    }));
    if (!wsCheck.hasSelect) {
      throw new Error('Workspace failed to load. URL: ' + wsCheck.url);
    }
  }
  await page.waitForTimeout(3000);

  // 1. 知识中心 (reference, no project needed)
  errors = [];
  await page.evaluate(() => {
    document.querySelector('nav')?.scrollTo(0, 0);
    document.querySelectorAll('button').forEach(b => { if (b.textContent.includes('知识中心') && b.offsetParent) b.click(); });
  });
  await page.waitForTimeout(3000);
  let r = await check('知识中心(参考)');

  // 2. 选择项目
  errors = [];
  await page.evaluate((id) => {
    const sel = document.querySelector('select');
    if (sel) { sel.value = String(id); sel.dispatchEvent(new Event('change', {bubbles:true})); }
  }, projectId);
  await page.waitForTimeout(3000);
  await check('选择项目');

  // 3-9. 当前项目下所有页面
  const projectPages = [
    '项目仪表盘', '项目知识', '项目技能', '项目规则',
    '项目 Agent', '项目流程', '项目记忆', '项目设置'
  ];

  const results = [];
  for (const name of projectPages) {
    errors = [];
    // Click the menu button
    await page.evaluate((label) => {
      document.querySelectorAll('button').forEach(b => {
        if (b.textContent.includes(label) && b.offsetParent) b.click();
      });
    }, name);
    await page.waitForTimeout(3000);
    
    const result = await check(name);
    
    // Verify layout
    const layout = await page.evaluate((refName) => {
      const tab = Array.from(document.querySelectorAll('[id^="tab-content-"]')).find(el => getComputedStyle(el).display !== 'none');
      if (!tab) return { error: 'no tab' };
      const w = tab.firstElementChild;
      if (!w) return { error: 'no wrapper' };
      const h = w.querySelector(':scope > div');
      if (!h) return { error: 'no header div' };
      const s = getComputedStyle(h);
      const bd = w.querySelector(':scope > div:nth-of-type(2)');
      const bs = bd ? getComputedStyle(bd) : null;
      return {
        header: s.display + ' ' + s.justifyContent,
        pt: s.paddingTop, pb: s.paddingBottom, bb: s.borderBottomWidth,
        bodyPT: bs ? bs.paddingTop : 'N/A',
        tabPL: getComputedStyle(tab).paddingLeft
      };
    }, name);
    
    results.push({ name, errors: result.errs, layout });
  }

  // Print results
  console.log('\n' + '='.repeat(70));
  console.log('当前项目页面综合测试');
  console.log('='.repeat(70));

  let totalOk = 0, totalFail = 0;
  for (const r of results) {
    const issue = [];
    if (r.layout.error) issue.push(r.layout.error);
    if (r.errors.length) issue.push(r.errors.length + ' errors: ' + r.errors[0].msg.substring(0,60));
    if (r.layout.header !== 'flex space-between') issue.push('header=' + r.layout.header);
    
    if (issue.length) {
      totalFail++;
      console.log('❌', r.name, '→', issue.join('; '));
    } else {
      totalOk++;
      console.log('✅', r.name, '→', r.layout.header, 'pt=' + r.layout.pt, 'pb=' + r.layout.pb, 'bodyPT=' + r.layout.bodyPT);
    }
  }

  console.log('\n' + '='.repeat(70));
  console.log(`共 ${results.length} 项: ${totalOk} 通过, ${totalFail} 失败`);
  if (totalFail > 0) process.exit(1);

  await browser.close();
})();