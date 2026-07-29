const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await ctx.newPage();

  let passed=0, failed=0;
  const test = async (name, fn) => {
    try { await fn(); passed++; process.stdout.write('.'); }
    catch(e) { failed++; process.stdout.write('X'); console.log('\n❌ '+name+': '+e.message.substring(0,200)); }
  };

  await page.goto(BASE+'/login', { waitUntil: 'networkidle' });
  await page.fill('#username','admin'); await page.fill('#password','admin123');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(3000);

  const ts = Date.now().toString(36).substring(4,10);
  let createdBaseId = null;

  // Create a knowledge base via API
  const baseResp = await page.evaluate(async (n) => {
    const r = await fetch('/api/knowledge/bases', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:'cat-test-'+n, description:'cat test'})
    });
    if (!r.ok) return null;
    const d = await r.json();
    return d.id;
  }, ts);
  if (!baseResp) { console.log('Failed to create base'); await browser.close(); return; }
  createdBaseId = baseResp;

  // Create a document with category via API
  test('创建带分类的文档', async () => {
    const r = await page.evaluate(async (args) => {
      const res = await fetch('/api/knowledge/bases/'+args.baseId+'/documents', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({title:'cat-doc-'+args.ts, content:'test', doc_type:'markdown', category:'research/market'})
      });
      return res.ok ? (await res.json()).id : null;
    }, {baseId: createdBaseId, ts});
    if (!r) throw new Error('创建文档失败');
  });

  // Verify document has category via API
  test('验证文档分类', async () => {
    const cat = await page.evaluate(async (args) => {
      const r = await fetch('/api/knowledge/documents-list?base_id='+args.baseId);
      if (!r.ok) return null;
      const d = await r.json();
      const doc = (d.items||[]).find(i => i.title === 'cat-doc-'+args.ts);
      return doc ? doc.category : null;
    }, {baseId: createdBaseId, ts});
    if (cat !== 'research/market') throw new Error('分类未保存: '+cat);
  });

  // Update document category via PUT
  test('更新文档分类', async () => {
    const result = await page.evaluate(async (args) => {
      const r1 = await fetch('/api/knowledge/documents-list?base_id='+args.baseId);
      const d1 = await r1.json();
      const doc = (d1.items||[]).find(i => i.title === 'cat-doc-'+args.ts);
      if (!doc) return 'NOT_FOUND';
      const r2 = await fetch('/api/knowledge/documents/'+doc.id, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({category:'prd/requirements'})
      });
      return r2.ok ? 'OK' : 'FAIL:'+r2.status;
    }, {baseId: createdBaseId, ts});
    if (result !== 'OK') throw new Error('更新失败: '+result);
  });

  // Verify updated category
  test('验证更新后的分类', async () => {
    const cat = await page.evaluate(async (args) => {
      const r = await fetch('/api/knowledge/documents-list?base_id='+args.baseId);
      const d = await r.json();
      const doc = (d.items||[]).find(i => i.title === 'cat-doc-'+args.ts);
      return doc ? doc.category : null;
    }, {baseId: createdBaseId, ts});
    if (cat !== 'prd/requirements') throw new Error('分类未更新: '+cat);
  });

  // Filter by category
  test('按分类筛选', async () => {
    const count = await page.evaluate(async (baseId) => {
      const r = await fetch('/api/knowledge/documents-list?base_id='+baseId+'&category=prd/requirements');
      const d = await r.json();
      return (d.items||[]).length;
    }, createdBaseId);
    if (count < 1) throw new Error('筛选结果为空');
  });

  // Cleanup
  await page.evaluate(async (args) => {
    const r = await fetch('/api/knowledge/documents-list?base_id='+args);
    const d = await r.json();
    for (const doc of d.items||[]) {
      await fetch('/api/knowledge/documents/'+doc.id, {method:'DELETE'});
    }
    await fetch('/api/knowledge/bases/'+args, {method:'DELETE'});
  }, createdBaseId);

  console.log('\n\n=== 结果: '+passed+'/'+(passed+failed)+' 通过 ===');
  if (failed>0) process.exit(1);
  await browser.close();
})();