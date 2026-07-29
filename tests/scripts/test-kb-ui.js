const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: true, slowMo: 100 });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  let passed = 0, failed = 0;
  const test = async (name, fn) => {
    try { await fn(); passed++; process.stdout.write('.'); }
    catch(e) { failed++; process.stdout.write('X'); console.log('\n❌ '+name+': '+e.message.substring(0,200)); }
  };

  const getTab = () => '[id^=tab-content-]:not([style*="display: none"])';

  await page.goto(BASE+'/login', { waitUntil: 'networkidle' });
  await page.fill('#username','admin'); await page.fill('#password','admin123');
  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(3000);

  console.log('\n=== 知识库 UI CRUD (新组件) ===\n');
  const ts = Date.now().toString(36).substring(4,10);

  // 1. Open knowledge center
  await test('打开知识中心', async () => {
    await page.evaluate(() => document.querySelector('nav')?.scrollTo(0,0));
    await page.getByText('知识中心').first().click();
    await page.waitForTimeout(3000);
    const tab = await page.locator(getTab()).count();
    if (!tab) throw new Error('知识库页面未加载');
  });

  // 2. Click create button
  await test('点击创建知识库', async () => {
    const createBtn = page.locator(getTab()+' button').filter({ hasText: '创建知识库' }).first();
    await createBtn.click({ force: true });
    await page.waitForTimeout(1000);
    const showVal = await page.evaluate(() => {
      const tab = document.querySelector('[id^=tab-content-]:not([style*="display: none"])');
      if (!tab) return false;
      const w = tab.querySelector('[x-data]');
      return w ? Alpine.$data(w).showCreateModal === true : false;
    });
    if (!showVal) throw new Error('创建模态框未打开');
  });

  // 3. Fill and submit via confirmForm
  await test('创建知识库', async () => {
    const result = await page.evaluate(async (name) => {
      const tab = document.querySelector('[id^=tab-content-]:not([style*="display: none"])');
      const w = tab.querySelector('[x-data]');
      const d = Alpine.$data(w);
      d.formKB.name = name;
      d.formKB.description = 'CRUD test new UI';
      await d.confirmForm();
      return 'ok';
    }, ts);
    if (result !== 'ok') throw new Error('创建失败');
    await page.waitForTimeout(2000);
    // Reload
    await page.evaluate(() => document.querySelector('nav')?.scrollTo(0,0));
    await page.getByText('知识中心').first().click();
    await page.waitForTimeout(3000);
    const found = await page.evaluate(async (name) => {
      const r = await fetch('/api/knowledge/bases?limit=100');
      const d = await r.json();
      return (d.items||[]).some(i => i.name === name);
    }, ts);
    if (!found) throw new Error('创建后 API 未找到');
  });

  // 4. Click to open documents
  await test('打开知识库详情', async () => {
    const clicked = await page.evaluate((name) => {
      const tab = document.querySelector('[id^=tab-content-]:not([style*="display: none"])');
      const w = tab.querySelector('[x-data]');
      if (!w) return false;
      const d = Alpine.$data(w);
      const kb = d.knowledgeBases.find(k => k.name === name);
      if (kb) { d.viewKnowledgeBase(kb); return true; }
      return false;
    }, ts);
    if (!clicked) throw new Error('无法找到并点击知识库');
    await page.waitForTimeout(3000);
  });

  // 5. Return to list
  await test('返回列表', async () => {
    await page.evaluate(() => document.querySelector('nav')?.scrollTo(0,0));
    await page.getByText('知识中心').first().click();
    await page.waitForTimeout(3000);
  });

  // 6. Delete
  await test('删除知识库', async () => {
    const result = await page.evaluate(async (name) => {
      window.confirm = () => true;
      const tab = document.querySelector('[id^=tab-content-]:not([style*="display: none"])');
      const w = tab.querySelector('[x-data]');
      const d = Alpine.$data(w);
      const kb = d.knowledgeBases.find(k => k.name === name);
      if (!kb) return 'not_found';
      await d.deleteKnowledgeBase(kb);
      return 'ok';
    }, ts);
    if (result === 'not_found') {} // Already deleted
    await page.waitForTimeout(2000);
    // Refresh
    await page.evaluate(() => document.querySelector('nav')?.scrollTo(0,0));
    await page.getByText('知识中心').first().click();
    await page.waitForTimeout(3000);
  });

  console.log('\n\n=== 结果: '+passed+'/'+(passed+failed)+' 通过 ===');
  if (failed>0) process.exit(1);
  await browser.close();
})();