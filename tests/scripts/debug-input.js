const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';

async function login(pg) { await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' }); await pg.fill('input[name="username"]', 'admin'); await pg.fill('input[name="password"]', 'admin123'); await pg.click('button[type="submit"]'); await pg.waitForTimeout(2000); }

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  await login(pg);

  pg.on('response', async resp => {
    if (resp.url().includes('/api/') && !resp.url().includes('stats') && !resp.url().includes('list') && !resp.url().includes('templates')) {
      console.log(`[API] ${resp.request().method()} ${resp.url().split('?')[0]} → ${resp.status()}`);
      try { const t = await resp.text(); if (t.length < 300) console.log(`  → ${t}`); } catch (e) {}
    }
  });

  console.log('=== 全局规则 - 完整流程 ===');
  await pg.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3000);

  // 打开弹窗
  await pg.locator('button', { hasText: '创建' }).first().click();
  await pg.waitForTimeout(1500);

  // 用 evaluate 设置值（确保 Alpine 数据绑定生效）
  await pg.evaluate((ts) => {
    const inputs = document.querySelectorAll('.fixed.inset-0 input, .fixed.inset-0 textarea');
    for (const inp of inputs) {
      const model = inp.getAttribute('x-model');
      if (model === 'form.name') {
        inp.value = '规则-' + ts;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
      if (model === 'form.content') {
        inp.value = '测试内容';
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  }, Date.now());
  await pg.waitForTimeout(500);

  // 检查 Alpine 数据是否已更新
  const formData = await pg.evaluate(() => {
    const el = document.querySelector('[x-data]');
    // Try different ways to access Alpine data
    if (el._x_dataStack) return { method: '_x_dataStack', name: el._x_dataStack[0]?.form?.name };
    if (el.__x) return { method: '__x', name: el.__x.$data?.form?.name };
    // Try accessing through Alpine's internal map
    const keys = Object.keys(el).filter(k => k.startsWith('_x'));
    return { method: 'keys', keys };
  });
  console.log('Form data:', formData);

  // 提交 - 用 evaluate + dispatchEvent 组合
  console.log('Submitting...');
  await pg.evaluate(() => {
    const btns = document.querySelectorAll('.fixed.inset-0 button');
    for (const b of btns) {
      const oc = b.getAttribute('@click');
      if (oc === 'createRule()') {
        // Trigger mousedown, mouseup, click sequence
        b.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
        b.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
        b.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        break;
      }
    }
  });
  await pg.waitForTimeout(3000);

  const isOpen = await pg.evaluate(() => {
    const modals = document.querySelectorAll('.fixed.inset-0');
    for (const m of modals) { if (m.offsetParent !== null) return true; }
    return false;
  });
  console.log('Modal still open:', isOpen);

  await browser.close();
})();
