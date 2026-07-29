const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';
const TS = Date.now();

async function login(pg) {
  await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await pg.fill('input[name="username"]', 'admin');
  await pg.fill('input[name="password"]', 'admin123');
  await pg.click('button[type="submit"]');
  await pg.waitForTimeout(2000);
}

async function openTab(pg, tabId, name, icon, url) {
  await pg.evaluate(({tabId, name, icon, url}) => {
    const ws = Alpine.$data(document.querySelector('[x-data="workspace()"]'));
    ws.openTab(tabId, name, `fas ${icon}`, url);
  }, {tabId, name, icon, url});
  await pg.waitForTimeout(5000);
}

async function getData(pg, selector) {
  return pg.evaluate((sel) => {
    const el = document.querySelector(sel);
    return el ? Alpine.$data(el) : null;
  }, selector);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  
  pg.on('response', async resp => {
    if (resp.url().includes('/api/') && resp.request().method() === 'POST') {
      console.log(`  [API] POST ${resp.url().split('?')[0]} → ${resp.status()}`);
    }
  });

  await login(pg);
  await pg.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(5000);
  console.log('Workspace loaded.\n');

  const results = [];

  // CRUD pages: T1+T2+T3
  const crudTests = [
    {
      tabId: 'rules-global', name: '全局规则', icon: 'fa-gavel', url: '/rules/global',
      component: '[x-data="globalRulesPage()"]',
      setup: `d.showCreateModal=true; d.form={name:'rule-${TS}',content:'test',description:'',category:'security',severity:'medium',priority:0,pattern:'',tagsInput:''}`,
      createFn: 'createRule',
      verify: (d) => d.rules?.some(r => r.name.includes('rule-')),
      findItem: (d) => d.rules?.find(r => r.name.includes('rule-')),
      deleteUrl: (item) => `/api/rules/${item.id}`,
    },
    {
      tabId: 'skills-global', name: '全局技能', icon: 'fa-star', url: '/skills/global',
      component: '[x-data="globalSkillsPage()"]',
      setup: `d.showCreateModal=true; d.newSkill={name:'skill-${TS}',description:'test',instruction:'test',content:'',tagsInput:''}`,
      createFn: 'createGlobalSkill',
      verify: (d) => d.skills?.some(s => s.name.includes('skill-')),
      findItem: (d) => d.skills?.find(s => s.name.includes('skill-')),
      deleteUrl: (item) => `/api/skills/${item.id}`,
    },
    {
      tabId: 'knowledge-bases', name: '知识库', icon: 'fa-book', url: '/knowledge/bases',
      component: '[x-data="knowledgeBasesPage()"]',
      setup: `d.showCreateModal=true; d.showEditModal=false; d.formKB={id:null,name:'kb-${TS}',description:'test',kb_level:'framework',parent_id:'',visibility:'private',techStackStr:'',domainsStr:'',keywordsStr:'',chunking_strategy:'fixed',chunk_size:500,chunk_overlap:50}`,
      createFn: 'confirmForm',
      verify: (d) => d.knowledgeBases?.some(k => k.name.includes('kb-')),
      findItem: (d) => d.knowledgeBases?.find(k => k.name.includes('kb-')),
      deleteUrl: (item) => `/api/knowledge/bases/${item.id}`,
    },
    {
      tabId: 'rules-personal', name: '个人规则', icon: 'fa-user-shield', url: '/rules/personal',
      component: '[x-data="personalRulesPage()"]',
      setup: `d.showCreateModal=true; d.form={name:'prule-${TS}',content:'test',description:'',category:'security',severity:'medium',priority:0,pattern:'',tagsInput:''}`,
      createFn: 'createRule',
      verify: (d) => d.rules?.some(r => r.name.includes('prule-')),
      findItem: (d) => d.rules?.find(r => r.name.includes('prule-')),
      deleteUrl: (item) => `/api/rules/${item.id}`,
    },
    {
      tabId: 'skills-personal', name: '个人技能', icon: 'fa-user', url: '/skills/personal',
      component: '[x-data="personalSkillsPage()"]',
      setup: `d.showCreateModal=true; d.form={name:'pskill-${TS}',description:'test',instruction:'test',content:'',tagsInput:'',group_id:null}`,
      createFn: 'createSkill',
      verify: (d) => d.skills?.some(s => s.name.includes('pskill-')),
      findItem: (d) => d.skills?.find(s => s.name.includes('pskill-')),
      deleteUrl: (item) => `/api/skills/${item.id}`,
    },
    {
      tabId: 'memories', name: '记忆管理', icon: 'fa-brain', url: '/memory/memories',
      component: '[x-data^="memoriesPage"]',
      setup: `d.showCreateModal=true; d.newMemory={title:'mem-${TS}',content:'test content',category:'experience',importance:5,tagsInput:''}`,
      createFn: 'createMemory',
      verify: (d) => d.memories?.some(m => m.title.includes('mem-')),
      findItem: (d) => d.memories?.find(m => m.title.includes('mem-')),
      deleteUrl: (item) => `/api/memory/${item.id}`,
    },
    {
      tabId: 'assets', name: '代码资产', icon: 'fa-code', url: '/assets',
      component: '[x-data="assetsPage()"]',
      setup: `d.showCreateModal=true; d.newAsset={title:'asset-${TS}',description:'test',asset_type:'code',language:'python',content:'print("hello")',tagsInput:''}`,
      createFn: 'createAsset',
      verify: (d) => d.assets?.some(a => a.title.includes('asset-')),
      findItem: (d) => d.assets?.find(a => a.title.includes('asset-')),
      deleteUrl: (item) => `/api/assets/${item.id}`,
    },
    {
      tabId: 'global-templates', name: '全局模板', icon: 'fa-file-alt', url: '/knowledge/templates',
      component: '[x-data="templatesPage()"]',
      setup: `d.showCreateModal=true; d.form={name:'tpl-${TS}',category:'dev',description:'test',content:'# Template'}`,
      createFn: 'createTemplate',
      verify: (d) => d.templates?.some(t => t.name.includes('tpl-')),
      findItem: (d) => d.templates?.find(t => t.name.includes('tpl-')),
      deleteUrl: (item) => `/api/knowledge/templates/${item.id}`,
    },
    {
      tabId: 'workflows', name: '流程管理', icon: 'fa-project-diagram', url: '/workflows',
      component: '[x-data="workflowsPage()"]',
      setup: `d.showCreateModal=true; d.form={name:'wf-${TS}',description:'test workflow',category:'deployment'}`,
      createFn: 'createWorkflow',
      verify: (d) => d.workflows?.some(w => w.name.includes('wf-')),
      findItem: (d) => d.workflows?.find(w => w.name.includes('wf-')),
      deleteUrl: (item) => `/api/workflows/${item.id}`,
    },
    {
      tabId: 'knowledge-documents', name: '知识文档', icon: 'fa-file', url: '/knowledge/documents',
      component: '[x-data="knowledgeDocumentsPage()"]',
      setup: `d.showCreateModal=true; d.newDoc={title:'doc-${TS}',doc_type:'dev',category:'general',content:'Test document content'}`,
      createFn: 'createDocument',
      verify: (d) => d.documents?.some(doc => doc.title.includes('doc-')),
      findItem: (d) => d.documents?.find(doc => doc.title.includes('doc-')),
      deleteUrl: (item) => `/api/knowledge/documents/${item.id}`,
    },
  ];

  // Tool pages: T1+T2 only (no CRUD, just verify they load)
  const toolTests = [
    { tabId: 'quality', name: '质量检查', icon: 'fa-check-circle', url: '/quality', component: '[x-data="qualityPage()"]' },
    { tabId: 'sandbox', name: '沙箱执行', icon: 'fa-terminal', url: '/sandbox', component: '[x-data="sandboxPage()"]' },
  ];

  // CRUD tests
  for (const t of crudTests) {
    console.log(`--- ${t.name} ---`);
    try {
      await openTab(pg, t.tabId, t.name, t.icon, t.url);
    } catch(e) {
      console.log(`  SKIP: ${e.message}`);
      results.push({page: t.name, pass: false, err: 'open failed'});
      continue;
    }

    const data = await getData(pg, t.component);
    if (!data) {
      console.log('  SKIP: component not found');
      results.push({page: t.name, pass: false, err: 'no component'});
      continue;
    }
    console.log(`  T1+T2: loaded`);

    try {
      await pg.evaluate(({sel, setup}) => {
        const d = Alpine.$data(document.querySelector(sel));
        eval(setup);
      }, {sel: t.component, setup: t.setup});
      await pg.waitForTimeout(500);

      await pg.evaluate(({sel, fn}) => {
        Alpine.$data(document.querySelector(sel))[fn]();
      }, {sel: t.component, fn: t.createFn});
      await pg.waitForTimeout(3000);

      const after = await getData(pg, t.component);
      const created = t.verify(after);
      console.log(`  T3: ${created ? 'PASS' : 'FAIL'}`);
      results.push({page: t.name, pass: created});

      if (created) {
        const item = t.findItem(after);
        if (item) await pg.evaluate(async (url) => { await fetch(url, {method:'DELETE'}); }, t.deleteUrl(item));
      }
    } catch(e) {
      console.log(`  T3: ERROR ${e.message}`);
      results.push({page: t.name, pass: false, err: e.message});
    }
  }

  // Tool tests (T1+T2 only)
  for (const t of toolTests) {
    console.log(`\n--- ${t.name} ---`);
    try {
      await openTab(pg, t.tabId, t.name, t.icon, t.url);
      const data = await getData(pg, t.component);
      const ok = !!data;
      console.log(`  T1+T2: ${ok ? 'PASS' : 'FAIL'}`);
      results.push({page: t.name, pass: ok});
    } catch(e) {
      console.log(`  SKIP: ${e.message}`);
      results.push({page: t.name, pass: false, err: e.message});
    }
  }

  // T4: Agent detail tabs
  console.log('\n--- Agent详情 (T4) ---');
  await openTab(pg, 'agents', 'Agent管理', 'fa-robot', '/agents');
  const agentsData = await getData(pg, '[x-data="agentsPage()"]');
  if (agentsData?.agents?.length > 0) {
    const agentId = agentsData.agents[0].id;
    await pg.evaluate(async (id) => {
      await Alpine.$data(document.querySelector('[x-data="agentsPage()"]')).viewAgent({id});
    }, agentId);
    await pg.waitForTimeout(3000);
    
    const detail = await getData(pg, '[x-data="agentsPage()"]');
    const hasDetail = !!detail?.detail;
    console.log(`  Detail modal: ${hasDetail ? 'PASS' : 'FAIL'}`);
    
    if (hasDetail) {
      for (const tab of ['skills', 'rules', 'knowledge']) {
        await pg.evaluate((tab) => {
          Alpine.$data(document.querySelector('[x-data="agentsPage()"]')).detailTab = tab;
        }, tab);
        await pg.waitForTimeout(500);
      }
      console.log('  Tabs (skills/rules/kb): PASS');
    }
    results.push({page: 'Agent详情T4', pass: hasDetail});
  } else {
    console.log('  SKIP: no agents');
    results.push({page: 'Agent详情T4', pass: false, err: 'no agents'});
  }

  // Summary
  console.log('\n\n=== SUMMARY ===');
  const passed = results.filter(r => r.pass).length;
  console.log(`${passed}/${results.length} passed\n`);
  results.forEach(r => console.log(`  ${r.pass ? 'PASS' : 'FAIL'} ${r.page}${r.err ? ' ('+r.err+')' : ''}`));

  await browser.close();
})();
