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

  // 全局技能 - 编辑/删除按钮在哪
  console.log('=== 全局技能 列表结构 ===');
  await page.goto(`${BASE_URL}/skills/global`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  const skillHtml = await page.$eval('.grid > div:first-child', el => el.innerHTML.substring(0, 1000));
  console.log(skillHtml);

  // 我的技能 - 编辑/删除按钮在哪
  console.log('\n=== 我的技能 列表结构 ===');
  await page.goto(`${BASE_URL}/skills/personal`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  const mySkillHtml = await page.$eval('.grid > div:first-child', el => el.innerHTML.substring(0, 1500));
  console.log(mySkillHtml);

  // 全局规则 - 编辑/删除按钮在哪
  console.log('\n=== 全局规则 列表结构 ===');
  await page.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  const ruleHtml = await page.$eval('.grid > div:first-child', el => el.innerHTML.substring(0, 1000));
  console.log(ruleHtml);

  // 知识库管理 - 创建弹窗
  console.log('\n=== 知识库管理 创建弹窗 ===');
  await page.goto(`${BASE_URL}/knowledge/bases`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("创建知识库")');
  await page.waitForTimeout(1000);
  const kbModal = await page.$$eval('.fixed.inset-0', modals => modals.map(m => ({
    visible: m.offsetParent !== null,
    h2: [...m.querySelectorAll('h2,h3')].map(h => h.textContent.trim()),
    inputs: [...m.querySelectorAll('input, textarea, select')].map(el => ({
      model: el.getAttribute('x-model') || '',
      placeholder: el.placeholder || '',
    }))
  })).filter(m => m.visible));
  console.log(JSON.stringify(kbModal, null, 2));

  // 项目列表 - 创建弹窗
  console.log('\n=== 项目列表 创建弹窗 ===');
  await page.goto(`${BASE_URL}/projects`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("创建项目")');
  await page.waitForTimeout(1000);
  const projModal = await page.$$eval('.fixed.inset-0', modals => modals.map(m => ({
    visible: m.offsetParent !== null,
    h2: [...m.querySelectorAll('h2,h3')].map(h => h.textContent.trim()),
    inputs: [...m.querySelectorAll('input, textarea, select')].map(el => ({
      model: el.getAttribute('x-model') || '',
      placeholder: el.placeholder || '',
    }))
  })).filter(m => m.visible));
  console.log(JSON.stringify(projModal, null, 2));

  await browser.close();
})();
