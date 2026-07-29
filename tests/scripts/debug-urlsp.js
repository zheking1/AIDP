const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  await p.goto('about:blank');
  const result = await p.evaluate(() => {
    try {
      const params = new URLSearchParams();
      params.set('name', 'test');
      params.set('description', 'hello world');
      return {
        toString: params.toString(),
        type: typeof URLSearchParams,
        name: URLSearchParams.name || 'unnamed',
      };
    } catch (e) {
      return { error: e.message, stack: e.stack };
    }
  });
  console.log('URLSearchParams test:', JSON.stringify(result));
  await b.close();
})();
