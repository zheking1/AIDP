const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';
const TS = Date.now();

async function login(pg) {
  await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await pg.fill('input[name="username"]', 'admin');
  await pg.fill('input[name="password"]', 'admin123');
  await pg.click('button[type="submit"]');
  await pg.waitForTimeout(3000);
}

async function openTab(pg, tabId, name, icon, url) {
  await pg.evaluate(({tabId, name, icon, url}) => {
    const ws = Alpine.$data(document.querySelector('[x-data="workspace()"]'));
    ws.openTab(tabId, name, `fas ${icon}`, url);
  }, {tabId, name, icon, url});
  await pg.waitForTimeout(5000);
}

function record(results, name, type, pass, detail) {
  const status = pass ? 'PASS' : 'FAIL';
  console.log(`  [${status}] ${type}: ${name}${detail ? ' — ' + detail : ''}`);
  results.push({ name, type, status, detail: detail || '' });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();

  let errors = [];
  pg.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  pg.on('pageerror', e => { errors.push(e.message); });
  pg.on('response', async resp => {
    if (resp.url().includes('/api/') && resp.request().method() === 'POST' && resp.url().includes('/api/evolution')) {
      console.log(`  [API] POST ${resp.url().split('?')[0]} → ${resp.status()}`);
    }
  });

  await login(pg);
  await pg.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(5000);
  console.log('=== Workspace loaded ===\n');

  // Pre-seed test data via UI
  console.log('--- Seeding test data ---');
  // Create an asset
  await openTab(pg, 'assets-seed', '代码资产', 'fa-archive', '/assets');
  await pg.evaluate((ts) => {
    const el = document.querySelector('[x-data="assetsPage()"]');
    const d = Alpine.$data(el);
    d.showCreateModal = true;
    d.newAsset = { title: '种子资产-' + ts, description: 'E2E', asset_type: 'snippet', language: 'javascript', content: 'console.log(1)' };
  }, TS);
  await pg.waitForTimeout(500);
  await pg.evaluate(() => { const d = Alpine.$data(document.querySelector('[x-data="assetsPage()"]')); d.createAsset(); });
  await pg.waitForTimeout(3000);
  console.log('  Asset created.');

  // Create a memory
  await openTab(pg, 'memories-seed', '记忆管理', 'fa-brain', '/memory/memories');
  await pg.evaluate((ts) => {
    const el = document.querySelector('[x-data^="memoriesPage"]');
    const d = Alpine.$data(el);
    d.showCreateModal = true;
    d.newMemory = { title: '种子记忆-' + ts, content: '自动化测试记忆', category: 'test', memory_tier: 'semantic', confidence_score: 1.0 };
  }, TS);
  await pg.waitForTimeout(500);
  await pg.evaluate(() => { const d = Alpine.$data(document.querySelector('[x-data^="memoriesPage"]')); d.createMemory(); });
  await pg.waitForTimeout(3000);
  console.log('  Memory created.\n');

  const results = [];

  // ==================== T1: ADMIN EVOLUTION PAGE ====================
  console.log('--- T1: Admin Evolution Page ---');
  await openTab(pg, 'admin-evolution', '进化管理', 'fa-code-branch', '/admin/evolution');
  errors = [];
  await pg.waitForTimeout(2000);
  record(results, 'Admin Evolution', 'T1', errors.length === 0, errors.length ? errors[0] : 'No JS errors');

  // ==================== T2: EVOLUTION STATS ====================
  console.log('\n--- T2: Admin Evolution Stats ---');
  const evoStats = await pg.evaluate(() => {
    const el = document.querySelector('[x-data="adminEvolutionPage()"]');
    if (!el) return null;
    const d = Alpine.$data(el);
    return d && d.stats ? { total: d.stats.total, pending: d.stats.pending } : null;
  });
  record(results, 'Evolution Stats', 'T2', evoStats !== null, evoStats ? `total=${evoStats.total} pending=${evoStats.pending}` : 'Stats not found');

  // ==================== T3: EVOLUTION PROPOSE ====================
  console.log('\n--- T3: Evolution Propose ---');
  await openTab(pg, 'evolution', '进化提案', 'fa-lightbulb', '/evolution');
  errors = [];
  await pg.waitForTimeout(2000);

  let proposeDone = false;
  try {
    await pg.evaluate((ts) => {
      const el = document.querySelector('[x-data="evolutionPage()"]');
      if (!el) throw new Error('Component not found');
      const d = Alpine.$data(el);
      d.showProposeModal = true;
    }, TS);
    await pg.waitForTimeout(500);

    await pg.evaluate((ts) => {
      const el = document.querySelector('[x-data="evolutionPage()"]');
      const d = Alpine.$data(el);
      d.form.title = 'E2E测试提案-' + ts;
      d.form.description = '自动化测试创建的进化提案';
      d.form.affected_tools = 'memory,knowledge';
      d.form.changes_str = '{"test":true}';
      d.form.version = '0.1.0';
    }, TS);
    await pg.waitForTimeout(300);

    await pg.evaluate(() => {
      const el = document.querySelector('[x-data="evolutionPage()"]');
      Alpine.$data(el).propose();
    });
    await pg.waitForTimeout(3000);

    const hasItem = await pg.evaluate((ts) => {
      const el = document.querySelector('[x-data="evolutionPage()"]');
      const d = Alpine.$data(el);
      return d.versions?.some(v => v.title.includes('E2E'));
    }, TS);
    proposeDone = hasItem;
  } catch (e) { console.log('  Error:', e.message); }

  record(results, 'Evolution Propose', 'T3', proposeDone, proposeDone ? '提案创建成功' : 'Propose failed');
  record(results, 'Evolution Page Errors', 'T1', errors.length === 0, errors.join('; '));

  // ==================== T1: KNOWLEDGE GRAPH ====================
  console.log('\n--- T1: Knowledge Graph ---');
  await openTab(pg, 'knowledge-graph', '知识图谱', 'fa-project-diagram', '/knowledge/graph');
  errors = [];
  await pg.waitForTimeout(3000);
  record(results, 'Knowledge Graph', 'T1', errors.length === 0, errors.length ? errors[0] : 'No JS errors');

  // ==================== T2: KNOWLEDGE GRAPH RENDERING ====================
  console.log('\n--- T2: Knowledge Graph Rendering ---');
  const graphInfo = await pg.evaluate(() => {
    const el = document.querySelector('[x-data="knowledgeGraphPage()"]');
    if (!el) return null;
    const d = Alpine.$data(el);
    const svg = document.querySelector('#kgraph-container svg');
    return {
      stats: d.stats,
      hasSvg: !!svg,
      svgGroups: svg ? svg.querySelectorAll('g g').length : 0,
    };
  });
  record(results, 'Knowledge Graph Render', 'T2', graphInfo && graphInfo.stats.nodes > 0,
    graphInfo ? `nodes=${graphInfo.stats.nodes} links=${graphInfo.stats.links}` : 'Not rendered');

  // ==================== T3: KNOWLEDGE DOCUMENT CHUNKS ====================
  console.log('\n--- T3: Knowledge Document Chunks ---');
  await openTab(pg, 'knowledge-docs', '文档管理', 'fa-file-text', '/knowledge/documents');
  errors = [];
  await pg.waitForTimeout(3000);

  let chunksLoaded = false;
  try {
    const hasDocs = await pg.evaluate(() => {
      const el = document.querySelector('[x-data="knowledgeDocumentsPage()"]');
      if (!el) return false;
      const d = Alpine.$data(el);
      return d.documents && d.documents.length > 0;
    });

    if (hasDocs) {
      await pg.evaluate(() => {
        const el = document.querySelector('[x-data="knowledgeDocumentsPage()"]');
        const d = Alpine.$data(el);
        d.viewDocument(d.documents[0]);
      });
      await pg.waitForTimeout(2000);

      await pg.evaluate(() => {
        const el = document.querySelector('[x-data="knowledgeDocumentsPage()"]');
        Alpine.$data(el).viewTab = 'chunks';
      });
      await pg.waitForTimeout(500);

      await pg.evaluate(() => {
        const el = document.querySelector('[x-data="knowledgeDocumentsPage()"]');
        Alpine.$data(el).loadChunks();
      });
      await pg.waitForTimeout(2000);

      const chunkCount = await pg.evaluate(() => {
        const el = document.querySelector('[x-data="knowledgeDocumentsPage()"]');
        return Alpine.$data(el).chunkCount;
      });
      chunksLoaded = chunkCount > 0;
      record(results, 'Knowledge Chunks', 'T3', chunksLoaded, `chunks=${chunkCount}`);
    } else {
      record(results, 'Knowledge Chunks', 'T3', false, 'No documents to test chunks - create docs first');
    }
  } catch (e) { record(results, 'Knowledge Chunks', 'T3', false, e.message); }

  // ==================== T2: MEMORY TIMELINE ====================
  console.log('\n--- T2: Memory Timeline ---');
  await openTab(pg, 'memories', '记忆管理', 'fa-brain', '/memory/memories');
  errors = [];
  await pg.waitForTimeout(3000);

  try {
    await pg.evaluate(() => {
      const el = document.querySelector('[x-data^="memoriesPage"]');
      if (!el) throw new Error('Component not found');
      Alpine.$data(el).activeTab = 'timeline';
    });
    await pg.waitForTimeout(500);
  } catch (e) {}

  await pg.evaluate(() => {
    const el = document.querySelector('[x-data^="memoriesPage"]');
    Alpine.$data(el).loadTimeline();
  });
  await pg.waitForTimeout(3000);

  const timelineInfo = await pg.evaluate(() => {
    const el = document.querySelector('[x-data^="memoriesPage"]');
    const d = Alpine.$data(el);
    return { groups: d.timelineGroups?.length || 0, loading: d.timelineLoading };
  });
  record(results, 'Memory Timeline', 'T2', timelineInfo.groups > 0,
    `groups=${timelineInfo.groups} ${timelineInfo.loading ? '(loading)' : ''}`);
  record(results, 'Memory Page Errors', 'T1', errors.length === 0, errors.join('; '));

  // ==================== T3: MEMORY CONTEXT PACKAGE ====================
  console.log('\n--- T3: Memory Context Package ---');
  try {
    await pg.evaluate(() => {
      const el = document.querySelector('[x-data^="memoriesPage"]');
      Alpine.$data(el).activeTab = 'context';
    });
    await pg.waitForTimeout(500);

    await pg.evaluate(() => {
      const el = document.querySelector('[x-data^="memoriesPage"]');
      Alpine.$data(el).loadContextPackages();
    });
    await pg.waitForTimeout(2000);

    const pkgCount = await pg.evaluate(() => {
      const el = document.querySelector('[x-data^="memoriesPage"]');
      const d = Alpine.$data(el);
      return d.contextPackages?.length || 0;
    });
    record(results, 'Context Packages List', 'T3', true, `count=${pkgCount}`);
  } catch (e) { record(results, 'Context Packages', 'T3', false, e.message); }

  // ==================== T2: QUALITY STATS + TREND ====================
  console.log('\n--- T2: Quality Stats ---');
  await openTab(pg, 'quality', '质量检查', 'fa-check-circle', '/quality');
  errors = [];
  await pg.waitForTimeout(3000);

  const qStats = await pg.evaluate(() => {
    const el = document.querySelector('[x-data="qualityPage()"]');
    if (!el) return null;
    const d = Alpine.$data(el);
    return { total: d.stats?.total, withIssues: d.stats?.with_issues, trend: d.trend?.length };
  });
  record(results, 'Quality Stats', 'T2', qStats && qStats.total >= 0,
    qStats ? `total=${qStats.total} issues=${qStats.withIssues} trend=${qStats.trend}d` : 'Not loaded');
  record(results, 'Quality Errors', 'T1', errors.length === 0, errors.join('; '));

  // ==================== T2: ASSET DETAIL ====================
  console.log('\n--- T2: Asset Detail ---');
  await openTab(pg, 'assets', '代码资产', 'fa-archive', '/assets');
  errors = [];
  await pg.waitForTimeout(3000);

  const hasAssets = await pg.evaluate(() => {
    const el = document.querySelector('[x-data="assetsPage()"]');
    if (!el) return false;
    const d = Alpine.$data(el);
    return d.assets && d.assets.length > 0;
  });

  if (hasAssets) {
    await pg.evaluate(() => {
      const el = document.querySelector('[x-data="assetsPage()"]');
      Alpine.$data(el).viewAsset(Alpine.$data(el).assets[0]);
    });
    await pg.waitForTimeout(1000);
    const detailOpen = await pg.evaluate(() => {
      const el = document.querySelector('[x-data="assetsPage()"]');
      return Alpine.$data(el).showDetailModal;
    });
    record(results, 'Asset Detail', 'T2', detailOpen, 'Detail modal opened');
  } else {
    record(results, 'Asset Detail', 'T2', false, 'No assets to view - create one first');
  }
  record(results, 'Asset Errors', 'T1', errors.length === 0, errors.join('; '));

  // ==================== T3: QUALITY CHECK EXECUTION ====================
  console.log('\n--- T3: Quality Check ---');
  try {
    await pg.evaluate(() => {
      const el = document.querySelector('[x-data="qualityPage()"]');
      const d = Alpine.$data(el);
      d.code = 'def test():\n    x = "hardcoded_password = secret123"\n    print(x)';
      d.filename = 'e2e_test.py';
    });
    await pg.waitForTimeout(300);

    await pg.evaluate(() => {
      const el = document.querySelector('[x-data="qualityPage()"]');
      Alpine.$data(el).runCheck();
    });
    await pg.waitForTimeout(3000);

    const checkResult = await pg.evaluate(() => {
      const el = document.querySelector('[x-data="qualityPage()"]');
      const d = Alpine.$data(el);
      return d.result && d.result.issueCount !== undefined;
    });
    record(results, 'Quality Check Execute', 'T3', checkResult, 'Code check executed');
  } catch (e) { record(results, 'Quality Check', 'T3', false, e.message); }

  // ==================== SUMMARY ====================
  console.log('\n\n========== TEST SUMMARY ==========');
  const passed = results.filter(r => r.status === 'PASS').length;
  const failed = results.filter(r => r.status === 'FAIL').length;
  results.forEach(r => console.log(`  ${r.status === 'PASS' ? '✅' : '❌'} [${r.type}] ${r.name}${r.detail ? ' — ' + r.detail : ''}`));
  console.log(`\nTotal: ${results.length} | Passed: ${passed} | Failed: ${failed} | Rate: ${((passed/results.length)*100).toFixed(0)}%`);

  await browser.close();
})();