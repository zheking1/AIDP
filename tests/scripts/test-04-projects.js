const { chromium } = require('playwright');
const { login, openWorkspace, openTab, cleanup } = require('./helper');
const TS = Date.now();

async function waitForContent(pg, tabId) {
  await pg.waitForSelector(`#tab-content-${tabId} [x-data]`, { timeout: 10000 });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  const jsErrors = [];
  pg.on('pageerror', err => jsErrors.push(err.message));

  await login(pg);
  await openWorkspace(pg);
  console.log('=== 项目测试 ===\n');

  const results = [];

  // ===== 1. 项目列表 =====
  console.log('--- 项目列表 ---');
  await openTab(pg, 'projects', '项目列表', 'fa-folder', '/projects');
  await waitForContent(pg, 'projects');
  jsErrors.length = 0;

  // T1+T2: 列表加载
  const projCount = await pg.evaluate(() => {
    var d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return d.projects?.length ?? -1;
  });
  console.log(`  列表加载: ${projCount >= 0 ? 'PASS (' + projCount + ')' : 'FAIL'}`);

  // T3-创建: 点击"新建项目"
  await pg.locator('#tab-content-projects button:has-text("创建项目")').first().click();
  await pg.waitForTimeout(1500);
  const modalOpen = await pg.evaluate(() => {
    var d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
    return d.showCreateModal;
  });
  console.log(`  新建项目 → 弹窗: ${modalOpen ? 'PASS' : 'FAIL'}`);

  if (modalOpen) {
    // JS 填写表单 + 提交
    await pg.evaluate(() => {
      var d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
      d.newProject = { name: 'TestProj-' + Date.now(), description: '自动化测试项目', type: 'python', nas_path: '' };
      d.createProject();
    });
    await pg.waitForTimeout(3000);

    const created = await pg.evaluate(() => {
      var d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
      return d.projects?.some(p => p.name.includes('TestProj-'));
    });
    console.log(`  创建 → 数据可见: ${created ? 'PASS' : 'FAIL'}`);

    // 清理
    if (created) {
      await pg.evaluate(() => {
        var d = Alpine.$data(document.querySelector('[x-data="projectsPage()"]'));
        var p = d.projects.find(p => p.name.includes('TestProj-'));
        if (p) fetch('/api/projects/' + p.id, { method: 'DELETE' });
      });
    }
  }

  console.log(`  JS错误: ${jsErrors.length === 0 ? 'PASS' : jsErrors.join('; ')}`);
  results.push({ page: '项目列表', pass: projCount >= 0 && jsErrors.length === 0 });

  // ===== 2. 项目管理 (admin) =====
  console.log('\n--- 项目管理 ---');
  jsErrors.length = 0;
  await openTab(pg, 'aprojects', '项目管理', 'fa-folder', '/admin/projects');
  await waitForContent(pg, 'aprojects');

  const adminProjCount = await pg.evaluate(() => {
    var d = Alpine.$data(document.querySelector('[x-data="adminProjectsPage()"]'));
    return d.projects?.length ?? -1;
  });
  console.log(`  列表加载: ${adminProjCount >= 0 ? 'PASS (' + adminProjCount + ')' : 'FAIL'}`);
  console.log(`  JS错误: ${jsErrors.length === 0 ? 'PASS' : jsErrors.join('; ')}`);
  results.push({ page: '项目管理', pass: adminProjCount >= 0 && jsErrors.length === 0 });

  // ===== Summary =====
  console.log('\n=== SUMMARY ===');
  const passed = results.filter(r => r.pass).length;
  console.log(`${passed}/${results.length} passed\n`);
  results.forEach(r => console.log(`  ${r.pass ? 'PASS' : 'FAIL'} ${r.page}`));

  await browser.close();
})();
