const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  await page.goto('http://192.168.0.100:8883/login', { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  // Debug 1: Global Rules
  console.log('--- Global Rules create ---');
  await page.goto('http://192.168.0.100:8883/rules/global', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("创建")');
  await page.waitForTimeout(1000);

  const allBtns = await page.$$eval('button', btns => btns.map(b => ({
    text: b.textContent.trim().substring(0, 30),
    cls: b.className.substring(0, 60),
    vis: b.offsetParent !== null,
    xclick: b.getAttribute('@click') || ''
  })));
  console.log('Visible buttons:', JSON.stringify(allBtns.filter(b => b.vis), null, 2));

  // Debug 2: Document buttons
  console.log('\n--- Document buttons ---');
  await page.goto('http://192.168.0.100:8883/knowledge/documents', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const docGrid = await page.$$('.grid > div');
  console.log('Doc grid items:', docGrid.length);

  if (docGrid.length > 0) {
    const firstDocBtns = await docGrid[0].$$eval('button', btns => btns.map(b => ({
      text: b.textContent.trim().substring(0, 30),
      title: b.title || '',
      cls: b.className.substring(0, 60),
      vis: b.offsetParent !== null
    })));
    console.log('First doc buttons:', JSON.stringify(firstDocBtns, null, 2));
  }

  // Debug 3: Document table structure
  const docTable = await page.$$('table tbody tr');
  console.log('Doc table rows:', docTable.length);
  if (docTable.length > 0) {
    const rowBtns = await docTable[0].$$eval('button', btns => btns.map(b => ({
      text: b.textContent.trim().substring(0, 30),
      title: b.title || '',
      cls: b.className.substring(0, 60),
      vis: b.offsetParent !== null
    })));
    console.log('Table row buttons:', JSON.stringify(rowBtns, null, 2));
  }

  await browser.close();
})();
