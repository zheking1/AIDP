const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  
  const errors = [];
  const failedRequests = [];

  page.on('console', msg => {
    const text = msg.text();
    if (msg.type() === 'error' || msg.type() === 'warning') {
      errors.push({ type: msg.type(), text: text.substring(0, 200) });
    }
  });
  page.on('pageerror', e => errors.push({ type: 'pageerror', text: e.message.substring(0, 200) }));
  
  page.on('response', response => {
    if (response.status() >= 400) {
      failedRequests.push({ url: response.url().substring(0, 100), status: response.status() });
    }
  });

  const ck = async (label, fn) => {
    await fn();
    await page.waitForTimeout(3500);
    console.log(`   ${label}: 控制台${errors.length}个, ${failedRequests.length}个失败请求`);
    if (errors.length) errors.forEach(e => console.log(`     ${e.type}: ${e.text.substring(0, 120)}`));
    if (failedRequests.length) failedRequests.forEach(r => console.log(`     ${r.status}: ${r.url}`));
    errors.splice(0); failedRequests.splice(0);
  };

  const click = async (text) => {
    const btns = await page.$$('button');
    for (const b of btns) {
      if ((await b.textContent().catch(()=>'')).includes(text)) { await b.click(); return; }
    }
  };

  console.log('1. 登录...');
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 20000 });
  await page.waitForTimeout(1000);
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);
  console.log(`   登录: 控制台${errors.length}个, ${failedRequests.length}个失败请求`);
  errors.splice(0); failedRequests.splice(0);

  console.log('2. Hub 页面...');
  await ck('知识中心', () => click('知识中心'));
  await ck('技能库', () => click('技能库'));
  await ck('记忆中心', () => click('记忆中心'));
  await ck('代码沙箱', () => click('代码沙箱'));
  await ck('质量检查', () => click('质量检查'));

  console.log('3. 系统管理...');
  await page.evaluate(() => document.querySelector('nav')?.scrollTo(0, 1000));
  await page.waitForTimeout(500);
  await ck('用户管理', () => click('用户管理'));
  await ck('系统设置', () => click('系统设置'));

  console.log('4. 审计日志...');
  // 可能需要滚动找到审计日志按钮
  await page.evaluate(() => document.querySelector('nav')?.scrollTo(0, 2000));
  await page.waitForTimeout(500);
  await ck('审计日志', () => click('审计日志'));

  console.log('\n全部测试完成');
  await page.waitForTimeout(2000);
  await browser.close();
})();