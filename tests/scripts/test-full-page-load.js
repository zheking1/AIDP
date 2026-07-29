const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'http://192.168.0.100:8883';
const USERNAME = 'admin';
const PASSWORD = 'admin123';

// All pages to test (from menu.yaml + routes)
const PAGES = [
  // Hub pages
  { id: 'knowledge-hub', name: '知识中心', path: '/hub/knowledge', hub: true },
  { id: 'skills-hub', name: '技能库', path: '/hub/skills', hub: true },
  { id: 'memory-hub', name: '记忆中心', path: '/hub/memory', hub: true },

  // Knowledge center sub-pages
  { id: 'knowledge-bases', name: '知识库管理', path: '/knowledge/bases' },
  { id: 'knowledge-docs', name: '文档管理', path: '/knowledge/documents' },
  { id: 'knowledge-search', name: '高级搜索', path: '/knowledge/search' },
  { id: 'knowledge-templates', name: '文档模板', path: '/knowledge/templates' },
  { id: 'assets', name: '代码资产', path: '/assets' },

  // Skills hub sub-pages
  { id: 'skills-global', name: '全局技能', path: '/skills/global' },
  { id: 'skills-personal', name: '我的技能', path: '/skills/personal' },
  { id: 'rules-global', name: '全局规则', path: '/rules/global' },
  { id: 'rules-personal', name: '我的规则', path: '/rules/personal' },
  { id: 'agents', name: 'Agent管理', path: '/agents' },
  { id: 'workflows', name: '流程引擎', path: '/workflows' },

  // Memory hub sub-pages
  { id: 'memory-list', name: '记忆列表', path: '/memory/memories' },
  { id: 'memory-graph', name: '记忆图谱', path: '/memory/graph' },
  { id: 'memory-search', name: '记忆检索', path: '/memory/search' },

  // Dev tools
  { id: 'sandbox', name: '代码沙箱', path: '/sandbox' },
  { id: 'quality', name: '质量检查', path: '/quality' },

  // Admin pages
  { id: 'admin-users', name: '用户管理', path: '/admin/users' },
  { id: 'admin-models', name: '模型管理', path: '/admin/models' },
  { id: 'admin-settings', name: '系统设置', path: '/admin/settings' },

  // Profile
  { id: 'profile', name: '个人资料', path: '/profile' },

  // Projects
  { id: 'projects', name: '项目列表', path: '/projects' },
];

const results = [];

async function runTest() {
  console.log('=== WebUI 全量页面加载测试 ===\n');
  console.log(`目标: ${BASE_URL}`);
  console.log(`页面数: ${PAGES.length}\n`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', error => {
    consoleErrors.push(error.message);
  });

  // Login
  console.log('1. 登录中...');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[name="username"]', USERNAME);
  await page.fill('input[name="password"]', PASSWORD);
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle' }),
    page.click('button[type="submit"]')
  ]);
  console.log(`   登录成功，当前URL: ${page.url()}`);

  // Wait for workspace to load
  await page.waitForTimeout(2000);

  // Test each page
  console.log('\n2. 开始页面加载测试...\n');
  let passCount = 0;
  let failCount = 0;

  for (const pg of PAGES) {
    consoleErrors.length = 0; // Clear errors for each page

    console.log(`   测试: ${pg.name} (${pg.path})`);

    try {
      // Navigate directly to the page via workspace
      // Use partial mode to load content
      const response = await page.goto(`${BASE_URL}${pg.path}?partial=1`, {
        waitUntil: 'networkidle',
        timeout: 15000
      });

      const status = response.status();
      const html = await page.content();

      // Check for errors
      const hasErrorText = html.includes('加载失败: ') || html.includes('请求失败: ') || html.includes('"detail"') || html.includes('Not Found');
      const hasContent = html.length > 100; // Should have substantial content
      const hasJsError = consoleErrors.length > 0;

      const passed = status === 200 && hasContent && !hasErrorText && !hasJsError;

      if (passed) {
        console.log(`      ✅ PASS (status=${status}, content=${html.length}b)`);
        passCount++;
      } else {
        console.log(`      ❌ FAIL (status=${status}, content=${html.length}b, errors=${hasJsError ? consoleErrors.join('; ') : hasErrorText ? '页面错误' : '无内容'})`);
        failCount++;
      }

      results.push({
        id: pg.id,
        name: pg.name,
        path: pg.path,
        status,
        passed,
        contentLength: html.length,
        errors: hasJsError ? consoleErrors : (hasErrorText ? ['页面显示错误'] : [])
      });
    } catch (e) {
      console.log(`      ❌ FAIL (异常: ${e.message})`);
      failCount++;
      results.push({
        id: pg.id,
        name: pg.name,
        path: pg.path,
        status: 0,
        passed: false,
        contentLength: 0,
        errors: [e.message]
      });
    }
  }

  // Summary
  console.log('\n=== 测试结果 ===');
  console.log(`总页面数: ${PAGES.length}`);
  console.log(`通过: ${passCount}`);
  console.log(`失败: ${failCount}`);
  console.log(`通过率: ${((passCount / PAGES.length) * 100).toFixed(1)}%\n`);

  // Failed pages detail
  const failedPages = results.filter(r => !r.passed);
  if (failedPages.length > 0) {
    console.log('=== 失败详情 ===');
    for (const f of failedPages) {
      console.log(`  ${f.name} (${f.path}): ${f.errors.join(', ')}`);
    }
  }

  // Save report
  const report = {
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    summary: { total: PAGES.length, passed: passCount, failed: failCount },
    results: results
  };
  fs.writeFileSync('test-reports-page-load.json', JSON.stringify(report, null, 2));
  console.log('\n报告已保存到 test-reports-page-load.json');

  await browser.close();
}

runTest().catch(e => {
  console.error('测试异常:', e);
  process.exit(1);
});
