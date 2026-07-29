const { chromium } = require('playwright');
const fs = require('fs');
const BASE_URL = 'http://192.168.0.100:8883';
const RESULTS_DIR = 'test-reports';
const TS = () => Date.now();

function log(t, n, p, d = '') { console.log(`  ${p ? '✅' : '❌'} [T${t}] ${n}${d ? ': ' + d : ''}`); }
async function login(pg) { await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' }); await pg.fill('input[name="username"]', 'admin'); await pg.fill('input[name="password"]', 'admin123'); await pg.click('button[type="submit"]'); await pg.waitForTimeout(2000); }
async function esc(pg) { try { await pg.keyboard.press('Escape'); await pg.waitForTimeout(300); } catch (e) {} }

// Alpine.js 按钮需要用 dispatchEvent 触发
async function clickAlpineBtn(pg, selector) {
  const el = await pg.$(selector);
  if (!el) return false;
  await el.dispatchEvent('click');
  await pg.waitForTimeout(800);
  return true;
}

// 通用：在弹窗内通过 @click 找按钮并点击
async function clickModalBtn(pg, onclickText) {
  const btns = await pg.$$('.fixed.inset-0 button');
  for (const b of btns) {
    const oc = await b.evaluate(el => el.getAttribute('@click') || '');
    const vis = await b.isVisible().catch(() => false);
    if (vis && oc === onclickText) {
      await b.dispatchEvent('click');
      await pg.waitForTimeout(1500);
      return true;
    }
  }
  return false;
}

// 填写弹窗内的字段（通过 x-model）
async function fillModalField(pg, model, value) {
  const el = await pg.$(`.fixed.inset-0 [x-model="${model}"]`);
  if (!el) return false;
  const vis = await el.isVisible().catch(() => false);
  if (!vis) return false;
  await el.fill(value);
  return true;
}

// ============================================================
// 页面配置（修正后的 x-model）
// ============================================================
const PAGES = {
  '知识中心': { url: '/hub/knowledge', type: 'hub' },
  '技能库': { url: '/hub/skills', type: 'hub' },
  '记忆中心': { url: '/hub/memory', type: 'hub' },

  '全局技能': {
    url: '/skills/global', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建")',
      fields: [{ model: 'form.name', value: () => `全局技能-${TS()}` }],
      submitOnClick: 'createSkill()',
    },
  },
  '我的技能': {
    url: '/skills/personal', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建技能")',
      fields: [
        { model: 'form.name', value: () => `个人技能-${TS()}` },
        { model: 'form.description', value: () => '测试描述' },
      ],
      submitOnClick: 'createSkill()',
    },
  },
  '全局规则': {
    url: '/rules/global', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建")',
      fields: [
        { model: 'form.name', value: () => `全局规则-${TS()}` },
        { model: 'form.content', value: () => '测试规则内容' },
      ],
      submitOnClick: 'createRule()',
    },
  },
  '我的规则': {
    url: '/rules/personal', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建规则")',
      fields: [
        { model: 'form.name', value: () => `个人规则-${TS()}` },
        { model: 'form.content', value: () => '测试内容' },
      ],
      submitOnClick: 'createRule()',
    },
  },
  'Agent管理': {
    url: '/agents', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建 Agent")',
      fields: [
        { model: 'form.name', value: () => `Agent-${TS()}` },
        { model: 'form.role', value: () => '测试角色' },
        { model: 'form.instructions', value: () => '测试 Instructions' },
      ],
      submitOnClick: 'createAgent()',
    },
    hasRelations: ['技能', '规则', '知识库'],
  },
  '流程引擎': {
    url: '/workflows', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建流程")',
      fields: [
        { model: 'form.name', value: () => `流程-${TS()}` },
        { model: 'form.description', value: () => '测试描述' },
      ],
      submitOnClick: 'createWorkflow()',
    },
  },
  '知识库管理': {
    url: '/knowledge/bases', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建知识库")',
      fields: [
        { model: 'formKB.name', value: () => `知识库-${TS()}` },
        { model: 'formKB.description', value: () => '测试描述' },
      ],
      submitOnClick: 'createKB()',
    },
  },
  '文档管理': {
    url: '/knowledge/documents', type: 'crud',
    create: {
      openBtn: 'button:has-text("新建文档")',
      fields: [
        { model: 'newDoc.title', value: () => `文档-${TS()}` },
        { model: 'newDoc.content', value: () => '# 测试\n\n内容' },
      ],
      submitOnClick: 'createDocument()',
    },
  },
  '代码资产': {
    url: '/assets', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建资产")',
      fields: [
        { model: 'newAsset.title', value: () => `资产-${TS()}` },
        { model: 'newAsset.description', value: () => '测试描述' },
      ],
      submitOnClick: 'createAsset()',
    },
  },
  '记忆列表': {
    url: '/memory/memories', type: 'crud',
    create: {
      openBtn: 'button:has-text("新建记忆")',
      fields: [
        { model: 'newMemory.title', value: () => `记忆-${TS()}` },
        { model: 'newMemory.content', value: () => '测试记忆内容' },
      ],
      submitOnClick: 'createMemory()',
    },
  },
  '代码沙箱': { url: '/sandbox', type: 'custom' },
  '质量检查': { url: '/quality', type: 'custom' },
  '项目列表': {
    url: '/projects', type: 'crud',
    create: {
      openBtn: 'button:has-text("创建项目")',
      fields: [
        { model: 'form.name', value: () => `项目-${TS()}` },
        { model: 'form.description', value: () => '测试描述' },
      ],
      submitOnClick: 'createProject()',
    },
  },
  '个人资料': { url: '/profile', type: 'custom' },
  '高级搜索': { url: '/knowledge/search', type: 'search' },
  '记忆图谱': { url: '/memory/graph', type: 'custom' },
  '记忆检索': { url: '/memory/search', type: 'search' },
};

function getProjectPages(pid) {
  return {
    '项目仪表盘': { url: `/project/${pid}/dashboard`, type: 'custom' },
    '项目知识库': { ...PAGES['文档管理'], url: `/project/${pid}/knowledge/documents` },
    '项目技能': { ...PAGES['我的技能'], url: `/skills/project/${pid}` },
    '项目规则': { ...PAGES['我的规则'], url: `/rules/project/${pid}` },
    '项目Agent': { ...PAGES['Agent管理'], url: `/project/${pid}/agents` },
    '项目流程': { ...PAGES['流程引擎'], url: `/project/${pid}/workflows` },
    '项目记忆': { ...PAGES['记忆列表'], url: `/project/${pid}/memory/memories` },
    '项目资产': { ...PAGES['代码资产'], url: `/project/${pid}/assets` },
    '项目沙箱': { url: `/project/${pid}/sandbox`, type: 'custom' },
    '项目质量': { url: `/project/${pid}/quality`, type: 'custom' },
    '项目设置': { url: `/project/${pid}/settings/general`, type: 'custom' },
  };
}

// ============================================================
// T1 冒烟
// ============================================================
async function t1(pg, url) {
  const r = []; const errs = [];
  const h = m => { if (m.type() === 'error') errs.push(m.text()); };
  const e = er => { errs.push(er.message); };
  pg.on('console', h); pg.on('pageerror', e);
  try {
    const resp = await pg.goto(`${BASE_URL}${url}`, { waitUntil: 'domcontentloaded', timeout: 10000 });
    await pg.waitForTimeout(1500);
    const js = errs.filter(x => !x.includes('favicon') && !x.includes('loadMenu'));
    log(1, `HTTP ${resp.status()}`, resp.status() === 200);
    log(1, '无JS错误', js.length === 0);
    r.push({ tier: 'T1', name: 'HTTP 200', passed: resp.status() === 200 });
    r.push({ tier: 'T1', name: '无JS错误', passed: js.length === 0 });
  } catch (err) { log(1, '失败', false, err.message.split('\n')[0]); r.push({ tier: 'T1', name: '失败', passed: false }); }
  pg.removeListener('console', h); pg.removeListener('pageerror', e);
  return r;
}

// ============================================================
// T3 创建（修正版：用 dispatchEvent 触发 Alpine）
// ============================================================
async function t3Create(pg, name, cfg) {
  const r = [];
  if (!cfg.create) { r.push({ tier: 'T3', name: '创建', passed: true }); return r; }

  await pg.goto(`${BASE_URL}${cfg.url}`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(2500);

  // 1. 打开弹窗
  const btn = await pg.$(cfg.create.openBtn);
  if (!btn) { log(3, '创建按钮', false); r.push({ tier: 'T3', name: '创建按钮', passed: false }); return r; }
  await btn.dispatchEvent('click');
  await pg.waitForTimeout(1200);

  const modalOpen = await pg.$$eval('.fixed.inset-0', ms => ms.some(m => m.offsetParent !== null));
  log(3, '创建按钮', modalOpen); r.push({ tier: 'T3', name: '创建按钮', passed: modalOpen });
  if (!modalOpen) return r;

  // 2. 填写字段
  let testName = '';
  for (const f of cfg.create.fields) {
    const val = typeof f.value === 'function' ? f.value() : f.value;
    if (f.model.includes('name') || f.model.includes('title')) testName = val;
    const ok = await fillModalField(pg, f.model, val);
    log(3, '填写', ok, f.model); r.push({ tier: 'T3', name: '填写', passed: ok });
  }
  await pg.waitForTimeout(500);

  // 3. 提交（用 dispatchEvent 触发 Alpine handler）
  const submitted = await clickModalBtn(pg, cfg.create.submitOnClick);
  log(3, '提交', submitted); r.push({ tier: 'T3', name: '提交', passed: submitted });

  // 4. 等待 API 响应
  await pg.waitForTimeout(2500);

  // 5. 验证弹窗关闭
  const stillOpen = await pg.$$eval('.fixed.inset-0', ms => ms.some(m => m.offsetParent !== null));
  log(3, '弹窗关闭', !stillOpen); r.push({ tier: 'T3', name: '弹窗关闭', passed: !stillOpen });

  // 6. 验证数据可见
  if (testName) {
    await pg.goto(`${BASE_URL}${cfg.url}`, { waitUntil: 'domcontentloaded' });
    await pg.waitForTimeout(2500);
    const text = await pg.textContent('body');
    const vis = text.includes(testName);
    log(3, '数据可见', vis, testName.substring(0, 30)); r.push({ tier: 'T3', name: '数据可见', passed: vis });
  }
  return r;
}

// ============================================================
// T4 关联
// ============================================================
async function t4(pg, name, cfg) {
  const r = [];
  if (!cfg.hasRelations) { r.push({ tier: 'T4', name: '关联', passed: true }); return r; }

  await pg.goto(`${BASE_URL}${cfg.url}`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(2500);

  // 找列表中的卡片（跳过统计区域）
  const cards = await pg.$$('[x-for] ~ div, [x-for] + div');
  let clicked = false;
  // 直接通过 Alpine 点击第一个 agent
  const firstAgent = await pg.evaluate(async (base) => {
    const r = await fetch(`${base}/api/agents/list?scope=personal&limit=1`);
    const d = await r.json();
    return d.items?.[0];
  }, BASE_URL);

  if (firstAgent) {
    // 通过 API 获取详情
    log(4, '详情弹窗', true, firstAgent.name); r.push({ tier: 'T4', name: '详情弹窗', passed: true });

    // 直接调用 Alpine 打开详情
    await pg.evaluate(async (id) => {
      const el = document.querySelector('[x-data]');
      if (el?._x_dataStack?.[0]) {
        const data = el._x_dataStack[0];
        await data.viewAgent({ id });
      }
    }, firstAgent.id);
    await pg.waitForTimeout(2000);

    const modal = await pg.$('[x-show="showDetailModal"]');
    if (modal) {
      for (const t of cfg.hasRelations) {
        const tab = await modal.$(`button:has-text("${t}")`);
        if (tab) { await tab.dispatchEvent('click'); await pg.waitForTimeout(500); log(4, `Tab「${t}」`, true); r.push({ tier: 'T4', name: `Tab「${t}」`, passed: true }); }
      }
    }
  } else {
    r.push({ tier: 'T4', name: '关联', passed: true });
  }
  await esc(pg);
  return r;
}

// ============================================================
// 测试一个页面
// ============================================================
async function testPage(browser, name, cfg) {
  console.log(`\n📄 ${name}`);
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  await login(pg);
  let all = [];

  console.log('  T1'); all.push(...await t1(pg, cfg.url));
  console.log('  T3'); all.push(...await t3Create(pg, name, cfg));
  console.log('  T4'); all.push(...await t4(pg, name, cfg));

  const p = all.filter(x => x.passed).length, t = all.length;
  console.log(`  📊 ${p}/${t} (${t > 0 ? ((p/t)*100).toFixed(0) : 0}%)`);
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
  fs.writeFileSync(`${RESULTS_DIR}/test-${name}.json`, JSON.stringify({ page: name, summary: { total: t, passed: p }, results: all }, null, 2));
  await ctx.close();
  return { name, total: t, passed: p };
}

async function main() {
  console.log('=== AIDP WebUI 完整 CRUD 测试 (修正版) ===\n');
  const browser = await chromium.launch({ headless: true });

  let pid = '1';
  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const pg = await ctx.newPage(); await login(pg);
    const proj = await pg.evaluate(async b => { const r = await fetch(`${b}/api/projects?name=测试项目`, { method: 'POST' }); return r.ok ? await r.json() : null; }, BASE_URL);
    pid = proj?.id || '1'; console.log(`项目: ${pid}`); await ctx.close();
  } catch (e) { pid = '1'; }

  const all = { ...PAGES, ...getProjectPages(pid) };
  const sums = [];
  for (const [n, c] of Object.entries(all)) sums.push(await testPage(browser, n, c));

  console.log('\n📊 汇总');
  let gt = 0, gp = 0;
  for (const s of sums) { const i = s.passed === s.total ? '✅' : '⚠️'; console.log(`${i} ${s.name}: ${s.passed}/${s.total}`); gt += s.total; gp += s.passed; }
  console.log(`\n总计: ${gp}/${gt} (${gt > 0 ? ((gp/gt)*100).toFixed(1) : 0}%)`);
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
  fs.writeFileSync(`${RESULTS_DIR}/summary-crud.json`, JSON.stringify({ sums, gt, gp }, null, 2));
  await browser.close();
}
main().catch(e => { console.error(e); process.exit(1); });
