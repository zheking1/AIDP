const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({headless:true});
  const ctx = await b.newContext({viewport:{width:1440,height:900}});
  const pg = await ctx.newPage();

  pg.on('response', r => {
    if (r.url().includes('alpine') || r.url().includes('tailwind') || r.url().includes('jsdelivr')) {
      console.log('[CDN]', r.status(), r.url().substring(0, 100));
    }
  });

  try {
    await pg.goto('http://192.168.0.100:8883/workspace', {timeout:15000, waitUntil:'networkidle'});
    console.log('[OK] Page loaded');
    const alpineDefined = await pg.evaluate(() => typeof Alpine !== 'undefined');
    console.log('[Alpine defined]:', alpineDefined);
  } catch(e) {
    console.error('[ERR]:', e.message);
  }
  await b.close();
})();
