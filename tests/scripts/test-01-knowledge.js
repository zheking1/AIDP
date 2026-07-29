const { chromium } = require('playwright');
const { login, openWorkspace, openTab, cleanup } = require('./helper');
const TS = Date.now();

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  const jsErrors = [];
  pg.on('pageerror', err => jsErrors.push(err.message));

  await login(pg);
  await openWorkspace(pg);
  console.log('=== 知识中心 Hub 测试 ===\n');

  const results = [];

  // ===== 1. 知识库管理 =====
  console.log('--- 知识库管理 ---');
  await openTab(pg, 'kb', '知识库管理', 'fa-database', '/knowledge/bases');
  jsErrors.length = 0;

  // T3-创建: 点击创建按钮 → 弹窗打开
  await pg.locator('button:has-text("创建知识库")').first().click();
  await pg.waitForTimeout(1500);
  modal = pg.locator('.fixed.inset-0:visible').last();
  modalOpen = await modal.isVisible();
  console.log('  创建按钮 → 弹窗:', modalOpen ? 'PASS' : 'FAIL');

  // 填写表单
  await modal.locator('input[x-model="formKB.name"]').fill('KB-' + TS);
  await modal.locator('textarea[x-model="formKB.description"]').fill('测试知识库');
  await pg.waitForTimeout(500);

  // 提交
  await modal.locator('button:has-text("创建知识库")').click();
  await pg.waitForTimeout(3000);
  let bodyText = await pg.textContent('body');
  let created = bodyText.includes('KB-' + TS);
  console.log('  提交 → 数据可见:', created ? 'PASS' : 'FAIL');

  // 清理
  if (created) {
    const d = await pg.evaluate(() => {
      const el = document.querySelector('[x-data="knowledgeBasesPage()"]');
      const data = Alpine.$data(el);
      const kb = data.knowledgeBases.find(k => k.name.includes('KB-'));
      return kb ? kb.id : null;
    });
    if (d) await cleanup(pg, '/api/knowledge/bases/' + d);
  }
  console.log('  JS错误:', jsErrors.length === 0 ? 'PASS' : jsErrors.join('; '));
  results.push({ page: '知识库管理', pass: modalOpen && created && jsErrors.length === 0 });

  // ===== 2. 知识文档 =====
  console.log('\n--- 知识文档 ---');
  await openTab(pg, 'docs', '文档管理', 'fa-file-text', '/knowledge/documents');
  jsErrors.length = 0;

  // T3-创建: 点击新建文档 → 弹窗
  await pg.locator('button:has-text("新建文档")').first().click();
  await pg.waitForTimeout(1500);
  modal = pg.locator('.fixed.inset-0:visible').last();
  modalOpen = await modal.isVisible();
  console.log('  新建文档 → 弹窗:', modalOpen ? 'PASS' : 'FAIL');

  // 填写 - 限定在可见弹窗内
  await modal.locator('input[x-model="newDoc.title"]').fill('Doc-' + TS);
  await modal.locator('textarea[x-model="newDoc.content"]').fill('测试文档内容');
  await pg.waitForTimeout(500);

  // 提交
  await modal.locator('button:has-text("保存")').click();
  await pg.waitForTimeout(3000);
  bodyText = await pg.textContent('body');
  created = bodyText.includes('Doc-' + TS);
  console.log('  提交 → 数据可见:', created ? 'PASS' : 'FAIL');

  if (created) {
    const d = await pg.evaluate(() => {
      const el = document.querySelector('[x-data="knowledgeDocumentsPage()"]');
      const data = Alpine.$data(el);
      const doc = data.documents.find(d => d.title.includes('Doc-'));
      return doc ? doc.id : null;
    });
    if (d) await cleanup(pg, '/api/knowledge/documents/' + d);
  }
  console.log('  JS错误:', jsErrors.length === 0 ? 'PASS' : jsErrors.join('; '));
  results.push({ page: '知识文档', pass: modalOpen && created && jsErrors.length === 0 });

  // ===== 3. 知识搜索 =====
  console.log('\n--- 知识搜索 ---');
  await openTab(pg, 'ksearch', '高级搜索', 'fa-search', '/knowledge/search');
  jsErrors.length = 0;

  await pg.locator('#tab-content-ksearch input[x-model="query"]').fill('test');
  await pg.locator('#tab-content-ksearch button:has-text("搜索")').first().click();
  await pg.waitForTimeout(3000);
  console.log('  搜索执行 → 无报错: PASS');
  console.log('  JS错误:', jsErrors.length === 0 ? 'PASS' : jsErrors.join('; '));
  results.push({ page: '知识搜索', pass: jsErrors.length === 0 });

  // ===== 4. 文档模板 =====
  console.log('\n--- 文档模板 ---');
  await openTab(pg, 'tpl', '文档模板', 'fa-file-alt', '/knowledge/templates');
  jsErrors.length = 0;

  await pg.locator('button:has-text("创建模板")').first().click();
  await pg.waitForTimeout(1500);
  modal = pg.locator('.fixed.inset-0:visible').last();
  modalOpen = await modal.isVisible();
  console.log('  创建模板 → 弹窗:', modalOpen ? 'PASS' : 'FAIL');

  await modal.locator('input[x-model="form.name"]').fill('Tpl-' + TS);
  await modal.locator('textarea[x-model="form.content"]').fill('# 测试模板');
  await pg.waitForTimeout(500);

  await modal.locator('button:has-text("创建")').click();
  await pg.waitForTimeout(3000);
  bodyText = await pg.textContent('body');
  created = bodyText.includes('Tpl-' + TS);
  console.log('  提交 → 数据可见:', created ? 'PASS' : 'FAIL');

  if (created) {
    const d = await pg.evaluate(() => {
      const el = document.querySelector('[x-data="templatesPage()"]');
      const data = Alpine.$data(el);
      const t = data.templates.find(t => t.name.includes('Tpl-'));
      return t ? t.id : null;
    });
    if (d) await cleanup(pg, '/api/knowledge/templates/' + d);
  }
  console.log('  JS错误:', jsErrors.length === 0 ? 'PASS' : jsErrors.join('; '));
  results.push({ page: '文档模板', pass: modalOpen && created && jsErrors.length === 0 });

  // ===== 5. 代码资产 =====
  console.log('\n--- 代码资产 ---');
  await openTab(pg, 'assets', '代码资产', 'fa-archive', '/assets');
  jsErrors.length = 0;

  await pg.locator('button:has-text("创建资产")').first().click();
  await pg.waitForTimeout(1500);
  modal = pg.locator('.fixed.inset-0:visible').last();
  modalOpen = await modal.isVisible();
  console.log('  创建资产 → 弹窗:', modalOpen ? 'PASS' : 'FAIL');

  await modal.locator('input[x-model="newAsset.title"]').fill('Asset-' + TS);
  await modal.locator('textarea[x-model="newAsset.content"]').fill('print("hello")');
  await pg.waitForTimeout(500);

  await modal.locator('button:has-text("创建")').click();
  await pg.waitForTimeout(3000);
  bodyText = await pg.textContent('body');
  created = bodyText.includes('Asset-' + TS);
  console.log('  提交 → 数据可见:', created ? 'PASS' : 'FAIL');

  if (created) {
    const d = await pg.evaluate(() => {
      const el = document.querySelector('[x-data="assetsPage()"]');
      const data = Alpine.$data(el);
      const a = data.assets.find(a => a.title.includes('Asset-'));
      return a ? a.id : null;
    });
    if (d) await cleanup(pg, '/api/assets/' + d);
  }
  console.log('  JS错误:', jsErrors.length === 0 ? 'PASS' : jsErrors.join('; '));
  results.push({ page: '代码资产', pass: modalOpen && created && jsErrors.length === 0 });

  // ===== Summary =====
  console.log('\n=== SUMMARY ===');
  const passed = results.filter(r => r.pass).length;
  console.log(`${passed}/${results.length} passed\n`);
  results.forEach(r => console.log(`  ${r.pass ? 'PASS' : 'FAIL'} ${r.page}`));

  await browser.close();
})();
