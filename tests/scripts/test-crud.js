const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  let passed = 0, failed = 0;
  const test = async (name, fn) => {
    try { await fn(); passed++; process.stdout.write('.'); }
    catch(e) { failed++; process.stdout.write('X'); console.log(`\n❌ ${name}: ${e.message.substring(0, 200)}`); }
  };

  const api = async (method, url, body) => {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const resp = await page.evaluate(async ([m, u, b, h]) => {
      try {
        const r = await fetch(u, { method: m, headers: h, body: b });
        const text = await r.text();
        let json;
        try { json = JSON.parse(text); } catch(e) { json = { raw: text.substring(0, 100) }; }
        return { status: r.status, ok: r.ok, data: json };
      } catch(e) {
        return { status: 0, ok: false, error: e.message };
      }
    }, [method, url, body ? JSON.stringify(body) : undefined, { 'Content-Type': 'application/json' }]);
    return resp;
  };

  // Login and get session
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  const created = [];

  // ===== 1. 指令管理 =====
  console.log('\n=== 指令管理 CRUD ===');
  await test('GET /api/instructions/list', async () => {
    const r = await api('GET', BASE + '/api/instructions/list');
    if (!r.ok) throw new Error('GET failed: ' + r.status);
  });
  await test('POST /api/instructions (create)', async () => {
    const r = await api('POST', BASE + '/api/instructions', { project_id: 0, agent_type: 'crud-test', role: 'CRUD测试指令角色', constraints: {}, rules: ['rule1', 'rule2'] });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });
  await test('GET /api/instructions/list (verify & get id)', async () => {
    const r = await api('GET', BASE + '/api/instructions/list');
    const items = Array.isArray(r.data) ? r.data : (r.data?.items || []);
    const found = items.find(i => i.agent_type === 'crud-test');
    if (!found) throw new Error('创建后未在列表中找到');
    created.push({ type: 'instruction', id: found.id });
  });
  if (created.length > 0 && created[created.length-1].type === 'instruction') {
    await test('DELETE /api/instructions/{id}', async () => {
      const item = created.pop();
      const r = await api('DELETE', BASE + '/api/instructions/' + item.id, {});
      if (!r.ok) throw new Error('DELETE failed: ' + r.status + ' ' + JSON.stringify(r.data));
    });
  }

  // ===== 2. 模型管理 =====
  console.log('\n=== 模型管理 CRUD ===');
  await test('GET /api/models', async () => {
    const r = await api('GET', BASE + '/api/models');
    if (!r.ok) throw new Error('GET failed');
  });
  await test('POST /api/models (create)', async () => {
    const r = await api('POST', BASE + '/api/models', { name: 'CRUD测试模型', model_name: 'gpt-4o-test', endpoint: 'https://test.api.com/v1', api_key: 'sk-test', provider: 'test', role: 'completion', status: 'active' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
    const modelId = r.data?.model?.id;
    if (!modelId) throw new Error('No model.id in response: ' + JSON.stringify(r.data));
    created.push({ type: 'model', id: modelId });
  });
  await test('GET /api/models (verify)', async () => {
    const r = await api('GET', BASE + '/api/models');
    const items = r.data?.items || [];
    if (!items.some(i => i.name === 'CRUD测试模型')) throw new Error('创建后未找到');
  });
  if (created.length > 0 && created[created.length-1].type === 'model') {
    await test('DELETE /api/models/{id}', async () => {
      const item = created.pop();
      const r = await api('DELETE', BASE + '/api/models/' + item.id);
      if (!r.ok) throw new Error('DELETE failed: ' + r.status);
    });
  }

  // ===== 3. 知识库 =====
  console.log('\n=== 知识库 CRUD ===');
  await test('GET /api/knowledge/bases', async () => {
    const r = await api('GET', BASE + '/api/knowledge/bases');
    if (!r.ok) throw new Error('GET failed');
  });
  await test('POST /api/knowledge/bases (create)', async () => {
    const r = await api('POST', BASE + '/api/knowledge/bases', { name: 'CRUD测试知识库', description: 'CRUD测试描述', category: 'test' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
    created.push({ type: 'kb', id: r.data.id });
  });
  await test('GET /api/knowledge/bases (verify)', async () => {
    const r = await api('GET', BASE + '/api/knowledge/bases');
    if (!r.data?.items?.some(i => i.name === 'CRUD测试知识库')) throw new Error('创建后未找到');
  });
  if (created.length > 0 && created[created.length-1].type === 'kb') {
    await test('DELETE /api/knowledge/bases/{id}', async () => {
      const item = created.pop();
      const r = await api('DELETE', BASE + '/api/knowledge/bases/' + item.id);
      if (!r.ok) throw new Error('DELETE failed: ' + r.status);
    });
  }

  // ===== 4. 技能 (Skills) =====
  console.log('\n=== 技能 CRUD ===');
  await test('GET /api/skills/list', async () => {
    const r = await api('GET', BASE + '/api/skills/list?scope=personal');
    if (!r.ok) throw new Error('GET failed');
  });
  await test('POST /api/skills/create', async () => {
    const r = await api('POST', BASE + '/api/skills/create', { name: 'CRUD测试技能', description: 'CRUD测试', instruction: 'test', content: 'test', scope: 'personal' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });
  await test('GET /api/skills/list (verify)', async () => {
    const r = await api('GET', BASE + '/api/skills/list?scope=personal');
    if (!r.data?.items?.some(i => i.name === 'CRUD测试技能')) throw new Error('创建后未找到');
  });

  // ===== 5. 记忆 =====
  console.log('\n=== 记忆 CRUD ===');
  await test('GET /api/memory/memories', async () => {
    const r = await api('GET', BASE + '/api/memory/memories');
    if (!r.ok) throw new Error('GET failed');
  });
  await test('POST /api/memory/memories (create)', async () => {
    const r = await api('POST', BASE + '/api/memory/memories', { title: 'CRUD测试记忆', content: 'CRUD测试内容', category: 'general', tier: 'P1' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
    created.push({ type: 'memory', id: r.data.id });
  });
  await test('GET /api/memory/memories (verify)', async () => {
    const r = await api('GET', BASE + '/api/memory/memories');
    if (!r.data?.items?.some(i => i.title === 'CRUD测试记忆')) throw new Error('创建后未找到');
  });
  if (created.length > 0 && created[created.length-1].type === 'memory') {
    await test('DELETE /api/memory/memories/{id}', async () => {
      const item = created.pop();
      const r = await api('DELETE', BASE + '/api/memory/memories/' + item.id);
      if (!r.ok) throw new Error('DELETE failed: ' + r.status);
    });
  }

  // ===== 6. Agent =====
  console.log('\n=== Agent CRUD ===');
  await test('GET /api/agents/list', async () => {
    const r = await api('GET', BASE + '/api/agents/list');
    if (!r.ok) throw new Error('GET failed');
  });
  await test('POST /api/agents/create', async () => {
    const r = await api('POST', BASE + '/api/agents/create', { name: 'CRUD测试Agent', role: '测试工程师', description: 'CRUD测试', instructions: '你是一个测试Agent', scope: 'personal' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });
  await test('GET /api/agents/list (verify)', async () => {
    const r = await api('GET', BASE + '/api/agents/list');
    if (!r.data?.items?.some(i => i.name === 'CRUD测试Agent')) throw new Error('创建后未找到');
  });

  // ===== 7. 工作流 =====
  console.log('\n=== 工作流 CRUD ===');
  await test('GET /api/workflows/list', async () => {
    const r = await api('GET', BASE + '/api/workflows/list');
    if (!r.ok) throw new Error('GET failed');
  });
  await test('POST /api/workflows/create', async () => {
    const r = await api('POST', BASE + '/api/workflows/create', { name: 'CRUD测试工作流', description: 'CRUD测试', category: 'development', scope: 'personal' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });
  await test('GET /api/workflows/list (verify)', async () => {
    const r = await api('GET', BASE + '/api/workflows/list');
    if (!r.data?.items?.some(i => i.name === 'CRUD测试工作流')) throw new Error('创建后未找到');
  });

  // ===== 8. 资产 =====
  console.log('\n=== 资产 CRUD ===');
  await test('GET /api/assets/list', async () => {
    const r = await api('GET', BASE + '/api/assets/list');
    if (!r.ok) throw new Error('GET failed');
  });
  await test('POST /api/assets/create', async () => {
    const r = await api('POST', BASE + '/api/assets/create', { title: 'CRUD测试资产', content: 'print("hello")', type: 'snippet', language: 'python' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });
  await test('GET /api/assets/list (verify)', async () => {
    const r = await api('GET', BASE + '/api/assets/list');
    if (!r.data?.items?.some(i => i.title === 'CRUD测试资产')) throw new Error('创建后未找到');
  });

  // ===== 9. 规则 =====
  console.log('\n=== 规则 CRUD ===');
  await test('GET /api/rules/list', async () => {
    const r = await api('GET', BASE + '/api/rules/list?scope=personal');
    if (!r.ok) throw new Error('GET failed');
  });
  await test('POST /api/rules/create', async () => {
    const r = await api('POST', BASE + '/api/rules/create', { name: 'CRUD测试规则', content: '禁止使用 eval', description: 'CRUD测试', category: 'security', severity: 'high', scope: 'personal' });
    if (!r.ok) throw new Error('POST failed: ' + r.status + ' ' + JSON.stringify(r.data));
  });
  await test('GET /api/rules/list (verify)', async () => {
    const r = await api('GET', BASE + '/api/rules/list?scope=personal');
    if (!r.data?.items?.some(i => i.name === 'CRUD测试规则')) throw new Error('创建后未找到');
  });

  // ===== Summary =====
  const total = passed + failed;
  console.log(`\n\n${'='.repeat(40)}`);
  console.log(`共 ${total} 项 CRUD API 测试: ${passed} 通过, ${failed} 失败`);
  console.log(`${'='.repeat(40)}`);
  if (failed > 0) process.exit(1);
  await browser.close();
})();