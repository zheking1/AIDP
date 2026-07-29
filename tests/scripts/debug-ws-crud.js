const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';

async function login(pg) { await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' }); await pg.fill('input[name="username"]', 'admin'); await pg.fill('input[name="password"]', 'admin123'); await pg.click('button[type="submit"]'); await pg.waitForTimeout(2000); }

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  
  pg.on('console', msg => { if (msg.type() === 'error') console.log(`[ERR] ${msg.text()}`); });
  pg.on('response', async resp => {
    if (resp.url().includes('/api/') && !resp.url().includes('stats') && !resp.url().includes('menu') && !resp.url().includes('projects') && !resp.url().includes('templates')) {
      console.log(`[API] ${resp.request().method()} ${resp.url().split('?')[0]} → ${resp.status()}`);
    }
  });

  await login(pg);
  console.log('=== 通过 workspace 测试全局规则 CRUD ===');
  await pg.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(5000);

  // 通过 workspace.openTab 打开全局规则页
  await pg.evaluate(() => {
    const ws = Alpine.$data(document.querySelector('[x-data="workspace()"]'));
    ws.openTab('rules-global', '全局规则', 'fas fa-gavel', '/rules/global');
  });
  await pg.waitForTimeout(5000);

  // 检查规则页是否加载
  const pageState = await pg.evaluate(() => {
    const ruleEl = document.querySelector('[x-data="globalRulesPage()"]');
    if (!ruleEl) return { found: false };
    const data = Alpine.$data(ruleEl);
    return { found: true, rules: data.rules?.length, loading: data.loading };
  });
  console.log('Page state:', pageState);

  if (pageState.found) {
    // 填写表单
    await pg.evaluate(() => {
      const ruleEl = document.querySelector('[x-data="globalRulesPage()"]');
      const data = Alpine.$data(ruleEl);
      data.showCreateModal = true;
      data.form.name = '测试规则-' + Date.now();
      data.form.content = '测试规则内容';
      data.form.description = '测试描述';
    });
    await pg.waitForTimeout(1000);

    // 提交
    console.log('Creating rule...');
    await pg.evaluate(() => {
      const ruleEl = document.querySelector('[x-data="globalRulesPage()"]');
      const data = Alpine.$data(ruleEl);
      data.createRule();
    });
    await pg.waitForTimeout(3000);

    // 验证
    const result = await pg.evaluate(() => {
      const ruleEl = document.querySelector('[x-data="globalRulesPage()"]');
      const data = Alpine.$data(ruleEl);
      return { modal: data.showCreateModal, count: data.rules?.length };
    });
    console.log('After create:', result);
  }

  await browser.close();
})();
