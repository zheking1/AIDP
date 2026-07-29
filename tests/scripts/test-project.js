const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  let passed = 0, failed = 0, errors = [];
  page.on('pageerror', e => errors.push({ type: 'pageerror', msg: e.message.substring(0,100) }));
  page.on('console', msg => { if (msg.type() === 'error') errors.push({ type: 'console', msg: msg.text().substring(0,100) }); });
  page.on('response', r => { if (r.status() >= 400) errors.push({ type: 'http', msg: r.status() + ' ' + r.url().substring(0,80) }); });

  const test = async (name, fn) => {
    try { await fn(); passed++; process.stdout.write('.'); }
    catch(e) { failed++; process.stdout.write('X'); console.log(`\n❌ ${name}: ${e.message.substring(0,150)}`); }
  };

  const clearErrors = () => { errors = []; };
  const reportErrors = (label) => {
    if (errors.length > 0) {
      console.log(`  ⚠ ${errors.length} errors:`, errors.slice(0,3).map(e => e.msg).join('; '));
    }
  };

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);
  clearErrors();

  // First, create a project if none exists
  console.log('\n=== 准备项目 ===');
  await test('API 创建测试项目', async () => {
    const r = await page.evaluate(async () => {
      const res = await fetch('/api/projects', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({name:'E2E测试项目', description:'用于E2E测试', tech_stack:['Python']})
      });
      return res.ok;
    });
    if (!r) throw new Error('创建项目失败');
  });

  // Reload workspace to get fresh menu
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  clearErrors();

  // Select project from sidebar
  console.log('\n=== 选择项目 ===');
  await test('选择项目下拉框', async () => {
    const select = await page.$('select');
    if (!select) throw new Error('无项目选择器');
    // Select the E2E test project
    await select.selectOption('1');
    await page.waitForTimeout(2000);
    // Check project section appears
    const body = await page.textContent('body');
    if (!body.includes('E2E测试项目') && !body.includes('当前项目')) {
      // Try clicking the project link
      await page.evaluate(() => {
        document.querySelectorAll('a, button').forEach(el => {
          if (el.textContent.includes('E2E测试项目') || el.textContent.includes('项目仪表盘')) el.click();
        });
      });
      await page.waitForTimeout(2000);
    }
  });

  // Navigate to project dashboard
  console.log('\n=== 项目仪表盘 ===');
  clearErrors();
  await test('页面加载', async () => {
    await page.goto(BASE + '/project/1/dashboard?partial=1', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    const body = await page.textContent('body');
    if (!body.includes('项目仪表盘') && !body.includes('概览')) throw new Error('页面未加载');
  });
  reportErrors('仪表盘');

  // Check layout
  await test('布局一致性', async () => {
    const layout = await page.evaluate(() => {
      const divs = document.querySelectorAll('body > div > div');
      const first = divs[0];
      if (!first) return 'no divs';
      const style = getComputedStyle(first);
      return {
        display: style.display,
        justifyContent: style.justifyContent,
        paddingTop: style.paddingTop,
        paddingBottom: style.paddingBottom,
        borderBottom: style.borderBottomWidth
      };
    });
    if (layout.display !== 'flex' || layout.justifyContent !== 'space-between') {
      throw new Error('Header 不是 flex space-between: ' + JSON.stringify(layout));
    }
  });

  // Navigate to project settings
  console.log('\n=== 项目设置 ===');
  for (const route of ['general', 'instructions', 'members']) {
    clearErrors();
    await test('设置-' + route, async () => {
      await page.goto(BASE + '/project/1/settings/' + route + '?partial=1', { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);
      const body = await page.textContent('body');
      if (body.includes('404') || body.includes('Not Found')) throw new Error('404');
    });
    reportErrors(route);
  }

  // Navigate via workspace sidebar
  console.log('\n=== 侧边栏导航 ===');
  clearErrors();
  await test('通过 workspace 加载仪表盘', async () => {
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    // Click project section dashboard link
    await page.evaluate(() => {
      document.querySelectorAll('button, a').forEach(el => {
        if (el.textContent.includes('项目仪表盘')) { el.click(); return; }
      });
    });
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    if (!body.includes('仪表盘') && !body.includes('概览')) throw new Error('页面未加载');
  });
  reportErrors('workspace 导航');

  const total = passed + failed;
  const errTotal = errors.length;
  console.log(`\n\n${'='.repeat(40)}`);
  console.log(`共 ${total} 项: ${passed} 通过, ${failed} 失败`);
  console.log(`控制台错误: ${errTotal} 个`);
  console.log(`${'='.repeat(40)}`);
  if (failed > 0) process.exit(1);
  await browser.close();
})();