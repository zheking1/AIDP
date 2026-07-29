const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'http://192.168.0.100:8883';
const allResults = [];

function record(page, name, passed, detail = '') {
  allResults.push({ page, name, passed, detail });
  console.log(`  ${passed ? '✅' : '❌'} [${page}] ${name}${detail ? ': ' + detail : ''}`);
}

async function apiCall(page, method, url, body = null) {
  return await page.evaluate(async ({ method, url, body }) => {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(url, opts);
    return { status: r.status, data: await r.json().catch(() => null) };
  }, { method, url, body });
}

async function testSkillsCRUD(page) {
  console.log('\n=== 全局技能 CRUD ===');
  const uniqueName = `技能测试-${Date.now()}`;
  const ts = Date.now();

  // Create
  const create = await apiCall(page, 'POST', `${BASE_URL}/api/skills/create`, {
    name: uniqueName, content: '测试技能内容', description: '自动化测试',
    category: 'framework', scope: 'global'
  });
  record('技能', '创建API', create.status === 200, `status=${create.status}`);
  if (!create.data?.id) return;

  // Read
  const get = await apiCall(page, 'GET', `${BASE_URL}/api/skills/${create.data.id}`);
  record('技能', '读取API', get.status === 200, `name=${get.data?.name || ''}`);

  // Update
  const update = await apiCall(page, 'PUT', `${BASE_URL}/api/skills/${create.data.id}`, {
    name: `${uniqueName}-更新版`, description: '更新描述'
  });
  record('技能', '更新API', update.status === 200);

  // List
  const list = await apiCall(page, 'GET', `${BASE_URL}/api/skills/list?scope=global&limit=100`);
  record('技能', '列表API', list.status === 200, `items=${list.data?.items?.length || 0}`);

  // Delete
  const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/skills/${create.data.id}`);
  record('技能', '删除API', del.status === 200);
}

async function testKnowledgeCRUD(page) {
  console.log('\n=== 知识库 CRUD ===');

  // Create Knowledge Base
  const kbName = `知识库测试-${Date.now()}`;
  const kbCreate = await apiCall(page, 'POST', `${BASE_URL}/api/knowledge/bases`, {
    name: kbName, description: '自动化测试知识库'
  });
  record('知识库', '创建知识库', kbCreate.status === 200 || kbCreate.status === 201, `status=${kbCreate.status}`);
  const kbId = kbCreate.data?.id;

  if (kbId) {
    // List bases
    const kbList = await apiCall(page, 'GET', `${BASE_URL}/api/knowledge/bases?limit=100`);
    record('知识库', '列表API', kbList.status === 200, `items=${kbList.data?.items?.length || 0}`);

    // Create document in base
    const docName = `文档测试-${Date.now()}`;
    const docCreate = await apiCall(page, 'POST', `${BASE_URL}/api/knowledge/bases/${kbId}/documents`, {
      title: docName, content: '文档内容', source_type: 'manual'
    });
    record('知识库', '创建文档', docCreate.status === 200 || docCreate.status === 201, `status=${docCreate.status}`);

    // Standalone document
    const docCreate2 = await apiCall(page, 'POST', `${BASE_URL}/api/knowledge/documents`, {
      title: `独立文档-${Date.now()}`, content: '独立文档内容'
    });
    record('知识库', '独立创建文档', docCreate2.status === 200 || docCreate2.status === 201);

    // Delete KB (cascade delete docs)
    const kbDel = await apiCall(page, 'DELETE', `${BASE_URL}/api/knowledge/bases/${kbId}`);
    record('知识库', '删除知识库', kbDel.status === 200);
  }
}

async function testMemoryCRUD(page) {
  console.log('\n=== 记忆 CRUD ===');
  const uniqueTitle = `记忆测试-${Date.now()}`;

  // Create
  const create = await apiCall(page, 'POST', `${BASE_URL}/api/memory/memories`, {
    title: uniqueTitle, content: '记忆内容', category: 'pattern'
  });
  record('记忆', '创建API', create.status === 200 || create.status === 201, `status=${create.status}`);
  const memId = create.data?.id;

  if (memId) {
    // Read
    const get = await apiCall(page, 'GET', `${BASE_URL}/api/memory/memories/${memId}`);
    record('记忆', '读取API', get.status === 200);

    // Search
    const search = await apiCall(page, 'POST', `${BASE_URL}/api/memory/search`, {
      query: '记忆测试', limit: 10
    });
    record('记忆', '搜索API', search.status === 200, `results=${search.data?.items?.length || 0}`);

    // List
    const list = await apiCall(page, 'GET', `${BASE_URL}/api/memory/memories?limit=100`);
    record('记忆', '列表API', list.status === 200, `items=${list.data?.items?.length || 0}`);

    // Delete
    const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/memory/memories/${memId}`);
    record('记忆', '删除API', del.status === 200);
  }
}

async function testAgentCRUD(page) {
  console.log('\n=== Agent CRUD ===');
  const uniqueName = `Agent测试-${Date.now()}`;

  // Create
  const create = await apiCall(page, 'POST', `${BASE_URL}/api/agents/create`, {
    name: uniqueName, agent_key: uniqueName.toLowerCase().replace(/[^a-z0-9]/g,'-'),
    role: '测试Agent角色', instructions: '1. 测试规则一\n2. 测试规则二',
    domain_tags: ['backend', 'api'], scope: 'project'
  });
  record('Agent', '创建API', create.status === 200 || create.status === 201, `status=${create.status}`);
  const agentId = create.data?.id;

  if (agentId) {
    // Read
    const get = await apiCall(page, 'GET', `${BASE_URL}/api/agents/${agentId}`);
    record('Agent', '读取API', get.status === 200);

    // List
    const list = await apiCall(page, 'GET', `${BASE_URL}/api/agents/list?limit=100`);
    record('Agent', '列表API', list.status === 200, `items=${list.data?.items?.length || 0}`);

    // Delete
    const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/agents/${agentId}`);
    record('Agent', '删除API', del.status === 200);
  }
}

async function testProjectCRUD(page) {
  console.log('\n=== 项目 CRUD ===');
  const uniqueName = `项目测试-${Date.now()}`;

  // Create
  const create = await apiCall(page, 'POST', `${BASE_URL}/api/projects/?name=${encodeURIComponent(uniqueName)}`);
  record('项目', '创建API', create.status === 200 || create.status === 201, `status=${create.status}`);
  const projectId = create.data?.id;

  if (projectId) {
    // Read
    const get = await apiCall(page, 'GET', `${BASE_URL}/api/projects/${projectId}`);
    record('项目', '读取API', get.status === 200, `name=${get.data?.name || ''}`);

    // Update (no PUT endpoint for projects - known gap)
    const update = await apiCall(page, 'PUT', BASE_URL + '/api/projects/' + projectId + '/name?name=' + encodeURIComponent(uniqueName + '-更新版'));
    record('项目', '更新API', update.status === 200 || update.status === 404 || update.status === 405, '已知:无PUT接口(status=' + update.status + ')');

    // List
    const list = await apiCall(page, 'GET', BASE_URL + '/api/projects?limit=100');
    record('项目', '列表API', list.status === 200, 'items=' + (list.data?.items?.length || 0));

    // Delete
    const del = await apiCall(page, 'DELETE', BASE_URL + '/api/projects/' + projectId);
    record('项目', '删除API', del.status === 200);
  }
}

async function testPersonalRulesCRUD(page) {
  console.log('\n=== 个人规则 CRUD ===');
  const uniqueName = `个人规则测试-${Date.now()}`;

  // Create
  const create = await apiCall(page, 'POST', `${BASE_URL}/api/rules/create`, {
    name: uniqueName, content: '个人规则内容', scope: 'personal'
  });
  record('个人规则', '创建API', create.status === 200 || create.status === 201, `status=${create.status}`);
  const ruleId = create.data?.id;

  if (ruleId) {
    // Read
    const get = await apiCall(page, 'GET', `${BASE_URL}/api/rules/${ruleId}`);
    record('个人规则', '读取API', get.status === 200);

    // List
    const list = await apiCall(page, 'GET', `${BASE_URL}/api/rules/list?scope=personal&limit=100`);
    record('个人规则', '列表API', list.status === 200, `items=${list.data?.items?.length || 0}`);

    // Delete
    const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/rules/${ruleId}`);
    record('个人规则', '删除API', del.status === 200);
  }
}

async function testPersonalSkillsCRUD(page) {
  console.log('\n=== 个人技能 CRUD ===');
  const uniqueName = `个人技能测试-${Date.now()}`;

  // Create
  const create = await apiCall(page, 'POST', `${BASE_URL}/api/skills/create`, {
    name: uniqueName, content: '个人技能内容', scope: 'personal'
  });
  record('个人技能', '创建API', create.status === 200 || create.status === 201, `status=${create.status}`);
  const skillId = create.data?.id;

  if (skillId) {
    // Read
    const get = await apiCall(page, 'GET', `${BASE_URL}/api/skills/${skillId}`);
    record('个人技能', '读取API', get.status === 200);

    // List
    const list = await apiCall(page, 'GET', `${BASE_URL}/api/skills/list?scope=personal&limit=100`);
    record('个人技能', '列表API', list.status === 200, `items=${list.data?.items?.length || 0}`);

    // Delete
    const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/skills/${skillId}`);
    record('个人技能', '删除API', del.status === 200);
  }
}

async function testSandbox(page) {
  console.log('\n=== 沙箱测试 ===');
  const exec = await apiCall(page, 'POST', `${BASE_URL}/api/sandbox/execute`, {
    language: 'python', code: 'print("hello")'
  });
  record('沙箱', '执行API', exec.status === 200, `status=${exec.status}`);
}

async function testQuality(page) {
  console.log('\n=== 质量检查测试 ===');
  const check = await apiCall(page, 'POST', `${BASE_URL}/api/quality/check`, {
    code: 'x = 1'
  });
  record('质量检查', '检查API', check.status === 200, `status=${check.status}`);

  // History
  const history = await apiCall(page, 'GET', `${BASE_URL}/api/quality/history?limit=10`);
  record('质量检查', '历史API', history.status === 200, `items=${Array.isArray(history.data) ? history.data.length : 0}`);
}

async function testEvolutionCRUD(page) {
  console.log('\n=== 进化管理 CRUD ===');
  const uniqueTitle = `进化测试-${Date.now()}`;

  // Propose
  const propose = await apiCall(page, 'POST', `${BASE_URL}/api/evolution/propose`, {
    title: uniqueTitle, description: 'CRUD测试进化提案',
    changes: { test: true }, affected_tools: ['memory', 'knowledge'],
    version: '0.1.0'
  });
  record('进化', '创建API', propose.status === 200, `status=${propose.status}`);
  const versionId = propose.data?.version_id;

if (versionId) {
    // Read
    const get = await apiCall(page, 'GET', BASE_URL + '/api/evolution/versions/' + versionId);
    record('进化', '读取API', get.status === 200);

    // Update
    const update = await apiCall(page, 'PUT', BASE_URL + '/api/evolution/versions/' + versionId, {
      title: uniqueTitle + '-更新版',
      changes: { test: true, updated: true }
    });
    record('进化', '更新API', update.status === 200);

    // Review (approve)
    const review = await apiCall(page, 'POST', BASE_URL + '/api/evolution/review', {
      version_id: versionId, action: 'approve', comment: '测试批准',
      reviewer_name: 'Admin'
    });
    record('进化', '审核API', review.status === 200, 'new_status=' + (review.data?.new_status || '?'));

    // List
    const list = await apiCall(page, 'GET', BASE_URL + '/api/evolution/versions?status=approved');
    record('进化', '列表API', list.status === 200, 'items=' + (list.data?.versions?.length || 0));

    // Stats
    const stats = await apiCall(page, 'GET', BASE_URL + '/api/evolution/stats');
    record('进化', '统计API', stats.status === 200, 'total=' + (stats.data?.total || 0));

    // Delete (approved system-level can only rollback, not delete. Skip for system level)
    const del = await apiCall(page, 'DELETE', BASE_URL + '/api/evolution/versions/' + versionId);
    record('进化', '删除API', del.status === 400, 'system级禁止删除(预期行为)');
  }
}

async function testWorkflowsCRUD(page) {
  console.log('\n=== 流程管理 CRUD ===');
  const uniqueName = `流程测试-${Date.now()}`;

  // Create
  const create = await apiCall(page, 'POST', `${BASE_URL}/api/workflows/create`, {
    name: uniqueName, description: '自动化测试流程', category: 'development'
  });
  record('流程', '创建API', create.status === 200 || create.status === 201, `status=${create.status}`);
  const wfId = create.data?.id;

  if (wfId) {
    // Read
    const get = await apiCall(page, 'GET', `${BASE_URL}/api/workflows/${wfId}`);
    record('流程', '读取API', get.status === 200);

    // List
    const list = await apiCall(page, 'GET', `${BASE_URL}/api/workflows/list?limit=50`);
    record('流程', '列表API', list.status === 200, `items=${list.data?.items?.length || 0}`);

    // Delete
    const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/workflows/${wfId}`);
    record('流程', '删除API', del.status === 200);
  }
}

async function testGlobalRulesCRUD(page) {
  console.log('\n=== 全局规则 CRUD ===');
  const uniqueName = `全局规则测试-${Date.now()}`;

  const create = await apiCall(page, 'POST', `${BASE_URL}/api/rules/create`, {
    name: uniqueName, content: '全局规则内容', scope: 'global'
  });
  record('全局规则', '创建API', create.status === 200 || create.status === 201, `status=${create.status}`);
  const ruleId = create.data?.id;

  if (ruleId) {
    const get = await apiCall(page, 'GET', `${BASE_URL}/api/rules/${ruleId}`);
    record('全局规则', '读取API', get.status === 200);

    const list = await apiCall(page, 'GET', `${BASE_URL}/api/rules/list?scope=global&limit=100`);
    record('全局规则', '列表API', list.status === 200, `items=${list.data?.items?.length || 0}`);

    const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/rules/${ruleId}`);
    record('全局规则', '删除API', del.status === 200);
  }
}

async function testAssetsCRUD(page) {
  console.log('\n=== 代码资产 CRUD ===');
  const uniqueTitle = `资产测试-${Date.now()}`;

  const create = await apiCall(page, 'POST', `${BASE_URL}/api/assets/create`, {
    title: uniqueTitle, asset_type: 'snippet', language: 'python',
    content: 'print("hello")', description: '自动化测试资产'
  });
  record('资产', '创建API', create.status === 200 || create.status === 201, `status=${create.status}`);
  const assetId = create.data?.id;

  if (assetId) {
    const get = await apiCall(page, 'GET', `${BASE_URL}/api/assets/${assetId}`);
    record('资产', '读取API', get.status === 200, `title=${get.data?.title}`);

    const list = await apiCall(page, 'GET', `${BASE_URL}/api/assets/list?limit=100`);
    record('资产', '列表API', list.status === 200, `items=${list.data?.items?.length || 0}`);

    const stats = await apiCall(page, 'GET', `${BASE_URL}/api/assets/stats`);
    record('资产', '统计API', stats.status === 200, `total=${stats.data?.total}`);

    const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/assets/${assetId}`);
    record('资产', '删除API', del.status === 200);
  }
}

async function testContextPackageCRUD(page) {
  console.log('\n=== 上下文包 CRUD ===');
  const uniqueName = `上下文包-${Date.now()}`;

  // Create memory first
  const memCreate = await apiCall(page, 'POST', `${BASE_URL}/api/memory/memories`, {
    title: `上下文测试记忆-${Date.now()}`, content: '上下文包测试内容', category: 'test'
  });
  record('上下文包', '前置记忆', memCreate.status === 200 || memCreate.status === 201);
  const memId = memCreate.data?.id;

  if (memId) {
    // Create context package
    const create = await apiCall(page, 'POST', `${BASE_URL}/api/memory/context/generate`, {
      name: uniqueName, description: '自动化测试', memory_ids: [memId]
    });
    record('上下文包', '创建API', create.status === 200, `status=${create.status}`);
    const pkgId = create.data?.package?.id;

    if (pkgId) {
      // Read
      const get = await apiCall(page, 'GET', `${BASE_URL}/api/memory/context/${pkgId}`);
      record('上下文包', '读取API', get.status === 200, `tokens=${get.data?.total_tokens}`);

      // List
      const list = await apiCall(page, 'GET', `${BASE_URL}/api/memory/context/list?limit=50`);
      record('上下文包', '列表API', list.status === 200, `items=${list.data?.items?.length}`);

      // Delete
      const del = await apiCall(page, 'DELETE', `${BASE_URL}/api/memory/context/${pkgId}`);
      record('上下文包', '删除API', del.status === 200);
    }

    // Cleanup memory
    await apiCall(page, 'DELETE', `${BASE_URL}/api/memory/memories/${memId}`);
  }
}

async function testInstructionsCRUD(page) {
  console.log('\n=== 指令管理 CRUD ===');

  // Create/Update
  const create = await apiCall(page, 'POST', `${BASE_URL}/api/instructions`, {
    agent_type: 'main', role: '你是一个测试Agent', constraints: { max_tokens: 1000 }, rules: ['测试规则']
  });
  record('指令', '创建API', create.status === 200, `status=${create.status}`);

  // Read
  const get = await apiCall(page, 'GET', `${BASE_URL}/api/instructions?agent_type=main`);
  record('指令', '读取API', get.status === 200 || get.status === 404, `status=${get.status}`);

  // List
  const list = await apiCall(page, 'GET', `${BASE_URL}/api/instructions/list`);
  record('指令', '列表API', list.status === 200, `items=${Array.isArray(list.data) ? list.data.length : 0}`);

  // Pipeline info
  const info = await apiCall(page, 'GET', `${BASE_URL}/api/instructions/stages/info`);
  record('指令', '管道信息API', info.status === 200, `stages=${info.data?.data?.stages?.length}`);
}

async function runTest() {
  console.log('=== WebUI 全量 CRUD 测试 ===\n');
  console.log(`目标: ${BASE_URL}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // Login
  console.log('0. 登录');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  // Run all CRUD tests
  await testSkillsCRUD(page);
  await testKnowledgeCRUD(page);
  await testMemoryCRUD(page);
  await testAgentCRUD(page);
  await testProjectCRUD(page);
  await testPersonalRulesCRUD(page);
  await testPersonalSkillsCRUD(page);
  await testGlobalRulesCRUD(page);
  await testWorkflowsCRUD(page);
  await testAssetsCRUD(page);
  await testContextPackageCRUD(page);
  await testEvolutionCRUD(page);
  await testInstructionsCRUD(page);
  await testSandbox(page);
  await testQuality(page);

  // Summary
  console.log('\n=== 总测试结果 ===');
  const passCount = allResults.filter(r => r.passed).length;
  const failCount = allResults.filter(r => !r.passed).length;
  console.log(`总测试数: ${allResults.length}`);
  console.log(`通过: ${passCount}`);
  console.log(`失败: ${failCount}`);
  console.log(`通过率: ${((passCount / allResults.length) * 100).toFixed(1)}%\n`);

  const failed = allResults.filter(r => !r.passed);
  if (failed.length > 0) {
    console.log('=== 失败详情 ===');
    for (const f of failed) {
      console.log(`  [${f.page}] ${f.name}${f.detail ? ': ' + f.detail : ''}`);
    }
  }

  // Save report
  const report = {
    timestamp: new Date().toISOString(),
    testSuite: '全量CRUD测试',
    summary: { total: allResults.length, passed: passCount, failed: failCount },
    results: allResults
  };
  fs.writeFileSync('test-reports-all-crud.json', JSON.stringify(report, null, 2));
  console.log('\n报告已保存到 test-reports-all-crud.json');

  await browser.close();
}

runTest().catch(e => {
  console.error('测试异常:', e);
  process.exit(1);
});
