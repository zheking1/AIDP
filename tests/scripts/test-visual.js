const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // Ensure test project exists
  await page.evaluate(async () => {
    const list = await fetch('/api/projects');
    const data = await list.json();
    const exists = (data.items || []).find(p => p.name === 'LayoutTest');
    if (!exists) {
      await fetch('/api/projects', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:'LayoutTest',description:'t',tech_stack:[]}) });
    }
  });
  await page.waitForTimeout(1000);

  // Get the project ID
  const projectId = await page.evaluate(async () => {
    const r = await fetch('/api/projects');
    const d = await r.json();
    const p = (d.items || []).find(p => p.name === 'LayoutTest');
    return p ? p.id : null;
  });
  if (!projectId) { console.log('No test project'); process.exit(1); }

  // Knowledge center as BASELINE
  console.log('\n=== 知识中心 (BASELINE) ===');
  await page.goto(BASE + '/knowledge/bases?partial=1', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const baseline = await page.evaluate(() => {
    const body = document.body;
    const firstDiv = body.firstElementChild;
    const header = firstDiv?.querySelector(':scope > div:first-of-type');
    if (!header) return { error: 'no header' };
    const hs = getComputedStyle(header);
    const bodyStyle = firstDiv?.querySelector(':scope > div:nth-of-type(2)');
    const bs = bodyStyle ? getComputedStyle(bodyStyle) : null;
    return {
      header: { display: hs.display, justify: hs.justifyContent, pt: hs.paddingTop, pb: hs.paddingBottom, bb: hs.borderBottomWidth, bc: hs.borderBottomColor },
      body: bs ? { pt: bs.paddingTop } : null,
      bodyBg: getComputedStyle(body).backgroundColor
    };
  });
  console.log('BASELINE:', JSON.stringify(baseline, null, 2));

  // Test ALL project pages
  const pages = [
    { name: '项目仪表盘', url: '/project/' + projectId + '/dashboard?partial=1' },
    { name: '设置-基本信息', url: '/project/' + projectId + '/settings/general?partial=1' },
    { name: '设置-AI配置', url: '/project/' + projectId + '/settings/instructions?partial=1' },
  ];

  for (const p of pages) {
    console.log('\n=== ' + p.name + ' ===');
    await page.goto(BASE + p.url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const info = await page.evaluate((bl) => {
      const body = document.body;
      const firstDiv = body.firstElementChild;
      if (!firstDiv) return { error: 'no firstElementChild' };

      // The Alpine wrapper
      const alpineWrapper = firstDiv.tagName === 'DIV' ? firstDiv : firstDiv.querySelector(':scope > div');
      if (!alpineWrapper) return { error: 'no alpine wrapper', firstTag: firstDiv.tagName };

      const header = alpineWrapper.querySelector(':scope > div:first-of-type');
      if (!header) return { error: 'no header', alpineClasses: alpineWrapper.className };

      const hs = getComputedStyle(header);
      const bodySection = alpineWrapper.querySelector(':scope > div:nth-of-type(2)');
      const bs = bodySection ? getComputedStyle(bodySection) : null;

      const issues = [];
      if (hs.display !== 'flex') issues.push('display=' + hs.display + '(需flex)');
      if (hs.justifyContent !== 'space-between') issues.push('justify=' + hs.justifyContent);
      if (hs.paddingTop !== '20px') issues.push('pt=' + hs.paddingTop);
      if (hs.paddingBottom !== '16px') issues.push('pb=' + hs.paddingBottom);
      if (hs.borderBottomWidth === '0px') issues.push('无border-bottom');
      if (getComputedStyle(body).backgroundColor !== bl.bodyBg) issues.push('背景色不同');

      return {
        header: { display: hs.display, justify: hs.justifyContent, pt: hs.paddingTop, pb: hs.paddingBottom, bb: hs.borderBottomWidth },
        body: bs ? { pt: bs.paddingTop } : null,
        bodyBg: getComputedStyle(body).backgroundColor,
        issues: issues.length ? issues : '无'
      };
    }, baseline);

    console.log(JSON.stringify(info, null, 2));
    if (info.issues !== '无' && info.issues.length > 0) {
      console.log('  ⚠ 不一致:', info.issues.join(', '));
    }
  }

  await browser.close();
})();