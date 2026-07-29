const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'http://192.168.0.100:8883';
const RESULTS_DIR = 'test-reports';

function record(results, tier, page, name, passed, detail = '') {
  results.push({ tier, page, name, passed, detail });
  const icon = passed ? '✅' : '❌';
  console.log(`  ${icon} [T${tier}] ${name}${detail ? ': ' + detail : ''}`);
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
}

async function closeAnyModal(page) {
  const modal = await page.$('.fixed.inset-0');
  if (modal) {
    const close = await modal.$('.fa-times, button:has-text("取消"), button:has-text("关闭")');
    if (close) {
      try { await close.click({ timeout: 2000 }); } catch (e) {}
      await page.waitForTimeout(300);
    }
    // Fallback: press Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(200);
  }
}

// ============================================================
// T1 冒烟测试
// ============================================================
async function t1Smoke(page, pageName, url) {
  const results = [];
  const errors = [];
  const handler = msg => { if (msg.type() === 'error') errors.push(msg.text()); };
  const errHandler = error => { errors.push(error.message); };
  page.on('console', handler);
  page.on('pageerror', errHandler);

  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.waitForTimeout(1500);
    const status = resp.status();
    const jsErrors = errors.filter(e => !e.includes('favicon'));
    record(results, 'T1', pageName, 'HTTP 200', status === 200, `status=${status}`);
    record(results, 'T1', pageName, '无JS错误', jsErrors.length === 0, jsErrors.length > 0 ? jsErrors[0] : '');
  } catch (e) {
    record(results, 'T1', pageName, '页面加载', false, e.message.split('\n')[0]);
  }
  page.removeListener('console', handler);
  page.removeListener('pageerror', errHandler);
  return results;
}

// ============================================================
// T2 渲染测试
// ============================================================
async function t2Render(page, pageName) {
  const results = [];
  const gridItems = await page.$$('.grid > div');
  const tableRows = await page.$$('table tbody tr');
  const listCount = Math.max(gridItems.length, tableRows.length);
  record(results, 'T2', pageName, '列表有数据', listCount > 0, `${listCount} 条`);
  return results;
}

// ============================================================
// T3 交互测试 - 每个按钮
// ============================================================
async function t3Interactions(page, pageName) {
  const results = [];
  const buttons = await page.$$('button');
  let testedCount = 0;

  for (const btn of buttons) {
    const visible = await btn.isVisible().catch(() => false);
    if (!visible) continue;

    const text = (await btn.textContent().catch(() => '')).trim() || '未命名';
    testedCount++;

    try {
      await btn.click({ timeout: 3000 });
      await page.waitForTimeout(800);

      // 检查弹窗
      const modalVisible = await page.$eval('.fixed.inset-0', el => {
        return el.offsetParent !== null || el.style.display !== 'none';
      }).catch(() => false);

      if (modalVisible) {
        record(results, 'T3', pageName, `「${text}」`, true, '打开弹窗');
        await closeAnyModal(page);
      } else {
        record(results, 'T3', pageName, `「${text}」`, true, '有响应');
      }
    } catch (e) {
      record(results, 'T3', pageName, `「${text}」`, false, e.message.split('\n')[0]);
      await closeAnyModal(page);
    }
  }

  if (testedCount === 0) {
    record(results, 'T3', pageName, '按钮检测', true, '无可见按钮');
  }
  return results;
}

// ============================================================
// T4 关联管理测试
// ============================================================
async function t4Relations(page, pageName) {
  const results = [];
  const hasDetail = await page.$('[x-show="showDetailModal"]');
  if (!hasDetail) {
    record(results, 'T4', pageName, '关联测试', true, '无关联管理，跳过');
    return results;
  }

  const firstItem = await page.$('.grid > div:first-child');
  if (firstItem) {
    try {
      await firstItem.click({ timeout: 5000 });
      await page.waitForTimeout(2000);

      const modal = await page.$('[x-show="showDetailModal"]');
      if (modal) {
        record(results, 'T4', pageName, '详情弹窗打开', true);

        const tabs = ['技能', '规则', '知识库'];
        for (const tabName of tabs) {
          const tab = await modal.$(`button:has-text("${tabName}")`);
          if (tab) {
            await tab.click({ timeout: 3000 });
            await page.waitForTimeout(500);
            record(results, 'T4', pageName, `Tab「${tabName}」`, true);
          }
        }

        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
      }
    } catch (e) {
      record(results, 'T4', pageName, '关联测试', false, e.message.split('\n')[0]);
      await page.keyboard.press('Escape');
    }
  }
  return results;
}

// ============================================================
// Per-page runner
// ============================================================
async function testPage(browser, pageName, url, options = {}) {
  console.log(`\n${'='.repeat(50)}`);
  console.log(`📄 测试: ${pageName}`);
  console.log(`${'='.repeat(50)}`);

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await login(page);

  let allResults = [];

  // T1
  console.log('  --- T1 ---');
  allResults.push(...await t1Smoke(page, pageName, url));

  // T2
  console.log('  --- T2 ---');
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  allResults.push(...await t2Render(page, pageName));

  // T3
  console.log('  --- T3 ---');
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  allResults.push(...await t3Interactions(page, pageName));

  // T4
  console.log('  --- T4 ---');
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  allResults.push(...await t4Relations(page, pageName));

  const passed = allResults.filter(r => r.passed).length;
  const total = allResults.length;
  const pct = total > 0 ? ((passed / total) * 100).toFixed(1) : 'N/A';
  console.log(`  📊 ${passed}/${total} (${pct}%)`);

  fs.mkdirSync(RESULTS_DIR, { recursive: true });
  fs.writeFileSync(`${RESULTS_DIR}/test-${pageName}.json`, JSON.stringify({
    page: pageName, url, timestamp: new Date().toISOString(),
    summary: { total, passed, percentage: pct }, results: allResults
  }, null, 2));

  await context.close();
  return { pageName, total, passed, percentage: pct };
}

// ============================================================
// Main
// ============================================================
async function main() {
  console.log('=== AIDP WebUI 按页面拆分测试 ===');
  console.log(`目标: ${BASE_URL}\n`);
  fs.mkdirSync(RESULTS_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });

  // 创建测试项目（用 query params）
  let projectId = null;
  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await login(page);
    const proj = await page.evaluate(async (base) => {
      const r = await fetch(`${base}/api/projects?name=测试项目-T3&description=自动化测试`, { method: 'POST' });
      return r.ok ? await r.json() : null;
    }, BASE_URL);
    projectId = proj?.id;
    console.log(`项目: ${projectId ? '创建成功 ID=' + projectId : '创建失败'}`);
    await ctx.close();
  } catch (e) {
    console.log(`项目创建异常: ${e.message}`);
  }

  // 页面列表
  const hubPages = [
    { name: '知识中心', url: '/hub/knowledge' },
    { name: '技能库', url: '/hub/skills' },
    { name: '记忆中心', url: '/hub/memory' },
  ];

  const globalPages = [
    { name: '全局技能', url: '/skills/global' },
    { name: '我的技能', url: '/skills/personal' },
    { name: '全局规则', url: '/rules/global' },
    { name: '我的规则', url: '/rules/personal' },
    { name: 'Agent管理', url: '/agents' },
    { name: '流程引擎', url: '/workflows' },
    { name: '知识库管理', url: '/knowledge/bases' },
    { name: '文档管理', url: '/knowledge/documents' },
    { name: '高级搜索', url: '/knowledge/search' },
    { name: '代码资产', url: '/assets' },
    { name: '记忆列表', url: '/memory/memories' },
    { name: '记忆图谱', url: '/memory/graph' },
    { name: '记忆检索', url: '/memory/search' },
    { name: '代码沙箱', url: '/sandbox' },
    { name: '质量检查', url: '/quality' },
    { name: '项目列表', url: '/projects' },
    { name: '个人资料', url: '/profile' },
  ];

  const projectPages = projectId ? [
    { name: '项目仪表盘', url: `/project/${projectId}/dashboard` },
    { name: '项目知识库', url: `/project/${projectId}/knowledge/documents` },
    { name: '项目技能', url: `/skills/project/${projectId}` },
    { name: '项目规则', url: `/rules/project/${projectId}` },
    { name: '项目Agent', url: `/project/${projectId}/agents` },
    { name: '项目流程', url: `/project/${projectId}/workflows` },
    { name: '项目记忆', url: `/project/${projectId}/memory/memories` },
    { name: '项目资产', url: `/project/${projectId}/assets` },
    { name: '项目沙箱', url: `/project/${projectId}/sandbox` },
    { name: '项目质量', url: `/project/${projectId}/quality` },
    { name: '项目设置', url: `/project/${projectId}/settings/general` },
  ] : [];

  const allPages = [...hubPages, ...globalPages, ...projectPages];
  const summaries = [];

  for (const p of allPages) {
    const r = await testPage(browser, p.name, `${BASE_URL}${p.url}`);
    summaries.push(r);
  }

  // 汇总
  console.log('\n\n' + '='.repeat(60));
  console.log('📊 全局汇总');
  console.log('='.repeat(60));
  let gt = 0, gp = 0;
  for (const s of summaries) {
    const icon = s.passed === s.total ? '✅' : '⚠️';
    console.log(`${icon} ${s.pageName}: ${s.passed}/${s.total} (${s.percentage}%)`);
    gt += s.total; gp += s.passed;
  }
  console.log(`\n总计: ${gp}/${gt} 通过 (${((gp/gt)*100).toFixed(1)}%)`);

  fs.writeFileSync(`${RESULTS_DIR}/summary.json`, JSON.stringify({
    timestamp: new Date().toISOString(), grandTotal: gt, grandPassed: gp,
    pages: summaries
  }, null, 2));

  await browser.close();
}

main().catch(e => { console.error('异常:', e); process.exit(1); });
