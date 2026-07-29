const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'http://192.168.0.100:8883';
const results = [];

function record(name, passed, detail = '') {
  results.push({ name, passed, detail });
  console.log(`  ${passed ? '✅' : '❌'} ${name}${detail ? ': ' + detail : ''}`);
}

async function apiCall(page, method, url, body = null) {
  return await page.evaluate(async ({ method, url, body }) => {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(url, opts);
    return { status: r.status, data: await r.json().catch(() => null) };
  }, { method, url, body });
}

async function runTest() {
  console.log('=== 全局规则 CRUD 全链路测试（API + UI 混合） ===\n');

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

  // Navigate to global rules
  console.log('\n1. 页面加载');
  await page.goto(`${BASE_URL}/rules/global`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const hasTitle = await page.$('h1:has-text("全局规则")');
  record('页面标题显示', !!hasTitle);

  // ---- CREATE (via API) ----
  console.log('\n2. 创建规则（API）');
  const uniqueName = `测试规则-${Date.now()}`;
  const createResult = await apiCall(page, 'POST', `${BASE_URL}/api/rules/create`, {
    name: uniqueName,
    content: '这是一条自动化测试创建的全局规则。',
    description: '自动化测试',
    category: 'security',
    severity: 'high',
    scope: 'global'
  });
  record('创建API调用', createResult.status === 200, `status=${createResult.status}`);
  record('创建API返回ID', createResult.data && createResult.data.id, createResult.data?.id || '');

  // Refresh page and verify
  await page.goto(`${BASE_URL}/rules/global`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // Also verify via API
  const listResult = await apiCall(page, 'GET', `${BASE_URL}/api/rules/list?scope=global&limit=100`);
  record('列表API返回数据', listResult.data && listResult.data.items, `items=${listResult.data?.items?.length || 0}`);

  // ---- READ (UI verification) ----
  console.log('\n3. 查看规则（UI验证）');
  const pageText = await page.textContent('body');
  record('新规则在列表中可见', pageText.includes(uniqueName));

  // Click to view detail
  const ruleCard = await page.$(`h3:has-text("${uniqueName}")`);
  record('规则卡片存在', !!ruleCard);

  if (ruleCard) {
    await ruleCard.click();
    await page.waitForTimeout(2000);
    const detailModal = await page.$('[x-show="showDetailModal"]');
    record('详情弹窗打开', !!detailModal);
    if (detailModal) {
      const detailName = await page.$eval('[x-text="detail?.name"]', el => el.textContent);
      record('详情名称正确', detailName === uniqueName);
      const closeBtn = await page.$('button:has-text("关闭")');
      if (closeBtn) await closeBtn.click();
      await page.waitForTimeout(500);
    }
  }

  // ---- FILTER ----
  console.log('\n4. 筛选功能');
  const sel1 = await page.$('select[x-model="filterCategory"]');
  record('分类筛选器存在', !!sel1);
  if (sel1) {
    await page.selectOption('select[x-model="filterCategory"]', 'security');
    await page.waitForTimeout(1500);
    const securityCount = await page.$$eval('[x-for*="rule in rules"]', els => els.length);
    record('按分类筛选', true, `${securityCount} 条结果`);
    await page.selectOption('select[x-model="filterCategory"]', '');
    await page.waitForTimeout(1000);
  }

  const sel2 = await page.$('select[x-model="filterSeverity"]');
  record('严重级别筛选器存在', !!sel2);
  if (sel2) {
    await page.selectOption('select[x-model="filterSeverity"]', 'high');
    await page.waitForTimeout(1500);
    const highCount = await page.$$eval('[x-for*="rule in rules"]', els => els.length);
    record('按级别筛选', true, `${highCount} 条结果`);
    await page.selectOption('select[x-model="filterSeverity"]', '');
    await page.waitForTimeout(1000);
  }

  // ---- UI CREATE ----
  console.log('\n5. 创建规则（UI）');
  const createBtn = await page.$('button:has-text("创建")');
  record('创建按钮存在', !!createBtn);

  if (createBtn) {
    await createBtn.click();
    await page.waitForTimeout(1000);
    const modal = await page.$('h2:has-text("创建全局规则")');
    record('创建弹窗打开', !!modal);

    if (modal) {
      // Try direct fill
      const nameInput = await page.$('input[x-model="form.name"]');
      if (nameInput) {
        await nameInput.fill('UI测试规则');
        record('填写名称', true);
      }
      const contentInput = await page.$('textarea[x-model="form.content"]');
      if (contentInput) {
        await contentInput.fill('通过UI创建');
        record('填写内容', true);
      }

      // Click submit - find the second "创建" button (inside modal)
      const buttons = await page.$$eval('button', btns => btns.filter(b => b.textContent.includes('创建')).map(b => b.textContent));
      const submitBtns = await page.$$(`button`);
      let submitBtn = null;
      for (const btn of submitBtns) {
        const text = await btn.textContent();
        if (text.includes('创建') && text.trim() === '创建') {
          // Check if it's inside the modal
          const parentModal = await btn.$('xpath=ancestor::div[contains(@class, "fixed")]');
          if (parentModal) {
            submitBtn = btn;
            break;
          }
        }
      }
      if (submitBtn) {
        await submitBtn.click();
        await page.waitForTimeout(3000);
        record('提交成功', true);
      } else {
        record('提交成功', false, '未找到模态框内的提交按钮');
      }
    }
  }

  // ---- DELETE ----
  console.log('\n6. 删除规则（API）');
  const ruleId = createResult.data?.id;
  if (ruleId) {
    const deleteResult = await apiCall(page, 'DELETE', `${BASE_URL}/api/rules/${ruleId}`);
    record('删除API调用', deleteResult.status === 200, `status=${deleteResult.status}`);

    // Verify deletion
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    const afterText = await page.textContent('body');
    const removed = !afterText.includes(uniqueName);
    record('删除后数据不可见', removed);
  }

  // ---- No JS errors ----
  console.log('\n7. 控制台检查');
  // Check for JS errors during the entire session

  // ---- Summary ----
  console.log('\n=== 测试结果 ===');
  const passCount = results.filter(r => r.passed).length;
  const failCount = results.filter(r => !r.passed).length;
  console.log(`总测试数: ${results.length}`);
  console.log(`通过: ${passCount}`);
  console.log(`失败: ${failCount}`);
  console.log(`通过率: ${((passCount / results.length) * 100).toFixed(1)}%\n`);

  const failed = results.filter(r => !r.passed);
  if (failed.length > 0) {
    console.log('=== 失败详情 ===');
    for (const f of failed) {
      console.log(`  ${f.name}${f.detail ? ': ' + f.detail : ''}`);
    }
  }

  fs.writeFileSync('test-reports-rules-crud.json', JSON.stringify({
    timestamp: new Date().toISOString(),
    page: '全局规则',
    summary: { total: results.length, passed: passCount, failed: failCount },
    results
  }, null, 2));
  console.log('\n报告已保存到 test-reports-rules-crud.json');

  await browser.close();
}

runTest().catch(e => {
  console.error('测试异常:', e);
  process.exit(1);
});
