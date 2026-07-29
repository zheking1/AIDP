const { chromium } = require('playwright');
const BASE_URL = 'http://192.168.0.100:8883';

async function login(pg) {
  await pg.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await pg.fill('input[name="username"]', 'admin');
  await pg.fill('input[name="password"]', 'admin123');
  await pg.click('button[type="submit"]');
  await pg.waitForTimeout(2000);
}

async function openWorkspace(pg) {
  await pg.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(5000);
}

async function openTab(pg, tabId, name, icon, url) {
  await pg.evaluate(({ tabId, name, icon, url }) => {
    const ws = Alpine.$data(document.querySelector('[x-data="workspace()"]'));
    ws.openTab(tabId, name, `fas ${icon}`, url);
  }, { tabId, name, icon, url });
  await pg.waitForTimeout(5000);
}

async function cleanup(pg, apiPath) {
  try {
    await pg.evaluate(async (url) => { await fetch(url, { method: 'DELETE' }); }, apiPath);
  } catch (e) {}
}

module.exports = { BASE_URL, login, openWorkspace, openTab, cleanup };
