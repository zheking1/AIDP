const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await login(page);

  // Intercept ALL network
  page.on('response', async resp => {
    if (resp.url().includes('/api/')) {
      console.log(`[API] ${resp.request().method()} ${resp.url().split('?')[0]} → ${resp.status()}`);
    }
  });
  page.on('requestfailed', req => {
    if (req.url().includes('/api/')) console.log(`[FAIL] ${req.url()} → ${req.failure()?.errorText}`);
  });

  // Test 1: 全局规则 - 用 evaluate 检查 Alpine 状态
  console.log('=== 全局规则 ===');
  await page.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  // 打开弹窗
  await page.click('button:has-text("创建")');
  await page.waitForTimeout(1500);

  // 检查弹窗内实际的 x-model
  const ruleModels = await page.$$eval('.fixed.inset-0 [x-model]', els => els.map(el => ({
    model: el.getAttribute('x-model'),
    tag: el.tagName,
    vis: el.offsetParent !== null
  })));
  console.log('Rule models:', JSON.stringify(ruleModels.filter(m => m.vis), null, 2));

  // 填写并提交
  const nameField = await page.$('.fixed.inset-0 [x-model="form.name"]');
  if (nameField) {
    await nameField.fill(`规则-${Date.now()}`);
    console.log('Filled name');
  }
  const contentField = await page.$('.fixed.inset-0 [x-model="form.content"]');
  if (contentField) {
    await contentField.fill('测试内容');
    console.log('Filled content');
  }

  // 找到弹窗内的创建按钮
  const createBtns = await page.$$('.fixed.inset-0 button');
  for (const b of createBtns) {
    const txt = (await b.textContent().catch(() => '')).trim();
    const onclick = await b.evaluate(el => el.getAttribute('@click') || el.getAttribute('x-on:click') || '');
    const vis = await b.isVisible().catch(() => false);
    if (vis) console.log(`  Button: "${txt}" onclick="${onclick}"`);
  }

  // 点击 createRule 按钮
  const btn = await page.$('.fixed.inset-0 button[\\@click="createRule()"]');
  if (btn) {
    console.log('Clicking createRule...');
    await btn.click();
    await page.waitForTimeout(3000);
  } else {
    console.log('createRule button not found, trying text match...');
    const allBtns = await page.$$('.fixed.inset-0 button');
    for (const b of allBtns) {
      const txt = (await b.textContent().catch(() => '')).trim();
      const vis = await b.isVisible().catch(() => false);
      if (vis && txt === '创建') {
        console.log('Clicking 创建 button by text...');
        await b.click();
        await page.waitForTimeout(3000);
        break;
      }
    }
  }

  // Test 2: 我的技能 - 检查实际 model
  console.log('\n=== 我的技能 ===');
  await page.goto(`${BASE_URL}/skills/personal`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await page.click('button:has-text("创建技能")');
  await page.waitForTimeout(1500);

  const skillModels = await page.$$eval('.fixed.inset-0 [x-model]', els => els.map(el => ({
    model: el.getAttribute('x-model'),
    tag: el.tagName,
    vis: el.offsetParent !== null
  })));
  console.log('Skill models:', JSON.stringify(skillModels.filter(m => m.vis), null, 2));

  // 找弹窗内按钮
  const skillBtns = await page.$$('.fixed.inset-0 button');
  for (const b of skillBtns) {
    const txt = (await b.textContent().catch(() => '')).trim();
    const onclick = await b.evaluate(el => el.getAttribute('@click') || '');
    const vis = await b.isVisible().catch(() => false);
    if (vis) console.log(`  Button: "${txt}" onclick="${onclick}"`);
  }

  await browser.close();
})();
