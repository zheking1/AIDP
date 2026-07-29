const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({headless:true});
  const ctx = await b.newContext({viewport:{width:1440,height:900}});
  const pg = await ctx.newPage();

  pg.on('response', r => {
    console.log('[RESP]', r.status(), r.url().substring(0, 120));
  });
  pg.on('requestfailed', r => {
    console.log('[FAIL]', r.failure().errorText, r.url().substring(0, 120));
  });

  try {
    const resp = await pg.goto('http://192.168.0.100:8883/workspace', {timeout:15000, waitUntil:'domcontentloaded'});
    console.log('[PAGE]', resp.status());
    await pg.waitForTimeout(5000);
    const html = await pg.content();
    // Check what scripts are in the page
    const scripts = await pg.evaluate(() => {
      return Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
    });
    console.log('[SCRIPTS]:', scripts);
    const alpineDefined = await pg.evaluate(() => typeof Alpine !== 'undefined');
    console.log('[Alpine]:', alpineDefined);
  } catch(e) {
    console.error('[ERR]:', e.message);
  }
  await b.close();
})();
