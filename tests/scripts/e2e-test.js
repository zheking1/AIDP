const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const BASE = 'http://192.168.0.100:8883';
const R = path.join(__dirname, '..', 'reports');
const S = path.join(__dirname, '..', 'screenshots');

class T {
  constructor() { this.b = null; this.p = null; this.r = []; this.err = []; }

  ok(n, s, d = '') { console.log(`  ${s==='PASS'?'✅':'❌'} ${n}: ${d}`); this.r.push({ n, s, d }); }

  async ss(name) { fs.mkdirSync(S, { recursive: true }); await this.p.screenshot({ path: path.join(S, `${name}.png`), fullPage: true }); }

  async rpt() {
    const p = this.r.filter(r => r.s === 'PASS').length;
    const f = this.r.filter(r => r.s === 'FAIL').length;
    console.log(`\n${'='.repeat(50)}\n  报告: ${this.r.length}项 | ✅${p} ❌${f} | ${(p/this.r.length*100).toFixed(1)}%\n${'='.repeat(50)}`);
    if (f) { console.log(`失败:`); this.r.filter(r => r.s === 'FAIL').forEach(r => console.log(`  ❌ ${r.n}: ${r.d}`)); }
    fs.mkdirSync(R, { recursive: true }); fs.writeFileSync(path.join(R, 'e2e-report.json'), JSON.stringify(this.r, null, 2));
  }

  async login() {
    console.log('[登录]');
    this.b = await chromium.launch({ headless: false, slowMo: 400 });
    this.p = await this.b.newPage({ viewport: { width: 1440, height: 900 } });
    this.p.on('console', msg => { if (msg.type() === 'error') this.err.push(msg.text()); });
    this.p.on('pageerror', e => this.err.push(e.message));
    await this.p.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
    await this.p.fill('#username', 'admin').catch(() => {});
    await this.p.fill('#password', 'admin123').catch(() => {});
    await this.p.click('button[type="submit"]').catch(() => {});
    await this.p.waitForTimeout(2000);
  }

  // ============== Page Smoke Tests ==============
  async smoke(url, name) {
    await this.p.goto(`${BASE}${url}`, { waitUntil: 'networkidle', timeout: 20000 }).catch(() => {});
    await this.p.waitForTimeout(2000);
    const body = await this.p.textContent('body').catch(() => '');
    const ok = body.length > 200 && !body.includes('Internal Server Error');
    this.ok(`${name} 页面`, ok ? 'PASS' : 'FAIL', `${body.length}b`);
    if (this.err.length) {
      this.ok(`${name} 控制台`, 'FAIL', this.err.slice(0, 2).join('; '));
      this.err = [];
    }
  }

  async close() { if (this.b) await this.b.close(); }
}

// ============== Direct API Tests (run on NAS) ==============
const API_TESTS = [
  { path: '/api/knowledge/bases', name: '知识库', create: { name: 'E2E-KB-{ts}', description: 'E2E test' } },
  { path: '/api/skills/create', name: '个人技能', create: { name: 'E2E-SK-{ts}', scope: 'personal', instruction: 'E2E test' } },
  { path: '/api/rules/create', name: '个人规则', create: { name: 'E2E-RL-{ts}', scope: 'personal', content: 'E2E test rule', category: 'security' } },
  { path: '/api/agents/create', name: 'Agent', create: { name: 'E2E-AG-{ts}', scope: 'personal', role: 'tester', instructions: 'E2E test' } },
  { path: '/api/workflows/create', name: '流程', create: { name: 'E2E-WF-{ts}', category: 'development' } },
  { path: '/api/memory/memories', name: '记忆', create: { title: 'E2E-MEM-{ts}', content: 'E2E test memory', category: 'other' } },
  { path: '/api/assets/create', name: '代码资产', create: { title: 'E2E-AST-{ts}', content: 'print(1)', asset_type: 'snippet' } },
];

const PAGE_SMOKE_TESTS = [
  ['/hub/knowledge', '知识中心Hub'],
  ['/hub/skills', '技能库Hub'],
  ['/hub/memory', '记忆中心Hub'],
  ['/knowledge/bases', '知识库管理'],
  ['/knowledge/documents', '文档管理'],
  ['/knowledge/search', '知识搜索'],
  ['/knowledge/templates', '文档模板'],
  ['/skills/global', '全局技能'],
  ['/skills/personal', '个人技能'],
  ['/rules/global', '全局规则'],
  ['/rules/personal', '个人规则'],
  ['/agents', 'Agent管理'],
  ['/workflows', '流程引擎'],
  ['/memory/memories', '记忆列表'],
  ['/memory/graph', '记忆图谱'],
  ['/memory/search', '记忆检索'],
  ['/assets', '代码资产'],
  ['/sandbox', '代码沙箱'],
  ['/quality', '质量检查'],
  ['/admin/projects', 'Admin项目管理'],
  ['/admin/skills', 'Admin技能管理'],
  ['/admin/rules', 'Admin规则管理'],
];

(async () => {
  const t = new T();
  const ts = String(Date.now());

  // Phase 1: Browser smoke tests
  try {
    await t.login();

    console.log(`\n【页面冒烟测试 (${PAGE_SMOKE_TESTS.length}页)】`);
    for (const [url, name] of PAGE_SMOKE_TESTS) {
      await t.smoke(url, name);
    }
  } catch (e) { console.error('BROWSER ERROR:', e.message); }
  finally { await t.close(); }

  // Phase 2: API CRUD tests via SSH
  console.log(`\n【API CRUD 测试 (${API_TESTS.length}项)】`);

  const { execSync } = require('child_process');

  function ssh(cmd) {
    try {
      const r = execSync(`ssh -i ~/.ssh/nas_temp root@192.168.0.100 "${cmd.replace(/"/g, '\\"')}"`, { timeout: 15000 });
      return r.toString().trim();
    } catch (e) { return ''; }
  }

  // Login via SSH
  ssh(`curl -s -c /tmp/e2e_cookies.txt -X POST 'http://127.0.0.1:8883/api/auth/login/form' -d 'username=admin&password=admin123' -o /dev/null`);

  for (const test of API_TESTS) {
    // List
    const listUrl = test.path === '/api/skills/create' ? '/api/skills/list?scope=personal' :
                    test.path === '/api/rules/create' ? '/api/rules/list?scope=personal' :
                    test.path === '/api/agents/create' ? '/api/agents/list?scope=personal' :
                    test.path === '/api/workflows/create' ? '/api/workflows/list' :
                    test.path;
    const listResp = ssh(`curl -sb /tmp/e2e_cookies.txt 'http://127.0.0.1:8883${listUrl}'`);
    try {
      const listData = JSON.parse(listResp);
      const items = listData.items || [];
      t.ok(`${test.name} 列表`, 'PASS', `${items.length}条`);
    } catch { t.ok(`${test.name} 列表`, 'FAIL', listResp.slice(0, 50)); }

    // Create
    const createBody = JSON.stringify({ ...test.create, name: test.create.name.replace('{ts}', ts) });
    const createResp = ssh(`curl -sb /tmp/e2e_cookies.txt -X POST 'http://127.0.0.1:8883${test.path}' -H 'Content-Type: application/json' -d '${createBody.replace(/'/g, "'\\''")}'`);
    try {
      const createData = JSON.parse(createResp);
      if (createData.id) {
        t.ok(`${test.name} 创建`, 'PASS', `id=${createData.id.slice(0, 8)}...`);
        // Delete
        const deletePath = test.path.replace('/create', '').replace('/memories', '/memories');
        const delResp = ssh(`curl -sb /tmp/e2e_cookies.txt -X DELETE 'http://127.0.0.1:8883${deletePath}/${createData.id}'`);
        try {
          const delData = JSON.parse(delResp);
          t.ok(`${test.name} 删除`, delData.success ? 'PASS' : 'FAIL', '');
        } catch { t.ok(`${test.name} 删除`, 'FAIL', ''); }
      } else {
        t.ok(`${test.name} 创建`, 'FAIL', JSON.stringify(createData).slice(0, 80));
      }
    } catch { t.ok(`${test.name} 创建`, 'FAIL', createResp.slice(0, 60)); }
  }

  await t.rpt();
})();