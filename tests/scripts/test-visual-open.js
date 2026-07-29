const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // Get project ID
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
  if (!projectId) { console.log('no project'); await browser.close(); return; }

  // Go to workspace and select project
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.evaluate((id) => {
    const sel = document.querySelector('select');
    if (sel) { sel.value = String(id); sel.dispatchEvent(new Event('change', {bubbles:true})); }
  }, projectId);
  await page.waitForTimeout(2000);

  // Open project dashboard in workspace
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('项目仪表盘') && b.offsetParent) b.click();
    });
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'screenshot_dashboard.png', fullPage: false });
  console.log('截图: 项目仪表盘');

  // Open project rules
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('项目规则') && b.offsetParent) b.click();
    });
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'screenshot_rules.png', fullPage: false });
  console.log('截图: 项目规则');

  // Open project agent
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('项目 Agent') && b.offsetParent) b.click();
    });
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'screenshot_agent.png', fullPage: false });
  console.log('截图: 项目 Agent');

  // Open project workflows
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('项目流程') && b.offsetParent) b.click();
    });
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'screenshot_workflows.png', fullPage: false });
  console.log('截图: 项目流程');

  // Open knowledge center for comparison
  await page.evaluate(() => { document.querySelector('nav')?.scrollTo(0, 0); });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('知识中心') && b.offsetParent) b.click();
    });
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'screenshot_knowledge.png', fullPage: false });
  console.log('截图: 知识中心');

  console.log('\n5 张截图已保存到 tests/ 目录');
  console.log('请查看: screenshot_dashboard.png, screenshot_rules.png, screenshot_agent.png, screenshot_workflows.png, screenshot_knowledge.png');

  await browser.close();
})();