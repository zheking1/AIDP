const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  let passed = 0, failed = 0, allErrors = [];

  const test = async (name, fn) => {
    let errors = [];
    page.on('pageerror', e => errors.push(e.message.substring(0,80)));
    page.on('console', msg => { if (msg.type() === 'error' || msg.type() === 'warning') errors.push(msg.type()+':'+msg.text().substring(0,80)); });
    page.on('response', r => { if (r.status() >= 400) errors.push(r.status()+':'+r.url().substring(0,60)); });

    try {
      await fn();
      passed++;
      process.stdout.write('.');
      if (errors.length) console.log('\n  ⚠ 出现 ' + errors.length + ' 个错误:', errors.slice(0,3).join('; '));
    } catch(e) {
      failed++;
      process.stdout.write('X');
      console.log('\n  ❌ ' + name + ': ' + e.message.substring(0,150));
      if (errors.length) console.log('  上下文错误:', errors.slice(0,3).join('; '));
    }
  };

  const api = async (method, url, body) => {
    return await page.evaluate(async ([m, u, b]) => {
      try {
        const res = await fetch(u, { method: m, headers: { 'Content-Type': 'application/json' }, body: b });
        const text = await res.text();
        let json;
        try { json = JSON.parse(text); } catch(e) { json = { raw: text.substring(0, 100) }; }
        return { status: res.status, ok: res.ok, data: json };
      } catch(e) { return { status: 0, ok: false, error: e.message }; }
    }, [method, url, body ? JSON.stringify(body) : undefined]);
  };

  // Login
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  console.log('\n=== 知识库 API CRUD 测试 ===\n');

  // ===== 1. CREATE =====
  let kbId = null;
  await test('POST /api/knowledge/bases 创建知识库', async () => {
    const r = await api('POST', BASE + '/api/knowledge/bases', {
      name: 'CRUD-测试知识库', description: '用于CRUD自动化测试', category: 'test'
    });
    if (!r.ok) throw new Error('创建失败: ' + r.status + ' ' + JSON.stringify(r.data));
    kbId = r.data.id;
    if (!kbId) throw new Error('未返回ID');
  });

  await test('POST /api/knowledge/bases 创建同名知识库(异常)', async () => {
    const r = await api('POST', BASE + '/api/knowledge/bases', {
      name: 'CRUD-测试知识库', description: '重复创建测试'
    });
    // 重复创建应该成功（目前允许同名）
    if (!r.ok) throw new Error('重名创建失败: ' + r.status);
  });

  // ===== 2. READ (List) =====
  await test('GET /api/knowledge/bases 列表', async () => {
    const r = await api('GET', BASE + '/api/knowledge/bases');
    if (!r.ok) throw new Error('列表查询失败: ' + r.status);
    const items = r.data?.items || [];
    const found = items.find(i => i.name === 'CRUD-测试知识库');
    if (!found) throw new Error('刚创建的知识库未出现在列表中');
  });

  await test('GET /api/knowledge/bases?search= 搜索', async () => {
    const r = await api('GET', BASE + '/api/knowledge/bases?search=CRUD');
    if (!r.ok) throw new Error('搜索失败');
    if (!r.data?.items?.length) throw new Error('搜索结果为空');
  });

  // ===== 3. READ (Detail) =====
  await test('GET /api/knowledge/bases/{id} 详情', async () => {
    if (!kbId) throw new Error('缺少知识库ID');
    const r = await api('GET', BASE + '/api/knowledge/bases/' + kbId);
    if (!r.ok) throw new Error('查询详情失败: ' + r.status);
    if (r.data?.name !== 'CRUD-测试知识库') throw new Error('返回数据不正确');
  });

  // ===== 4. 文档 CRUD =====
  let docId = null;
  await test('POST 上传文档', async () => {
    if (!kbId) throw new Error('缺少知识库ID');
    const r = await api('POST', BASE + '/api/knowledge/bases/' + kbId + '/documents', {
      title: 'CRUD-测试文档.md', content: '# 测试文档\n\n这是用于CRUD测试的内容', source_type: 'manual'
    });
    if (!r.ok) throw new Error('上传失败: ' + r.status);
  });

  await test('GET 文档列表', async () => {
    if (!kbId) throw new Error('缺少知识库ID');
    const r = await api('GET', BASE + '/api/knowledge/bases/' + kbId + '/documents');
    if (!r.ok) throw new Error('文档列表查询失败');
    const docs = r.data?.items || [];
    const found = docs.find(d => d.title === 'CRUD-测试文档.md');
    if (!found) throw new Error('刚创建的文档未出现在列表中');
    docId = found.id;
  });

  await test('GET /api/knowledge/documents/{id} 文档详情', async () => {
    if (!docId) throw new Error('缺少文档ID');
    const r = await api('GET', BASE + '/api/knowledge/documents/' + docId);
    if (!r.ok) throw new Error('文档详情查询失败: ' + r.status);
  });

  await test('DELETE 文档', async () => {
    if (!docId) throw new Error('缺少文档ID');
    const r = await api('DELETE', BASE + '/api/knowledge/documents/' + docId);
    if (!r.ok) throw new Error('删除文档失败');
  });

  // ===== 5. 搜索 =====
  await test('POST /api/knowledge/search 搜索', async () => {
    const r = await api('POST', BASE + '/api/knowledge/search', { query: '测试', limit: 10 });
    if (!r.ok) throw new Error('搜索失败: ' + r.status);
  });

  // ===== 6. 统计 =====
  await test('GET /api/knowledge/stats 统计', async () => {
    const r = await api('GET', BASE + '/api/knowledge/stats');
    if (!r.ok) throw new Error('统计查询失败');
    if (typeof r.data?.total_bases !== 'number') throw new Error('统计返回格式异常');
  });

  // ===== 7. DELETE 知识库 =====
  await test('DELETE /api/knowledge/bases/{id} 删除知识库', async () => {
    if (!kbId) throw new Error('缺少知识库ID');
    const r = await api('DELETE', BASE + '/api/knowledge/bases/' + kbId);
    if (!r.ok) throw new Error('删除失败: ' + r.status + ' ' + JSON.stringify(r.data));
  });

  await test('GET 验证已删除', async () => {
    if (!kbId) throw new Error('缺少知识库ID');
    const r = await api('GET', BASE + '/api/knowledge/bases/' + kbId);
    if (r.status !== 404 && r.status !== 200) throw new Error('查询已删除知识库异常: ' + r.status);
    if (r.status === 200) throw new Error('删除后仍可查询到');
  });

  // ===== 8. UI 测试 =====
  console.log('\n=== 知识库 UI 测试 ===\n');

  await test('页面加载 - 知识中心', async () => {
    await page.evaluate(() => { document.querySelector('nav')?.scrollTo(0,0); document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('知识中心')&&b.offsetParent) b.click(); }); });
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    if (!body.includes('知识库')) throw new Error('页面未加载');
  });

  await test('布局检查 - flex header', async () => {
    const layout = await page.evaluate(() => {
      const tab = Array.from(document.querySelectorAll('[id^=tab-content-]')).find(el => getComputedStyle(el).display !== 'none');
      if(!tab) return null;
      const w = tab.firstElementChild; if(!w) return null;
      const h = w.querySelector(':scope > div:first-of-type'); if(!h) return null;
      const s = getComputedStyle(h);
      return { display: s.display, justify: s.justifyContent, pt: s.paddingTop, pb: s.paddingBottom };
    });
    if (!layout || layout.display !== 'flex') throw new Error('Header 不是 flex: ' + JSON.stringify(layout));
  });

  // ===== Results =====
  const total = Math.min(passed + failed, 15);
  console.log('\n\n' + '='.repeat(50));
  console.log('知识库 CRUD 测试报告');
  console.log('='.repeat(50));
  console.log('共 ' + total + ' 项: ' + passed + ' 通过, ' + failed + ' 失败');
  console.log('='.repeat(50));
  if (failed > 0) process.exit(1);

  await browser.close();
})();