import { test, expect, devices, type Page, type Route, type Request } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE = 'https://tonita-deposable-manneristically.ngrok-free.dev';
const AUDIT_DIR = path.resolve('D:/BikeMaster/frontend/audit-screenshots');
const REPORT_PATH = 'D:/BikeMaster/frontend/audit-report.json';

if (!fs.existsSync(AUDIT_DIR)) fs.mkdirSync(AUDIT_DIR, { recursive: true });

const JWT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaXNfYWRtaW4iOnRydWUsImlzX2NsaWVudCI6dHJ1ZSwiaWF0IjoxNzg1NzM2MTk2LCJleHAiOjE3ODU4MjI1OTYsImlzcyI6ImJpa2VtYXN0ZXIiLCJhdWQiOiJiaWtlbWFzdGVyIiwianRpIjoiYXVkaXRfanRpXzAwMSIsInRlbmFudF9pZCI6MSwiYXRobGV0ZV9pZCI6MX0.mncbYwUvLgGlfsZQGc1V0R1jqWy1D_a19iVb1vjmww0';
const USER_JSON = JSON.stringify({
  id: 1, username: 'audit_admin', email: 'admin@test.com',
  is_admin: true, is_client: true, tenant_id: 1, active_athlete_id: 1
});

const reports: any[] = [];

test.describe.configure({ mode: 'serial' });

test.beforeEach(async ({ page }) => {
  // Add ngrok skip header only for ngrok URLs to avoid CORS on external resources
  await page.route('**/*.ngrok-free.dev/**', async (route: Route) => {
    const headers = { ...route.request().headers(), 'ngrok-skip-browser-warning': 'true' };
    await route.continue({ headers });
  });

  // Set auth state in sessionStorage before page load
  await page.addInitScript((token: string, user: string) => {
    sessionStorage.setItem('bikemaster_token', token);
    sessionStorage.setItem('bikemaster_user', user);
    sessionStorage.setItem('bikemaster_just_logged_in', 'false');
  }, JWT_TOKEN, USER_JSON);
});

async function auditRoute(page: Page, zone: string, route: string, filename: string, checks: string[] = []) {
  const consoleErrors: string[] = [];
  const consoleWarnings: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text().substring(0, 500));
    } else if (msg.type() === 'warning') {
      consoleWarnings.push(msg.text().substring(0, 300));
    }
  });
  page.on('pageerror', (err) => {
    consoleErrors.push('PAGE ERROR: ' + (err.message || String(err)).substring(0, 500));
  });

  const response = await page.goto(BASE + route, { timeout: 30000, waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // Try to wait for Vue app to mount
  try {
    await page.waitForFunction(() => document.querySelector('#app') && document.querySelector('#app')!.children.length > 0, { timeout: 10000 });
  } catch {
    await page.waitForTimeout(2000);
  }

  // Full page desktop screenshot
  await page.screenshot({ fullPage: true, path: path.join(AUDIT_DIR, filename), scale: 'css', type: 'png' });

  // Accessibility snapshot (depth 3)
  const snapshot = await page.accessibility.snapshot({ depth: 3 });

  // Verify critical elements
  const elementChecks = await page.evaluate((checksList: string[]) => {
    const results: Record<string, boolean> = {};
    checksList.forEach((sel: string) => {
      results[sel] = !!document.querySelector(sel);
    });
    return results;
  }, checks);

  const bodyText = await page.evaluate(() => document.body.innerText.trim().substring(0, 500));

  return {
    zone,
    route,
    status: response?.status() || 0,
    screenshot: filename,
    consoleErrors: consoleErrors.filter(e => !e.includes('ngrok')).slice(0, 10),
    consoleWarnings: consoleWarnings.filter(w => !w.includes('ngrok')).slice(0, 10),
    checks: elementChecks,
    bodyPreview: bodyText,
    hasApp: await page.evaluate(() => !!document.getElementById('app') && document.getElementById('app')!.children.length > 1),
    hasHeader: await page.evaluate(() => !!document.querySelector('header')),
    hasNav: await page.evaluate(() => !!document.querySelector('nav')),
    hasFooter: await page.evaluate(() => !!document.querySelector('footer')),
    snapshotChildren: snapshot?.children?.length || 0,
  };
}

test('ZONA 1: Welcome e pubbliche', async ({ page }) => {
  // Desktop
  await page.setViewportSize({ width: 1920, height: 1080 });
  const desktop = await auditRoute(page, 'welcome', '/welcome', 'welcome-desktop.png', [
    'h1', 'h2', 'button:has-text("Get Started")', 'a:has-text("Login")', 'nav', 'header', 'footer'
  ]);
  reports.push(desktop);

  // Mobile
  await page.setViewportSize({ width: 375, height: 667 });
  const response = await page.goto(BASE + '/welcome', { timeout: 30000, waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await page.screenshot({ fullPage: true, path: path.join(AUDIT_DIR, 'welcome-mobile.png'), scale: 'css', type: 'png' });
  const mobile = {
    zone: 'welcome-mobile',
    route: '/welcome',
    status: response?.status() || 0,
    screenshot: 'welcome-mobile.png',
    consoleErrors: [],
    issues: [],
    notes: 'Mobile viewport 375x667'
  };
  reports.push(mobile);

  fs.writeFileSync(REPORT_PATH, JSON.stringify(reports, null, 2));
});
