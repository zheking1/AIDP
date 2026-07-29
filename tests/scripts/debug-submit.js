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

  // Intercept network requests
  page.on('response', async resp => {
    if (resp.url().includes('/api/') && resp.request().method() !== 'GET') {
      console.log(`[API] ${resp.request().method()} ${resp.url()} → ${resp.status()}`);
      try { const body = await resp.text(); console.log(`  Body: ${body.substring(0, 200)}`); } catch (e) {}
    }
  });

  page.on('requestfailed', req => {
    if (req.url().includes('/api/')) console.log(`[FAIL] ${req.method()} ${req.url()} → ${req.failure()?.errorText}`);
  });

  // Test 1: 全局规则创建
  console.log('=== 全局规则创建 ===');
  await page.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("创建")');
  await page.waitForTimeout(1000);

  await page.fill('[x-model="form.name"]', `规则测试-${Date.now()}`);
  await page.fill('[x-model="form.content"]', '测试内容');
  await page.waitForTimeout(500);

  // 点击提交
  const submitBtn = await page.$('button[\\@click="createRule()"]');
  console.log('Submit button found:', !!submitBtn);
  if (submitBtn) {
    await submitBtn.click();
    await page.waitForTimeout(3000);
  }

  // Test 2: 我的技能创建
  console.log('\n=== 我的技能创建 ===');
  await page.goto(`${BASE_URL}/skills/personal`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("创建技能")');
  await page.waitForTimeout(1000);

  // 检查弹窗内的所有 x-model 字段
  const models = await page.$$eval('.fixed.inset-0 [x-model]', els => els.map(el => ({
    model: el.getAttribute('x-model'),
    tag: el.tagName,
    visible: el.offsetParent !== null
  })));
  console.log('Models:', JSON.stringify(models, null, 2));

  // 尝试用 evaluate 直接调用 Alpine
  await page.evaluate(() => {
    const el = document.querySelector('[x-data]');
    if (el && el.__x) {
      console.log('Alpine data:', JSON.stringify(Object.keys(el.__x.$data)));
    }
  });

  await browser.close();
})();
