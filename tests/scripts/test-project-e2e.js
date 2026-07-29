const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  let passed = 0, failed = 0, errors = [];
  page.on('pageerror', e => errors.push({ type:'pageerror', msg: e.message.substring(0,100) }));
  page.on('console', msg => { if (msg.type() === 'error') errors.push({ type:'console', msg: msg.text().substring(0,100) }); });
  page.on('response', r => { if (r.status() >= 400) errors.push({ type:'http', msg: r.status()+' '+r.url().substring(0,80) }); });

  const test = async (name, fn) => {
    try { await fn(); passed++; process.stdout.write('.'); }
    catch(e) { failed++; process.stdout.write('X'); console.log('\n❌ ' + name + ': ' + e.message.substring(0,150)); }
  };

  const clear = () => { errors = []; };
  const report = (label) => {
    if (errors.length) console.log('  ⚠ ' + label + ': ' + errors.length + ' errors' + (errors[0] ? ' (' + errors[0].msg + ')' : ''));
  };

  // Login + create test project
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // Create project via API and store its ID
  let projectId = null;
  await test('API 创建测试项目', async () => {
    projectId = await page.evaluate(async () => {
      const r = await fetch('/api/projects', { method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name:'E2E测试项目', description:'E2E test', tech_stack:['Python']}) });
      if (r.ok) { const d = await r.json(); return d.id; }
      return null;
    });
    if (!projectId) throw new Error('创建项目失败');
  });

  // Navigate to workspace
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  clear();

  console.log('\n=== 项目页面测试 ===');
  await test('项目仪表盘 partial', async () => {
    const result = await page.evaluate(async (id) => {
      const r = await fetch('/project/' + id + '/dashboard?partial=1');
      const text = await r.text();
      return { status: r.status, start: text.substring(0, 100) };
    }, projectId);
    if (result.status !== 200 || !result.start.includes('projectDashboard')) throw new Error('dashboard partial 失败');
  });
  clear();
  await test('项目设置-general partial', async () => {
    const result = await page.evaluate(async (id) => {
      const r = await fetch('/project/' + id + '/settings/general?partial=1');
      const text = await r.text();
      return { status: r.status, start: text.substring(0, 100) };
    }, projectId);
    if (result.status !== 200 || !result.start.includes('flex items-center')) throw new Error('general partial 失败: ' + result.start.substring(0,50));
  });
  clear();
  await test('项目设置-instructions partial', async () => {
    const result = await page.evaluate(async (id) => {
      const r = await fetch('/project/' + id + '/settings/instructions?partial=1');
      const text = await r.text();
      return { status: r.status, start: text.substring(0, 100) };
    }, projectId);
    if (result.status !== 200 || !result.start.includes('flex items-center')) throw new Error('instructions partial 失败');
  });

  // Summary
  const total = passed + failed;
  console.log(`\n\n${'='.repeat(40)}`);
  console.log(`共 ${total} 项: ${passed} 通过, ${failed} 失败`);
  console.log(`总控制台错误: ${errors.length} 个`);
  if (errors.length) console.log('  最后错误:', errors[errors.length-1].msg);
  console.log(`${'='.repeat(40)}`);
  if (failed > 0) process.exit(1);
  await browser.close();
})();