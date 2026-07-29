const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  let errors = [];
  page.on('pageerror', e => errors.push({ type:'pageerror', msg: e.message.substring(0,100) }));
  page.on('console', msg => { if (msg.type() === 'error') errors.push({ type:'console', msg: msg.text().substring(0,100) }); });
  page.on('response', r => { if (r.status() >= 400) errors.push({ type:'http', msg: r.status()+' '+r.url().substring(0,80) }); });

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // Ensure test project
  const projectId = await page.evaluate(async () => {
    const r = await fetch('/api/projects');
    const d = await r.json();
    let p = (d.items || []).find(x => x.name === 'LayoutTest');
    if (!p) {
      await fetch('/api/projects', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:'LayoutTest',description:'t',tech_stack:[]}) });
      const r2 = await fetch('/api/projects');
      const d2 = await r2.json();
      p = (d2.items || []).find(x => x.name === 'LayoutTest');
    }
    return p ? p.id : null;
  });
  if (!projectId) { console.log('no project'); process.exit(1); }

  // Go to workspace and select project
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await page.evaluate((id) => {
    const sel = document.querySelector('select');
    if (sel) { sel.value = String(id); sel.dispatchEvent(new Event('change', {bubbles:true})); }
  }, projectId);
  await page.waitForTimeout(3000);

  // Test THREE specific pages
  const targets = ['项目规则', '项目 Agent', '项目流程'];
  
  for (const tgt of targets) {
    errors = [];
    console.log('\n=== ' + tgt + ' ===');
    
    // Find and click button
    await page.evaluate((label) => {
      const allBtns = document.querySelectorAll('button');
      for (const b of allBtns) {
        if (b.textContent.includes('LayoutTest')) { b.scrollIntoView({block:'center'}); break; }
      }
    }, tgt);
    await page.waitForTimeout(500);

    await page.evaluate((label) => {
      document.querySelectorAll('button').forEach(b => {
        if (b.textContent.includes(label) && b.offsetParent) b.click();
      });
    }, tgt);
    await page.waitForTimeout(3000);

    // Layout check
    const layout = await page.evaluate(() => {
      const tab = Array.from(document.querySelectorAll('[id^="tab-content-"]')).find(el => getComputedStyle(el).display !== 'none');
      if (!tab) return { error: 'no tab' };
      const w = tab.firstElementChild;
      if (!w) return { error: 'no wrapper', first: tab.firstChild?.nodeName };
      const firstDiv = w.querySelector(':scope > div');
      if (!firstDiv) return { error: 'no first div', children: w.children.length };
      const s = getComputedStyle(firstDiv);
      const bodyDiv = w.querySelector(':scope > div:nth-of-type(2)');
      const bs = bodyDiv ? getComputedStyle(bodyDiv) : null;
      return {
        headerDisplay: s.display,
        headerJustify: s.justifyContent,
        headerPT: s.paddingTop,
        headerPB: s.paddingBottom,
        headerBB: s.borderBottomWidth,
        bodyPT: bs ? bs.paddingTop : 'N/A',
        tabPadding: getComputedStyle(tab).paddingLeft,
        classes: firstDiv.className
      };
    });
    console.log('  Layout:', JSON.stringify(layout));
    
    if (errors.length) {
      console.log('  ERRORS:');
      errors.slice(0,8).forEach(e => console.log('    ' + e.type + ': ' + e.msg));
    } else {
      console.log('  No errors');
    }
  }

  await browser.close();
})();