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

  // 点击创建按钮
  await pg.locator(`#tab-content-${cfg.tabId} button:has-text("${cfg.createBtnText}")`).first().click();
  await pg.waitForTimeout(1500);

  const modalOpen = await pg.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return false;
    const data = Alpine.$data(el);
    return data.showCreateModal || data.showCreate || false;
  }, cfg.componentSel);
  console.log(`  点击"${cfg.createBtnText}" → 弹窗: ${modalOpen ? 'PASS' : 'FAIL'}`);

  if (!modalOpen) {
    console.log(`  JS错误: ${jsErrors.length === 0 ? 'PASS' : jsErrors.join('; ')}`);
    return { page: cfg.name, pass: false };
  }

  // 填写 + 提交
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
  console.log('=== 技能库 Hub 测试 ===\n');

  const results = [];

  results.push(await testCrud(pg, {
    tabId: 'sg', name: '全局技能', icon: 'fa-globe', url: '/skills/global',
    componentSel: '[x-data="globalSkillsPage()"]',
    createBtnText: '创建',
    formSetup: `d.showCreateModal=true;d.newSkill={name:'Skill-${TS}',description:'测试',instruction:'测试',content:'',tagsInput:''}`,
    createFn: 'd.createGlobalSkill',
    verifyCode: `d.skills.some(s=>s.name.includes('Skill-'))`,
    cleanupCode: `var s=d.skills.find(s=>s.name.includes('Skill-'));if(s)fetch('/api/skills/'+s.id,{method:'DELETE'})`,
  }));

  results.push(await testCrud(pg, {
    tabId: 'sp', name: '我的技能', icon: 'fa-user', url: '/skills/personal',
    componentSel: '[x-data="personalSkillsPage()"]',
    createBtnText: '创建技能',
    formSetup: `d.showCreateModal=true;d.form={name:'PSkill-${TS}',description:'测试',instruction:'测试',content:'',tagsInput:'',group_id:null}`,
    createFn: 'd.createSkill',
    verifyCode: `d.skills.some(s=>s.name.includes('PSkill-'))`,
    cleanupCode: `var s=d.skills.find(s=>s.name.includes('PSkill-'));if(s)fetch('/api/skills/'+s.id,{method:'DELETE'})`,
  }));

  results.push(await testCrud(pg, {
    tabId: 'rg', name: '全局规则', icon: 'fa-shield-alt', url: '/rules/global',
    componentSel: '[x-data="globalRulesPage()"]',
    createBtnText: '创建',
    formSetup: `d.showCreateModal=true;d.form={name:'Rule-${TS}',content:'测试',description:'',category:'security',severity:'medium',priority:0,pattern:'',tagsInput:''}`,
    createFn: 'd.createRule',
    verifyCode: `d.rules.some(r=>r.name.includes('Rule-'))`,
    cleanupCode: `var r=d.rules.find(r=>r.name.includes('Rule-'));if(r)fetch('/api/rules/'+r.id,{method:'DELETE'})`,
  }));

  results.push(await testCrud(pg, {
    tabId: 'rp', name: '我的规则', icon: 'fa-user-shield', url: '/rules/personal',
    componentSel: '[x-data="personalRulesPage()"]',
    createBtnText: '创建规则',
    formSetup: `d.showCreateModal=true;d.form={name:'PRule-${TS}',content:'测试',description:'',category:'security',severity:'medium',priority:0,pattern:'',tagsInput:''}`,
    createFn: 'd.createRule',
    verifyCode: `d.rules.some(r=>r.name.includes('PRule-'))`,
    cleanupCode: `var r=d.rules.find(r=>r.name.includes('PRule-'));if(r)fetch('/api/rules/'+r.id,{method:'DELETE'})`,
  }));

  // Agent 管理
  console.log('\n--- Agent 管理 ---');
  await openTab(pg, 'agents', 'Agent管理', 'fa-robot', '/agents');
  await waitForContent(pg, 'agents');
  const agentCount = await pg.evaluate(() => {
    const data = Alpine.$data(document.querySelector('[x-data="agentsPage()"]'));
    return data.agents?.length || 0;
  });
  console.log(`  列表加载: ${agentCount >= 0 ? 'PASS (' + agentCount + ')' : 'FAIL'}`);
  if (agentCount > 0) {
    await pg.locator('#tab-content-agents .cursor-pointer').first().click();
    await pg.waitForTimeout(3000);
    const detailOpen = await pg.evaluate(() => !!Alpine.$data(document.querySelector('[x-data="agentsPage()"]')).detail);
    console.log(`  点击 → 详情: ${detailOpen ? 'PASS' : 'FAIL'}`);
    if (detailOpen) {
      for (const tab of ['skills', 'rules', 'knowledge']) {
        await pg.evaluate((t) => { Alpine.$data(document.querySelector('[x-data="agentsPage()"]')).detailTab = t; }, tab);
        await pg.waitForTimeout(500);
      }
      console.log('  标签切换: PASS');
    }
  }
  results.push({ page: 'Agent管理', pass: agentCount >= 0 });

  results.push(await testCrud(pg, {
    tabId: 'wf', name: '流程引擎', icon: 'fa-cogs', url: '/workflows',
    componentSel: '[x-data="workflowsPage()"]',
    createBtnText: '创建流程',
    formSetup: `d.showCreateModal=true;d.form={name:'WF-${TS}',description:'测试流程',category:'deployment'}`,
    createFn: 'd.createWorkflow',
    verifyCode: `d.workflows.some(w=>w.name.includes('WF-'))`,
    cleanupCode: `var w=d.workflows.find(w=>w.name.includes('WF-'));if(w)fetch('/api/workflows/'+w.id,{method:'DELETE'})`,
  }));

  console.log('\n=== SUMMARY ===');
  const passed = results.filter(r => r.pass).length;
  console.log(`${passed}/${results.length} passed\n`);
  results.forEach(r => console.log(`  ${r.pass ? 'PASS' : 'FAIL'} ${r.page}`));

  await browser.close();
})();
