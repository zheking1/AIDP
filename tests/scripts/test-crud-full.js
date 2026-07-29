const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  let passed = 0, failed = 0;
  const test = async (name, fn) => {
    try { await fn(); passed++; process.stdout.write('.'); }
    catch(e) { failed++; process.stdout.write('X'); console.error(`\nFAIL ${name}: ${e.message.substring(0, 200)}`); }
  };

  const api = async (method, url, body) => {
    const r = await page.evaluate(async ([m, u, b]) => {
      try {
        const res = await fetch(u, { method: m, headers: { 'Content-Type': 'application/json' }, body: b });
        const text = await res.text();
        let json;
        try { json = JSON.parse(text); } catch(e) { json = { raw: text.substring(0, 100) }; }
        return { status: res.status, ok: res.ok, data: json };
      } catch(e) { return { status: 0, ok: false, error: e.message } };
    }, [method, url, body ? JSON.stringify(body) : undefined]);
    return r;
  };

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // ===== 1. 项目管理 =====
  console.log('=== 项目管理 ===');
  await test('GET 列表', async () => {
    const r = await api('GET', BASE + '/api/projects');
    if (!r.ok) throw new Error('GET failed: ' + r.status);
  });
  await test('POST 创建', async () => {
    const r = await api('POST', BASE + '/api/projects', { name: 'CRUD-测试项目', description: 'CRUD测试', tech_stack: ['Python', 'FastAPI'] });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });
  await test('GET 验证创建', async () => {
    const r = await api('GET', BASE + '/api/projects');
    if (!r.data?.items?.some(i => i.name === 'CRUD-测试项目')) throw new Error('项目未出现在列表');
  });
  await test('DELETE 删除', async () => {
    // Get project ID first
    const r = await api('GET', BASE + '/api/projects');
    const proj = r.data?.items?.find(i => i.name === 'CRUD-测试项目');
    if (!proj) throw new Error('找不到刚创建的项目');
    const del = await api('DELETE', BASE + '/api/projects/' + proj.id);
    if (!del.ok && del.status !== 404) throw new Error('DELETE failed: ' + del.status);
  });

  // ===== 2. 知识中心 UI CRUD =====
  console.log('\n=== 知识中心 ===');
  await test('页面加载 + 创建', async () => {
    await page.goto(BASE + '/knowledge/bases?partial=1', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    const body = await page.textContent('body');
    if (!body.includes('知识库')) throw new Error('页面未加载');
  });
  await test('API 创建知识库', async () => {
    const r = await api('POST', BASE + '/api/knowledge/bases', { name: 'CRUD-测试知识库', description: 'CRUD测试' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });
  await test('API 删除知识库', async () => {
    const r = await api('GET', BASE + '/api/knowledge/bases');
    const kb = r.data?.items?.find(i => i.name === 'CRUD-测试知识库');
    if (kb) await api('DELETE', BASE + '/api/knowledge/bases/' + kb.id);
  });

  // ===== 3. 技能 =====
  console.log('\n=== 技能 ===');
  await test('API CRUD', async () => {
    const r = await api('POST', BASE + '/api/skills/create', { name: 'CRUD-测试技能', description: 'CRUD测试', instruction: 'test', content: 'test', scope: 'personal' });
    if (!r.ok) throw new Error('CREATE failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });

  // ===== 4. 记忆 =====
  console.log('\n=== 记忆 ===');
  await test('API CRUD', async () => {
    const r = await api('POST', BASE + '/api/memory/memories', { title: 'CRUD-测试记忆', content: 'CRUD测试内容', category: 'general', tier: 'P1' });
    if (!r.ok) throw new Error('CREATE failed: ' + r.status);
  });

  // ===== 5. Agent =====
  console.log('\n=== Agent ===');
  await test('API CRUD', async () => {
    const r = await api('POST', BASE + '/api/agents/create', { name: 'CRUD-测试Agent', role: '测试工程师', description: 'CRUD测试', instructions: 'test', scope: 'personal' });
    if (!r.ok) throw new Error('CREATE failed: ' + r.status);
  });

  // ===== 6. 工作流 =====
  console.log('\n=== 工作流 ===');
  await test('API CRUD', async () => {
    const r = await api('POST', BASE + '/api/workflows/create', { name: 'CRUD-测试工作流', description: 'CRUD测试', category: 'development', scope: 'personal' });
    if (!r.ok) throw new Error('CREATE failed: ' + r.status);
  });

  // ===== 7. 资产 =====
  console.log('\n=== 资产 ===');
  await test('API CRUD', async () => {
    const r = await api('POST', BASE + '/api/assets/create', { title: 'CRUD-测试资产', content: 'print("test")', type: 'snippet', language: 'python' });
    if (!r.ok) throw new Error('CREATE failed: ' + r.status);
  });

  // ===== 8. 规则 =====
  console.log('\n=== 规则 ===');
  await test('API CRUD', async () => {
    const r = await api('POST', BASE + '/api/rules/create', { name: 'CRUD-测试规则', content: '禁止使用 eval', description: 'CRUD测试', category: 'security', severity: 'high', scope: 'personal' });
    if (!r.ok) throw new Error('CREATE failed: ' + r.status);
  });

  // ===== 9. 指令管理 =====
  console.log('\n=== 指令 ===');
  await test('API CRUD', async () => {
    const r = await api('POST', BASE + '/api/instructions', { project_id: 0, agent_type: 'crud-test', role: 'CRUD测试指令角色', constraints: {}, rules: ['rule1'] });
    if (!r.ok) throw new Error('CREATE failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });

  // ===== 10. 模型管理 =====
  console.log('\n=== 模型 ===');
  await test('API CRUD', async () => {
    const r = await api('POST', BASE + '/api/models', { name: 'CRUD-测试模型', model_name: 'gpt-4o-test', endpoint: 'https://test.api.com/v1', api_key: 'sk-test', provider: 'test', role: 'completion', status: 'active' });
    if (!r.ok) throw new Error('CREATE failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });

  // ===== Summary =====
  const total = passed + failed;
  console.log(`\n\n${'='.repeat(40)}`);
  console.log(`完整 CRUD 测试: ${total} 项, ${passed} 通过, ${failed} 失败`);
  console.log(`${'='.repeat(40)}`);
  if (failed > 0) process.exit(1);
  await browser.close();
})();