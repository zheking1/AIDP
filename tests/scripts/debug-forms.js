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

  // Debug 1: 全局技能 - 创建弹窗结构
  console.log('=== 全局技能 创建弹窗 ===');
  await page.goto(`${BASE_URL}/skills/global`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("创建")');
  await page.waitForTimeout(1000);

  const skillModal = await page.$$eval('.fixed.inset-0', modals => modals.map(m => ({
    visible: m.offsetParent !== null || m.style.display !== 'none',
    html: m.innerHTML.substring(0, 500)
  })));
  console.log('Modals:', JSON.stringify(skillModal, null, 2));

  // Debug 2: 全局规则 - 提交按钮
  console.log('\n=== 全局规则 提交按钮 ===');
  await page.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("创建")');
  await page.waitForTimeout(1000);

  const ruleBtns = await page.$$eval('.fixed.inset-0 button', btns => btns.map(b => ({
    text: b.textContent.trim(),
    onclick: b.getAttribute('@click') || '',
    visible: b.offsetParent !== null
  })));
  console.log('Rule modal buttons:', JSON.stringify(ruleBtns, null, 2));

  // Debug 3: 我的技能 - 列表项按钮
  console.log('\n=== 我的技能 列表项按钮 ===');
  await page.goto(`${BASE_URL}/skills/personal`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  const gridItems = await page.$$('.grid > div');
  if (gridItems.length > 0) {
    const itemBtns = await gridItems[0].$$eval('button', btns => btns.map(b => ({
      text: b.textContent.trim().substring(0, 30),
      title: b.title || '',
      classes: b.className.substring(0, 50),
      onclick: b.getAttribute('@click') || '',
      visible: b.offsetParent !== null
    })));
    console.log('First item buttons:', JSON.stringify(itemBtns, null, 2));
  }

  // Debug 4: 代码资产 - 创建弹窗
  console.log('\n=== 代码资产 创建弹窗 ===');
  await page.goto(`${BASE_URL}/assets`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("创建资产")');
  await page.waitForTimeout(1000);

  const assetModal = await page.$$eval('.fixed.inset-0', modals => modals.map(m => ({
    visible: m.offsetParent !== null,
    inputs: [...m.querySelectorAll('input, textarea, select')].map(el => ({
      tag: el.tagName,
      model: el.getAttribute('x-model') || '',
      placeholder: el.placeholder || '',
      type: el.type || ''
    }))
  })));
  console.log('Asset modal:', JSON.stringify(assetModal, null, 2));

  // Debug 5: 记忆列表 - 创建弹窗
  console.log('\n=== 记忆列表 创建弹窗 ===');
  await page.goto(`${BASE_URL}/memory/memories`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("新建记忆")');
  await page.waitForTimeout(1000);

  const memModal = await page.$$eval('.fixed.inset-0', modals => modals.map(m => ({
    visible: m.offsetParent !== null,
    inputs: [...m.querySelectorAll('input, textarea, select')].map(el => ({
      tag: el.tagName,
      model: el.getAttribute('x-model') || '',
      placeholder: el.placeholder || '',
      type: el.type || ''
    })),
    buttons: [...m.querySelectorAll('button')].map(b => ({
      text: b.textContent.trim().substring(0, 30),
      onclick: b.getAttribute('@click') || ''
    }))
  })));
  console.log('Memory modal:', JSON.stringify(memModal, null, 2));

  await browser.close();
})();
