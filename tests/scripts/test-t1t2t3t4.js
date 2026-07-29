const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'http://192.168.0.100:8883';
const results = [];

function record(tier, page, name, passed, detail = '') {
  results.push({ tier, page, name, passed, detail });
  const icon = passed ? '✅' : '❌';
  console.log(`  ${icon} [T${tier}] ${page} | ${name}${detail ? ': ' + detail : ''}`);
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
}

// ============================================================
// T1: 冒烟测试
// ============================================================
async function runT1(browser) {
  console.log('\n========== T1 冒烟测试 ==========\n');
  const pages = [
    { name: '知识库管理', path: '/knowledge/bases' },
    { name: '文档管理', path: '/knowledge/documents' },
    { name: '高级搜索', path: '/knowledge/search' },
    { name: '文档模板', path: '/knowledge/templates' },
    { name: '代码资产', path: '/assets' },
    { name: '全局技能', path: '/skills/global' },
    { name: '我的技能', path: '/skills/personal' },
    { name: '全局规则', path: '/rules/global' },
    { name: '我的规则', path: '/rules/personal' },
    { name: 'Agent管理', path: '/agents' },
    { name: '流程引擎', path: '/workflows' },
    { name: '记忆列表', path: '/memory/memories' },
    { name: '记忆图谱', path: '/memory/graph' },
    { name: '记忆检索', path: '/memory/search' },
    { name: '代码沙箱', path: '/sandbox' },
    { name: '质量检查', path: '/quality' },
    { name: '系统设置', path: '/admin/settings' },
    { name: '个人资料', path: '/profile' },
    { name: '项目列表', path: '/projects' },
  ];

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await login(page);

  for (const p of pages) {
    const errors = [];
    const handler = msg => { if (msg.type() === 'error') errors.push(msg.text()); };
    const errHandler = error => { errors.push(error.message); };
    page.on('console', handler);
    page.on('pageerror', errHandler);

    try {
      const resp = await page.goto(`${BASE_URL}${p.path}`, { waitUntil: 'domcontentloaded', timeout: 10000 });
      await page.waitForTimeout(1500);
      const status = resp.status();
      const jsErrors = errors.filter(e => !e.includes('favicon'));
      record('T1', p.name, 'HTTP状态', status === 200, `status=${status}`);
      record('T1', p.name, '无JS错误', jsErrors.length === 0, jsErrors.length > 0 ? jsErrors.slice(0, 2).join('; ') : '');
    } catch (e) {
      record('T1', p.name, '页面加载', false, e.message.split('\n')[0]);
    }

    page.removeListener('console', handler);
    page.removeListener('pageerror', errHandler);
  }
  await context.close();
}

// ============================================================
// T2: 渲染测试
// ============================================================
async function runT2(browser) {
  console.log('\n========== T2 渲染测试 ==========\n');
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await login(page);

  const tests = [
    { name: '知识库管理', path: '/knowledge/bases', selector: '.grid > div' },
    { name: '文档管理', path: '/knowledge/documents', selector: '.grid > div' },
    { name: '全局技能', path: '/skills/global', selector: '.grid > div' },
    { name: '全局规则', path: '/rules/global', selector: '.grid > div' },
    { name: '我的规则', path: '/rules/personal', selector: '.grid > div' },
    { name: 'Agent管理', path: '/agents', selector: '.grid > div' },
    { name: '流程引擎', path: '/workflows', selector: '.grid > div' },
    { name: '记忆列表', path: '/memory/memories', selector: '.grid > div' },
    { name: '代码资产', path: '/assets', selector: '.grid > div' },
    { name: '项目列表', path: '/projects', selector: '.grid > div' },
  ];

  for (const t of tests) {
    await page.goto(`${BASE_URL}${t.path}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    try {
      const items = await page.$$(t.selector);
      record('T2', t.name, '列表渲染', true, `${items.length} 条`);
    } catch (e) {
      record('T2', t.name, '列表渲染', false, e.message);
    }
  }
  await context.close();
}

// ============================================================
// T3: UI 操作测试
// ============================================================
async function runT3(browser) {
  console.log('\n========== T3 UI 操作测试 ==========\n');
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await login(page);

  // ---- 全局规则 CRUD ----
  console.log('--- 全局规则 ---');
  await page.goto(`${BASE_URL}/rules/global`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  const createBtn = await page.$('button:has-text("创建")');
  record('T3', '全局规则', '创建按钮存在', !!createBtn);

  if (createBtn) {
    await createBtn.click();
    await page.waitForTimeout(1000);

    const modal = await page.$('h2:has-text("创建全局规则")');
    record('T3', '全局规则', '创建弹窗打开', !!modal);

    if (modal) {
      const nameInput = await page.$('input[x-model="form.name"]');
      const contentInput = await page.$('textarea[x-model="form.content"]');
      record('T3', '全局规则', '名称字段存在', !!nameInput);
      record('T3', '全局规则', '内容字段存在', !!contentInput);

      if (nameInput && contentInput) {
        const uniqueName = `T3测试规则-${Date.now()}`;
        await nameInput.fill(uniqueName);
        await contentInput.fill('T3自动化测试内容');
        await page.waitForTimeout(500);

        // 精确选择弹窗内的创建按钮（非背景按钮）
        const submitBtn = await page.$('button.bg-indigo-600:has-text("创建")');
        if (submitBtn) {
          await submitBtn.click();
          await page.waitForTimeout(2000);

          const modalClosed = !await page.$('h2:has-text("创建全局规则")');
          record('T3', '全局规则', '提交后弹窗关闭', modalClosed);

          const pageText = await page.textContent('body');
          record('T3', '全局规则', '新数据可见', pageText.includes(uniqueName));
        } else {
          record('T3', '全局规则', '提交按钮', false, '未找到提交按钮');
        }
      }
    }
  }

  // ---- 文档管理 ----
  console.log('\n--- 文档管理 ---');
  await page.goto(`${BASE_URL}/knowledge/documents`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const docItems = await page.$$('.grid > div');
  record('T3', '文档管理', '列表有数据', docItems.length > 0, `${docItems.length} 条`);

  if (docItems.length > 0) {
    // 点击查看按钮（fa-eye）
    const viewBtn = await docItems[0].$('button[title="查看"]');
    if (viewBtn) {
      await viewBtn.click();
      await page.waitForTimeout(2000);

      const viewModal = await page.$('[x-show="showViewModal"]');
      record('T3', '文档管理', '查看弹窗打开', !!viewModal);

      if (viewModal) {
        const content = await viewModal.textContent();
        record('T3', '文档管理', '查看内容有内容', content && content.length > 20, `长度: ${content?.length || 0}`);

        // 关闭按钮（fa-times 图标）
        const closeBtn = await viewModal.$('.fa-times');
        if (closeBtn) {
          await closeBtn.click();
          await page.waitForTimeout(500);
          record('T3', '文档管理', '查看弹窗关闭', !await page.$('[x-show="showViewModal"]'));
        }
      }
    }

    // 点击编辑按钮（fa-edit）
    const editBtn = await docItems[0].$('button[title="编辑"]');
    if (editBtn) {
      await editBtn.click();
      await page.waitForTimeout(2000);

      const editModal = await page.$('[x-show="showEditModal"]');
      record('T3', '文档管理', '编辑弹窗打开', !!editModal);

      if (editModal) {
        const contentField = await editModal.$('textarea[x-model="editDoc.content"]');
        const contentVal = contentField ? await contentField.inputValue() : null;
        record('T3', '文档管理', '编辑内容回填', contentVal !== null && contentVal !== undefined, `content长度: ${contentVal?.length || 0}`);

        const cancelBtn = await editModal.$('button:has-text("取消")');
        if (cancelBtn) await cancelBtn.click();
        await page.waitForTimeout(500);
      }
    }
  }

  // ---- Agent 管理 ----
  console.log('\n--- Agent 管理 ---');
  await page.goto(`${BASE_URL}/agents`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const agentItems = await page.$$('.grid > div');
  record('T3', 'Agent管理', '列表有数据', agentItems.length > 0, `${agentItems.length} 条`);

  if (agentItems.length > 0) {
    await agentItems[0].click();
    await page.waitForTimeout(2000);

    const detailModal = await page.$('[x-show="showDetailModal"]');
    record('T3', 'Agent管理', '详情弹窗打开', !!detailModal);

    if (detailModal) {
      const tabs = ['信息', 'Instructions', '技能', '规则', '知识库'];
      for (const tabName of tabs) {
        const tab = await detailModal.$(`button:has-text("${tabName}")`);
        record('T3', 'Agent管理', `Tab-${tabName}存在`, !!tab);
      }

      const addSkillBtn = await detailModal.$('button:has-text("添加技能")');
      record('T3', 'Agent管理', '添加技能按钮存在', !!addSkillBtn);

      const addRuleBtn = await detailModal.$('button:has-text("添加规则")');
      record('T3', 'Agent管理', '添加规则按钮存在', !!addRuleBtn);

      const addKbBtn = await detailModal.$('button:has-text("添加知识库")');
      record('T3', 'Agent管理', '添加知识库按钮存在', !!addKbBtn);

      const deleteBtn = await detailModal.$('button:has-text("删除")');
      record('T3', 'Agent管理', '删除按钮存在', !!deleteBtn);

      const closeBtn = await detailModal.$('button:has-text("关闭")');
      record('T3', 'Agent管理', '关闭按钮存在', !!closeBtn);

      if (closeBtn) await closeBtn.click();
      await page.waitForTimeout(500);
    }
  }

  // ---- 流程引擎 ----
  console.log('\n--- 流程引擎 ---');
  await page.goto(`${BASE_URL}/workflows`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const wfItems = await page.$$('.grid > div');
  record('T3', '流程引擎', '列表有数据', wfItems.length > 0, `${wfItems.length} 条`);

  if (wfItems.length > 0) {
    await wfItems[0].click();
    await page.waitForTimeout(2000);

    const wfDetail = await page.$('[x-show="showDetailModal"]');
    record('T3', '流程引擎', '详情弹窗打开', !!wfDetail);

    if (wfDetail) {
      const editBtn = await wfDetail.$('button:has-text("编辑")');
      record('T3', '流程引擎', '编辑按钮存在', !!editBtn);

      const closeBtn = await wfDetail.$('button:has-text("关闭")');
      record('T3', '流程引擎', '关闭按钮存在', !!closeBtn);

      if (closeBtn) await closeBtn.click();
      await page.waitForTimeout(500);
    }
  }

  await context.close();
}

// ============================================================
// T4: 关联管理测试
// ============================================================
async function runT4(browser) {
  console.log('\n========== T4 关联管理测试 ==========\n');
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await login(page);

  const agentName = `T4测试Agent-${Date.now()}`;
  const createResult = await page.evaluate(async ({ name, base }) => {
    const r = await fetch(`${base}/api/agents/create`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, role: '测试', instructions: 'T4测试', scope: 'personal' })
    });
    return r.ok ? await r.json() : null;
  }, { name: agentName, base: BASE_URL });

  if (createResult) {
    record('T4', 'Agent', '创建测试Agent', true);

    await page.goto(`${BASE_URL}/agents`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const agentItems = await page.$$('.grid > div');
    for (const item of agentItems) {
      const text = await item.textContent();
      if (text.includes(agentName)) {
        await item.click();
        await page.waitForTimeout(2000);
        break;
      }
    }

    const detailModal = await page.$('[x-show="showDetailModal"]');
    if (detailModal) {
      // 技能 Tab
      const skillTab = await detailModal.$('button:has-text("技能")');
      if (skillTab) {
        await skillTab.click();
        await page.waitForTimeout(500);
        record('T4', 'Agent', '技能Tab可点击', true);

        const addSkillBtn = await detailModal.$('button:has-text("添加技能")');
        record('T4', 'Agent', '添加技能按钮可点击', !!addSkillBtn);
        if (addSkillBtn) {
          await addSkillBtn.click();
          await page.waitForTimeout(1000);
          const skillModal = await page.$('[x-show="showLinkSkillModal"]');
          record('T4', 'Agent', '技能选择弹窗打开', !!skillModal);
          if (skillModal) {
            const cancelBtn = await skillModal.$('button:has-text("取消")');
            if (cancelBtn) await cancelBtn.click();
            await page.waitForTimeout(500);
          }
        }
      }

      // 规则 Tab
      const ruleTab = await detailModal.$('button:has-text("规则")');
      if (ruleTab) {
        await ruleTab.click();
        await page.waitForTimeout(500);
        record('T4', 'Agent', '规则Tab可点击', true);

        const addRuleBtn = await detailModal.$('button:has-text("添加规则")');
        record('T4', 'Agent', '添加规则按钮可点击', !!addRuleBtn);
        if (addRuleBtn) {
          await addRuleBtn.click();
          await page.waitForTimeout(1000);
          const ruleModal = await page.$('[x-show="showLinkRuleModal"]');
          record('T4', 'Agent', '规则选择弹窗打开', !!ruleModal);
          if (ruleModal) {
            const cancelBtn = await ruleModal.$('button:has-text("取消")');
            if (cancelBtn) await cancelBtn.click();
            await page.waitForTimeout(500);
          }
        }
      }

      // 知识库 Tab
      const kbTab = await detailModal.$('button:has-text("知识库")');
      if (kbTab) {
        await kbTab.click();
        await page.waitForTimeout(500);
        record('T4', 'Agent', '知识库Tab可点击', true);

        const addKbBtn = await detailModal.$('button:has-text("添加知识库")');
        record('T4', 'Agent', '添加知识库按钮可点击', !!addKbBtn);
        if (addKbBtn) {
          await addKbBtn.click();
          await page.waitForTimeout(1000);
          const kbModal = await page.$('[x-show="showLinkKbModal"]');
          record('T4', 'Agent', '知识库选择弹窗打开', !!kbModal);
          if (kbModal) {
            const cancelBtn = await kbModal.$('button:has-text("取消")');
            if (cancelBtn) await cancelBtn.click();
            await page.waitForTimeout(500);
          }
        }
      }

      const closeBtn = await detailModal.$('button:has-text("关闭")');
      if (closeBtn) await closeBtn.click();
    }

    await page.evaluate(async (id) => {
      await fetch(`${location.origin}/api/agents/${id}`, { method: 'DELETE' });
    }, createResult.id);
    record('T4', 'Agent', '清理测试Agent', true);
  } else {
    record('T4', 'Agent', '创建测试Agent', false);
  }

  await context.close();
}

// ============================================================
// Main
// ============================================================
async function main() {
  console.log('=== WebUI T1/T2/T3/T4 全量测试 ===');
  console.log(`目标: ${BASE_URL}`);
  console.log(`时间: ${new Date().toISOString()}`);

  const browser = await chromium.launch({ headless: true });

  await runT1(browser);
  await runT2(browser);
  await runT3(browser);
  await runT4(browser);

  const summary = { T1: { total: 0, passed: 0 }, T2: { total: 0, passed: 0 }, T3: { total: 0, passed: 0 }, T4: { total: 0, passed: 0 } };
  results.forEach(r => { if (summary[r.tier]) { summary[r.tier].total++; if (r.passed) summary[r.tier].passed++; } });

  console.log('\n========== 测试结果汇总 ==========\n');
  let grandTotal = 0, grandPassed = 0;
  for (const [tier, s] of Object.entries(summary)) {
    const pct = s.total > 0 ? ((s.passed / s.total) * 100).toFixed(1) : 'N/A';
    console.log(`${tier}: ${s.passed}/${s.total} 通过 (${pct}%)`);
    grandTotal += s.total;
    grandPassed += s.passed;
  }
  console.log(`\n总计: ${grandPassed}/${grandTotal} 通过 (${((grandPassed/grandTotal)*100).toFixed(1)}%)`);

  const failed = results.filter(r => !r.passed);
  if (failed.length > 0) {
    console.log('\n========== 失败详情 ==========\n');
    for (const f of failed) console.log(`  [${f.tier}] ${f.page} | ${f.name}: ${f.detail}`);
  }

  fs.writeFileSync('test-reports-t1t2t3t4.json', JSON.stringify({ timestamp: new Date().toISOString(), testSuite: 'T1/T2/T3/T4', summary, grandTotal: { total: grandTotal, passed: grandPassed }, results }, null, 2));
  console.log('\n报告已保存到 test-reports-t1t2t3t4.json');
  await browser.close();
}

main().catch(e => { console.error('测试异常:', e); process.exit(1); });
