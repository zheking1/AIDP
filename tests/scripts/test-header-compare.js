const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin'); await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]'); await page.waitForTimeout(3000);

  // Ensure project exists
  const pid = await page.evaluate(async () => {
    const r = await fetch('/api/projects'); const d = await r.json();
    let p = (d.items||[]).find(x=>x.name==='LayoutTest');
    if (!p) {
      const r2 = await fetch('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'LayoutTest',description:'t'})});
      p = r2.ok ? await r2.json() : null;
    }
    return p ? p.id : null;
  });
  await page.goto(BASE+'/',{waitUntil:'networkidle'}); await page.waitForTimeout(2000);
  await page.evaluate((id)=>{const s=document.querySelector('select');if(s){s.value=String(id);s.dispatchEvent(new Event('change',{bubbles:true}));}},pid);
  await page.waitForTimeout(2000);

  const pages = [
    '知识中心',
    '项目规则', '项目 Agent', '项目流程',
    '项目仪表盘', '项目记忆', '项目技能', '项目设置', '项目知识'
  ];

  for (const name of pages) {
    if (name === '知识中心') {
      await page.evaluate(()=>{document.querySelector('nav')?.scrollTo(0,0);document.querySelectorAll('button').forEach(b=>{if(b.textContent.includes('知识中心')&&b.offsetParent)b.click()});});
    } else {
      await page.evaluate((n)=>{document.querySelectorAll('button').forEach(b=>{if(b.textContent.includes(n)&&b.offsetParent)b.click()});}, name);
    }
    await page.waitForTimeout(3000);
    
    const info = await page.evaluate(() => {
      const tab = Array.from(document.querySelectorAll('[id^="tab-content-"]')).find(el=>getComputedStyle(el).display!=='none');
      if(!tab) return {error:'no tab'};
      const w = tab.firstElementChild;
      if(!w) return {error:'no wrapper'};
      const h = w.querySelector(':scope>div:first-of-type');
      if(!h) return {error:'no header'};
      
      // Get ALL children of header with their rendered positions
      const kids = Array.from(h.children).map(c => {
        const r = c.getBoundingClientRect();
        const s = getComputedStyle(c);
        return {
          tag: c.tagName,
          html: (c.innerHTML||'').replace(/\s+/g,' ').substring(0,60),
          left: Math.round(r.left),
          right: Math.round(r.right),
          width: Math.round(r.width),
          textAlign: s.textAlign,
          display: s.display,
          flex: s.flex,
          classes: c.className
        };
      });
      
      const hr = h.getBoundingClientRect();
      const tr = tab.getBoundingClientRect();
      return {
        headerLeft: Math.round(hr.left),
        headerRight: Math.round(hr.right),
        headerWidth: Math.round(hr.width),
        tabLeft: Math.round(tr.left),
        tabWidth: Math.round(tr.width),
        children: kids,
        childCount: kids.length
      };
    });
    
    if (info.error) { console.log(name+': ❌ '+info.error); continue; }
    console.log(name+':');
    console.log('  tab: left='+info.tabLeft+' width='+info.tabWidth+' header: left='+info.headerLeft+' right='+info.headerRight+' width='+info.headerWidth);
    info.children.forEach((k,i)=>console.log('  ['+i+'] '+k.tag+' left='+k.left+' right='+k.right+' w='+k.width+' align='+k.textAlign+' display='+k.display+' flex='+k.flex+' "'+k.html+'"'));
    console.log('');
  }
  await browser.close();
})();