const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  let passed = 0, failed = 0;
  const test = async (name, fn) => {
    try { await fn(); passed++; process.stdout.write('.'); }
    catch(e) { failed++; process.stdout.write('X'); console.log(`\n❌ ${name}: ${e.message.substring(0, 200)}`); }
  };

  // Login first
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  const clickMenu = async (label) => {
    await page.evaluate(() => document.querySelector('nav')?.scrollTo(0, 0));
    await page.waitForTimeout(300);
    const btns = await page.$$('button');
    for (const b of btns) {
      if ((await b.textContent().catch(()=>'')).includes(label)) { await b.click(); return; }
    }
    return false;
  };

  const getAlpineData = () => {
    return page.evaluate(() => {
      const tab = Array.from(document.querySelectorAll('[id^="tab-content-"]')).find(el => getComputedStyle(el).display !== 'none');
      if (!tab) return null;
      const root = tab.querySelector('[x-data]');
      if (!root) return null;
      try { return Alpine.$data(root); } catch(e) { return null; }
    });
  };

  // ===== 知识中心 =====
  console.log('\n=== 知识中心 UI ===');
  await test('页面加载', async () => {
    await clickMenu('知识中心'); await page.waitForTimeout(2000);
    const body = await page.textContent('body');
    if (!body.includes('知识库')) throw new Error('页面未加载');
  });

  await test('创建知识库', async () => {
    await page.evaluate(() => {
      const tab = Array.from(document.querySelectorAll('[id^="tab-content-"]')).find(el => getComputedStyle(el).display !== 'none');
      if (!tab) return;
      const root = tab.querySelector('[x-data]');
      if (!root) return;
      const data = Alpine.$data(root);
      if (data) { data.newKB.name = 'E2E-知识库'; data.newKB.description = 'E2E测试'; data.showCreateModal = true; }
    });
    await page.waitForTimeout(1000);
  });

  await test('提交创建表单', async () => {
    await page.evaluate(() => {
      const modal = Array.from(document.querySelectorAll('.fixed')).find(el => getComputedStyle(el).display !== 'none');
      if (!modal) return;
      modal.querySelectorAll('button').forEach(b => {
        if (b.textContent.trim() === '创建知识库' && getComputedStyle(b).display !== 'none') b.click();
      });
    });
    await page.waitForTimeout(2000);
  });

  await test('验证列表', async () => {
    const body = await page.textContent('body');
    if (!body.includes('E2E-知识库')) throw new Error('未找到');
  });

  // ===== 记忆中心 =====
  console.log('\n=== 记忆中心 UI ===');
  await test('页面加载', async () => {
    await clickMenu('记忆中心'); await page.waitForTimeout(2000);
    const body = await page.textContent('body');
    if (!body.includes('记忆')) throw new Error('页面未加载');
  });

  // ===== 全局技能 =====
  console.log('\n=== 全局技能 UI ===');
  await test('页面加载', async () => {
    await clickMenu('技能库'); await page.waitForTimeout(2000);
    const body = await page.textContent('body');
    if (!body.includes('技能')) throw new Error('页面未加载');
  });

  // ===== 代码沙箱 =====
  console.log('\n=== 代码沙箱 UI ===');
  await test('页面加载', async () => {
    await clickMenu('代码沙箱'); await page.waitForTimeout(2000);
    const ta = await page.$('textarea');
    if (!ta) throw new Error('无代码编辑器');
  });
  await test('执行代码', async () => {
    // Close any open modals first
    await page.evaluate(() => {
      document.querySelectorAll('.fixed').forEach(el => {
        if (getComputedStyle(el).display !== 'none') {
          el.querySelectorAll('button').forEach(b => {
            if (b.innerHTML.includes('times') || b.textContent.includes('取消')) b.click();
          });
        }
      });
    });
    await page.waitForTimeout(500);
    // Find sandbox textarea (the one with placeholder or inside sandbox page)
    const textareas = await page.$$('textarea');
    let sandboxTa = null;
    for (const ta of textareas) {
      const ph = await ta.getAttribute('placeholder').catch(() => '');
      if (ph && (ph.includes('代码') || ph.includes('Ctrl+Enter'))) { sandboxTa = ta; break; }
      const visible = await ta.isVisible().catch(() => false);
      if (visible && !sandboxTa) sandboxTa = ta;
    }
    if (!sandboxTa) throw new Error('无沙箱 textarea');
    await sandboxTa.fill('print("hello e2e")');
    await page.waitForTimeout(300);
    await page.evaluate(() => {
      document.querySelectorAll('button').forEach(b => {
        if (b.textContent.includes('运行') && b.offsetParent !== null) b.click();
      });
    });
    await page.waitForTimeout(3000);
  });

  // ===== 质量检查 =====
  console.log('\n=== 质量检查 UI ===');
  await test('页面加载', async () => {
    await clickMenu('质量检查'); await page.waitForTimeout(2000);
    const body = await page.textContent('body');
    if (!body.includes('质量检查') && !body.includes('代码')) throw new Error('页面未加载');
  });

  // ===== 审计日志 =====
  console.log('\n=== 审计日志 UI ===');
  await test('页面加载', async () => {
    await clickMenu('审计日志'); await page.waitForTimeout(2000);
    const body = await page.textContent('body');
    if (!body.includes('审计日志')) throw new Error('页面未加载');
  });

  const total = passed + failed;
  console.log(`\n\n${'='.repeat(40)}`);
  console.log(`E2E UI 测试: ${total} 项, ${passed} 通过, ${failed} 失败`);
  console.log(`${'='.repeat(40)}`);
  if (failed > 0) process.exit(1);
  await browser.close();
})();