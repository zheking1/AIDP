const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  let errors = [];
  page.on('pageerror', e => errors.push(e.message.substring(0,80)));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text().substring(0,80)); });
  page.on('response', r => { if (r.status() >= 400) errors.push(r.status()+' '+r.url().substring(0,60)); });

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  const pid = await page.evaluate(async () => {
    const r = await fetch('/api/projects'); const d = await r.json();
    let p = (d.items||[]).find(x=>x.name==='E2E-Test-Project');
    if(!p){ const r2=await fetch('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'E2E-Test-Project',description:'e2e'})}); if(r2.ok)p=await r2.json(); }
    return p?p.id:null;
  });

  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await page.evaluate((id) => { const s=document.querySelector('select'); if(s){s.value=String(id);s.dispatchEvent(new Event('change',{bubbles:true}));} }, pid);
  await page.waitForTimeout(2000);

  const pages = ['项目仪表盘','项目知识','项目技能','项目规则','项目 Agent','项目流程','项目记忆','项目设置'];
  for (const name of pages) {
    errors = [];
    await page.evaluate(() => { document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('项目仪表盘')&&b.offsetParent) b.click(); }); });
    await page.evaluate((n) => { document.querySelectorAll('button').forEach(b => { if(b.textContent.includes(n)&&b.offsetParent) b.click(); }); }, name);
    await page.waitForTimeout(3000);

    const layout = await page.evaluate(() => {
      const tab = Array.from(document.querySelectorAll('[id^=tab-content-]')).find(el => getComputedStyle(el).display !== 'none');
      if(!tab) return {error:'no tab'};
      const w = tab.firstElementChild; if(!w) return {error:'no wrapper'};
      const h = w.querySelector(':scope > div:first-of-type'); if(!h) return {error:'no header'};
      const s = getComputedStyle(h);
      return `${s.display} ${s.justifyContent} pt=${s.paddingTop} pb=${s.paddingBottom}`;
    });
    console.log(`${name}: ${layout} | ${errors.length > 0 ? '⚠ '+errors.slice(0,2).join('; ') : '✅'}`);
  }

  await browser.close();
})();