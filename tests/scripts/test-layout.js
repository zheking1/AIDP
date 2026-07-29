const { chromium } = require('playwright');
const BASE = 'http://192.168.0.100:8883';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  const click = async (text) => {
    const btns = await page.$$('button');
    for (const b of btns) {
      if ((await b.textContent().catch(()=>'')).includes(text)) { await b.click(); break; }
    }
    await page.waitForTimeout(1500);
  };

  const pages = ['知识中心', '技能库', '记忆中心', '代码沙箱', '质量检查', '用户管理', '系统设置', '审计日志'];
  for (const name of pages) await click(name);

  const all = await page.evaluate(() => {
    const tabs = document.querySelectorAll('[id^="tab-content-"]');
    const results = [];
    tabs.forEach((el) => {
      const wrapper = el.firstElementChild;
      if (!wrapper) return;
      const id = el.id;
      const tStyle = getComputedStyle(el);
      const item = {
        id, visible: tStyle.display !== 'none',
        tabW: el.offsetWidth, tabL: el.offsetLeft, tabPL: tStyle.paddingLeft, tabML: tStyle.marginLeft
      };
      const divs = Array.from(wrapper.children).filter(c => c.tagName === 'DIV');
      if (divs.length > 0) {
        const h = divs[0];
        const hs = getComputedStyle(h);
        item.header = {
          pt: hs.paddingTop, pb: hs.paddingBottom,
          bb: hs.borderBottomStyle !== 'none' ? hs.borderBottomWidth + ' ' + hs.borderBottomStyle + ' ' + hs.borderBottomColor : 'none',
          flex: hs.display === 'flex' ? 'flex' : 'block',
          justify: hs.justifyContent,
          cls: h.className
        };
      }
      if (divs.length > 1) {
        const b = divs[1];
        const bs = getComputedStyle(b);
        item.body = { pt: bs.paddingTop, firstTag: b.firstElementChild?.tagName };
      }
      results.push(item);
    });
    return results;
  });

  console.log(`Tabs: ${all.length}\n`);
  all.forEach(t => {
    console.log(`--- ${t.id} ---`);
    console.log(`  visible=${t.visible} w=${t.tabW} left=${t.tabL} padL=${t.tabPL} ml=${t.tabML}`);
    if (t.header) console.log(`  header: pt=${t.header.pt} pb=${t.header.pb} border=${t.header.bb} layout=${t.header.flex} ${t.header.justify}`);
    if (t.body) console.log(`  body: pt=${t.body.pt} first=${t.body.firstTag}`);
  });

  await browser.close();
})();