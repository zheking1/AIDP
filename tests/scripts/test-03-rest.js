const { chromium } = require('playwright');
const { login, openWorkspace, openTab, cleanup } = require('./helper');
const TS = Date.now();

async function waitForContent(pg, tabId) {
  await pg.waitForSelector(`#tab-content-${tabId} [x-data]`, { timeout: 10000 });
}

async function testCrud(pg, cfg) {
  const jsErrors = [];
  pg.removeAllListeners('pageerror');
  pg.on('pageerror', err => jsErrors.push(err.message));

  console.log(`--- ${cfg.name} ---`);
  await openTab(pg, cfg.tabId, cfg.name, cfg.icon, cfg.url);
  await waitForContent(pg, cfg.tabId);

  await pg.locator(`#tab-content-${cfg.tabId} button:has-text("${cfg.createBtnText}")`).first().click();
  await pg.waitForTimeout(1500);

  const modalOpen = await pg.evaluate((sel) => {
    var d = Alpine.$data(document.querySelector(sel));
    return d.showCreateModal || d.showCreate || false;
  }, cfg.componentSel);
  console.log(`  点击"${cfg.createBtnText}" → 弹窗: ${modalOpen ? 'PASS' : 'FAIL'}`);

  if (!modalOpen) {
    console.log(`  JS错误: ${jsErrors.length === 0 ? 'PASS' : jsErrors.join('; ')}`);
    return { page: cfg.name, pass: false };
  }

  await pg.evaluate(({sel, code}) => {
    var d = Alpine.$data(document.querySelector(sel));
    eval(code);
  }, {sel: cfg.componentSel, code: cfg.formSetup + ';' + cfg.createFn + '()'});
  await pg.waitForTimeout(3000);

  const created = await pg.evaluate(({sel, code}) => {
    var d = Alpine.$data(document.querySelector(sel));
    return eval(code);
  }, {sel: cfg.componentSel, code: cfg.verifyCode});
  console.log(`  创建 → 数据可见: ${created ? 'PASS' : 'FAIL'}`);

  if (created && cfg.cleanupCode) {
    await pg.evaluate(({sel, code}) => {
      var d = Alpine.$data(document.querySelector(sel));
      eval(code);
    }, {sel: cfg.componentSel, code: cfg.cleanupCode});
  }

  console.log(`  JS错误: ${jsErrors.length === 0 ? 'PASS' : jsErrors.join('; ')}`);
  return { page: cfg.name, pass: modalOpen && created && jsErrors.length === 0 };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();

  await login(pg);
  await openWorkspace(pg);
  console.log('=== 记忆中心 + 开发工具 + 项目专区 + 系统管理 测试 ===\n');

  const results = [];

  // ===== 记忆中心 =====
  results.push(await testCrud(pg, {
    tabId: 'mem', name: '记忆列表', icon: 'fa-list', url: '/memory/memories',
    componentSel: '[x-data^="memoriesPage"]',
    createBtnText: '新建记忆',
    formSetup: `d.showCreateModal=true;d.newMemory={title:'Mem-${TS}',content:'测试记忆',category:'experience',importance:5,tagsInput:''}`,
    createFn: 'd.createMemory',
    verifyCode: `d.memories.some(m=>m.title.includes('Mem-'))`,
    cleanupCode: `var m=d.memories.find(m=>m.title.includes('Mem-'));if(m)fetch('/api/memory/'+m.id,{method:'DELETE'})`,
  }));

  // 记忆图谱 (只读)
  console.log('\n--- 记忆图谱 ---');
  await openTab(pg, 'mgraph', '记忆图谱', 'fa-share-2', '/memory/graph');
  await waitForContent(pg, 'mgraph');
  const graphLoaded = await pg.evaluate(() => {
    var el = document.querySelector('[x-data="memoryGraphPage()"]');
    return !!el;
  });
  console.log(`  T1+T2: ${graphLoaded ? 'PASS' : 'FAIL'}`);
  results.push({ page: '记忆图谱', pass: graphLoaded });

  // 记忆检索 (只读搜索)
  console.log('\n--- 记忆检索 ---');
  await openTab(pg, 'msearch', '记忆检索', 'fa-search', '/memory/search');
  await waitForContent(pg, 'msearch');
  const searchLoaded = await pg.evaluate(() => {
    var el = document.querySelector('[x-data^="memoriesPage"]');
    return !!el;
  });
  console.log(`  T1+T2: ${searchLoaded ? 'PASS' : 'FAIL'}`);
  results.push({ page: '记忆检索', pass: searchLoaded });

  // ===== 开发工具 =====
  console.log('\n--- 代码沙箱 ---');
  await openTab(pg, 'sandbox', '代码沙箱', 'fa-terminal', '/sandbox');
  await waitForContent(pg, 'sandbox');
  const sandboxLoaded = await pg.evaluate(() => !!document.querySelector('[x-data="sandboxPage()"]'));
  console.log(`  T1+T2: ${sandboxLoaded ? 'PASS' : 'FAIL'}`);
  results.push({ page: '代码沙箱', pass: sandboxLoaded });

  console.log('\n--- 质量检查 ---');
  await openTab(pg, 'quality', '质量检查', 'fa-check-circle', '/quality');
  await waitForContent(pg, 'quality');
  const qualityLoaded = await pg.evaluate(() => !!document.querySelector('[x-data="qualityPage()"]'));
  console.log(`  T1+T2: ${qualityLoaded ? 'PASS' : 'FAIL'}`);
  results.push({ page: '质量检查', pass: qualityLoaded });

  // ===== 项目专区 (需先创建项目) =====
  console.log('\n--- 项目专区 ---');
  // 创建测试项目
  const projResp = await pg.evaluate(async () => {
    const r = await fetch('/api/projects?name=TestProject-' + Date.now() + '&description=test', { method: 'POST' });
    return r.ok ? await r.json() : null;
  });
  if (projResp?.id) {
    const pid = projResp.id;
    console.log(`  创建项目: PASS (id=${pid})`);

    // 项目仪表盘
    await openTab(pg, 'pdash', '项目仪表盘', 'fa-bar-chart-2', `/project/${pid}/dashboard`);
    await waitForContent(pg, 'pdash');
    const dashLoaded = await pg.evaluate(() => !!document.querySelector('[x-data^="projectDashboard"]'));
    console.log(`  项目仪表盘: ${dashLoaded ? 'PASS' : 'FAIL'}`);
    results.push({ page: '项目仪表盘', pass: dashLoaded });

    // 项目知识
    await openTab(pg, 'pkb', '项目知识', 'fa-book', `/project/${pid}/knowledge/documents`);
    await waitForContent(pg, 'pkb');
    const pkbLoaded = await pg.evaluate(() => !!document.querySelector('#tab-content-pkb [x-data]'));
    console.log(`  项目知识: ${pkbLoaded ? 'PASS' : 'FAIL'}`);
    results.push({ page: '项目知识', pass: pkbLoaded });

    // 项目设置
    await openTab(pg, 'pset', '项目设置', 'fa-settings', `/project/${pid}/settings/general`);
    await waitForContent(pg, 'pset');
    const psetLoaded = await pg.evaluate(() => !!document.querySelector('#tab-content-pset [x-data]'));
    console.log(`  项目设置: ${psetLoaded ? 'PASS' : 'FAIL'}`);
    results.push({ page: '项目设置', pass: psetLoaded });

    // 清理项目
    await pg.evaluate(async (id) => { await fetch('/api/projects/' + id, { method: 'DELETE' }); }, pid);
  } else {
    console.log('  创建项目: FAIL');
    results.push({ page: '项目专区', pass: false });
  }

  // ===== 系统管理 =====
  const adminPages = [
    { tabId: 'ausers', name: '用户管理', icon: 'fa-users', url: '/admin/users-frame', sel: '[x-data="usersManager()"]' },
    { tabId: 'aprojects', name: '项目管理', icon: 'fa-folder', url: '/admin/projects', sel: '[x-data="adminProjectsPage()"]' },
    { tabId: 'ainstr', name: '指令管理', icon: 'fa-book', url: '/admin/instructions', sel: '[x-data="adminInstructionsPage()"]' },
    { tabId: 'amodels', name: '模型管理', icon: 'fa-microchip', url: '/admin/models-frame', sel: '[x-data="modelsManager()"]' },
    { tabId: 'atools', name: '工具注册', icon: 'fa-plug', url: '/admin/tools', sel: '[x-data="adminToolsPage()"]' },
    { tabId: 'anas', name: 'NAS文件', icon: 'fa-database', url: '/admin/nas', sel: '[x-data="adminNasPage()"]' },
    { tabId: 'aconfigs', name: '环境配置', icon: 'fa-cog', url: '/admin/configs', sel: '[x-data="adminConfigsPage()"]' },
    { tabId: 'aaudit', name: '审计日志', icon: 'fa-file-text', url: '/admin/audit-logs', sel: '[x-data="auditLogsPage()"]' },
    { tabId: 'asettings', name: '系统设置', icon: 'fa-cog', url: '/admin/settings-frame', sel: '[x-data="settingsManager()"]' },
  ];

  for (const p of adminPages) {
    console.log(`\n--- ${p.name} ---`);
    await openTab(pg, p.tabId, p.name, p.icon, p.url);
    try {
      await waitForContent(pg, p.tabId);
      const loaded = await pg.evaluate((sel) => !!document.querySelector(sel), p.sel);
      console.log(`  T1+T2: ${loaded ? 'PASS' : 'FAIL'}`);
      results.push({ page: p.name, pass: loaded });
    } catch (e) {
      console.log(`  SKIP: ${e.message.substring(0, 60)}`);
      results.push({ page: p.name, pass: false });
    }
  }

  // ===== Summary =====
  console.log('\n=== SUMMARY ===');
  const passed = results.filter(r => r.pass).length;
  console.log(`${passed}/${results.length} passed\n`);
  results.forEach(r => console.log(`  ${r.pass ? 'PASS' : 'FAIL'} ${r.page}`));

  await browser.close();
})();
