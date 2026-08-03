import { test, type Page, type Route } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE = 'https://tonita-deposable-manneristically.ngrok-free.dev';
const AUDIT_DIR = path.resolve('D:/BikeMaster/frontend/audit-screenshots');
const REPORT_PATH = 'D:/BikeMaster/frontend/audit-report.json';

if (!fs.existsSync(AUDIT_DIR)) fs.mkdirSync(AUDIT_DIR, { recursive: true });

const JWT_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaXNfYWRtaW4iOnRydWUsImlzX2NsaWVudCI6dHJ1ZSwiaWF0IjoxNzg1NzM2MTk2LCJleHAiOjE3ODU4MjI1OTYsImlzcyI6ImJpa2VtYXN0ZXIiLCJhdWQiOiJiaWtlbWFzdGVyIiwianRpIjoiYXVkaXRfanRpXzAwMSIsInRlbmFudF9pZCI6MSwiYXRobGV0ZV9pZCI6MX0.mncbYwUvLgGlfsZQGc1V0R1jqWy1D_a19iVb1vjmww0';
const USER_JSON = JSON.stringify({
  id: 1,
  username: 'audit_admin',
  email: 'admin@test.com',
  is_admin: true,
  is_client: true,
  tenant_id: 1,
  active_athlete_id: 1,
});

interface AuditEntry {
  zone: string;
  route: string;
  status: string;
  screenshot: string;
  consoleErrors: string[];
  issues: string[];
  missingElements: string[];
  notes: string;
}

const reports: AuditEntry[] = [];

async function auditRoute(
  page: Page,
  zone: string,
  route: string,
  filename: string,
  checks: Record<string, string> = {},
  mobile = false,
): Promise<void> {
  const consoleErrors: string[] = [];
  const consoleWarnings: string[] = [];

  page.off('console', () => {});
  page.off('pageerror', () => {});

  page.on('console', (msg) => {
    const text = msg.text() || '';
    const url = msg.location()?.url || '';
    if (msg.type() === 'error') {
      if (!url.includes('fonts.gstatic.com') && !url.includes('google.com')) {
        consoleErrors.push(text.substring(0, 300));
      }
    } else if (msg.type() === 'warning') {
      consoleWarnings.push(text.substring(0, 200));
    }
  });
  page.on('pageerror', (err) => {
    consoleErrors.push('PAGE ERROR: ' + (err.message || String(err)).substring(0, 300));
  });

  const response = await page.goto(BASE + route, { timeout: 30000, waitUntil: 'networkidle' });
  await page.waitForTimeout(4000);

  // Wait for Vue to mount (app div should have more than just the loading state)
  try {
    await page.waitForFunction(
      () => {
        const app = document.getElementById('app');
        if (!app) return false;
        // Check that app has meaningful content (more than just loading spinner)
        const innerHTML = app.innerHTML;
        return innerHTML.length > 100 && !innerHTML.includes('app-loading');
      },
      { timeout: 15000 },
    );
  } catch {
    await page.waitForTimeout(2000);
  }

  // Screenshot
  await page.screenshot({
    fullPage: true,
    path: path.join(AUDIT_DIR, filename),
    scale: 'css',
    type: 'png',
  });

  // Accessibility snapshot
  let snapshot: any;
  try {
    snapshot = await page.accessibility.snapshot({ depth: 3 });
  } catch {
    snapshot = null;
  }

  // Element checks
  const missingElements: string[] = [];
  const foundElements: string[] = [];
  for (const [label, selector] of Object.entries(checks)) {
    const found = await page.$(selector);
    if (found) {
      foundElements.push(label);
    } else {
      missingElements.push(label);
    }
  }

  // Get basic page info
  const pageInfo = await page.evaluate(() => ({
    title: document.title,
    h1: document.querySelector('h1')?.textContent || null,
    hasHeader: !!document.querySelector('header'),
    hasNav: !!document.querySelector('nav'),
    hasFooter: !!document.querySelector('footer'),
    bodyText: document.body.innerText.trim().substring(0, 500),
  }));

  // Determine status
  let status: 'ok' | 'warning' | 'error' = 'ok';
  const apiErrors = consoleErrors.filter((e) => e.includes('/api/') && (e.includes('401') || e.includes('403') || e.includes('500')));
  if (apiErrors.length > 0) {
    status = 'warning';
  }
  const realErrors = consoleErrors.filter((e) => !e.includes('ngrok') && !e.includes('fonts') && !e.includes('favicon'));
  if (realErrors.length > 0) {
    status = 'warning';
  }
  if (response && response.status() >= 400 && response.status() !== 401) {
    status = 'error';
  }

  reports.push({
    zone,
    route,
    status,
    screenshot: filename,
    consoleErrors: realErrors.slice(0, 10),
    issues: [],
    missingElements,
    notes: `Viewport: ${mobile ? '375x667 (mobile)' : '1920x1080 (desktop)'}. Found: ${foundElements.join(', ') || 'none'}. Page title: ${pageInfo.title}. Status code: ${response?.status() || 'N/A'}.`,
  });
}

test.describe('Frontend Visual & Functional Audit', () => {
  test.beforeEach(async ({ page }) => {
    // Route interception: add ngrok skip header only for ngrok URLs
    await page.route('**/*.ngrok-free.dev/**', async (route: Route) => {
      const headers = { ...route.request().headers(), 'ngrok-skip-browser-warning': 'true' };
      await route.continue({ headers });
    });

    // Set auth state in sessionStorage before every page load
    await page.addInitScript((token: string, user: string) => {
      sessionStorage.setItem('bikemaster_token', token);
      sessionStorage.setItem('bikemaster_user', user);
      sessionStorage.setItem('bikemaster_just_logged_in', 'false');
    }, JWT_TOKEN, USER_JSON);
  });

  test.afterAll(async () => {
    // Save consolidated report
    const summary = {
      timestamp: new Date().toISOString(),
      totalZones: reports.length,
      zonesByStatus: {
        ok: reports.filter((r) => r.status === 'ok').length,
        warning: reports.filter((r) => r.status === 'warning').length,
        error: reports.filter((r) => r.status === 'error').length,
      },
      reports,
    };
    fs.writeFileSync(REPORT_PATH, JSON.stringify(summary, null, 2));
    console.log('Report saved to', REPORT_PATH);
  });

  test('ZONA 1: Welcome e pubbliche', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'welcome', '/welcome', 'welcome-desktop.png', {
      'Hero H1': 'h1',
      'Subheading H2': 'h2',
      'CTA Get Started': 'button:has-text("Get Started")',
      'Login link': 'a:has-text("Login")',
      'Footer': 'footer',
    });

    await page.setViewportSize({ width: 375, height: 667 });
    await auditRoute(page, 'welcome-mobile', '/welcome', 'welcome-mobile.png', {
      'Hero H1': 'h1',
      'CTA Get Started': 'button:has-text("Get Started")',
    }, true);
  });

  test('ZONA 2: Rides (lista uscite)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'rides', '/rides', 'rides-list.png', {
      'Rides list container': '.rides-list, .ride-list, [class*="ride"]',
      'Filter controls': 'select, input[type="date"], input[placeholder*="Filter"]',
      'Stats summary': '[class*="stat"], [class*="summary"], [class*="total"]',
    });
  });

  test('ZONA 3: Dashboard', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'dashboard', '/dashboard', 'dashboard.png', {
      'KPI widgets': '[class*="kpi"], [class*="metric"], [class*="stat"]',
      'Charts': 'canvas, svg',
      'Athlete info': '[class*="athlete"]',
    });
  });

  test('ZONA 4: Import', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'import', '/import', 'import-panel.png', {
      'Drop zone': '[class*="drop"], [class*="drag"]',
      'File input': 'input[type="file"]',
      'Import list': '[class*="import-list"], [class*="history"]',
    });
  });

  test('ZONA 5: Athlete e Avatar', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'athlete', '/athlete', 'athlete-profile.png', {
      'Profile form': 'form',
      'Save button': 'button:has-text("Save")',
    });
    await auditRoute(page, 'avatar', '/avatar', 'avatar-panel.png', {
      'Avatar 2D': '[class*="avatar"], canvas, svg',
      'Equipment section': '[class*="equipment"]',
    });
  });

  test('ZONA 6: AI Coach', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'coach', '/coach', 'coach-panel.png', {
      'Chat interface': '[class*="chat"], [class*="message"]',
      'Input area': 'input[type="text"], textarea, [class*="input"]',
    });
  });

  test('ZONA 7: Knowledge e BM2', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'knowledge', '/knowledge', 'knowledge.png', {
      'Search bar': 'input[type="search"], input[placeholder*="Search"]',
      'Topic list': '[class*="topic"], [class*="article"]',
    });
    await auditRoute(page, 'bm2', '/bm2', 'bm2-panel.png', {
      'Simulator': '[class*="simulator"], button',
      'Power chart': 'canvas, svg',
    });
  });

  test('ZONA 8: Calendar e Granfondo', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'calendar', '/calendar', 'calendar.png', {
      'Calendar grid': '[class*="calendar"], table, .day',
      'Event items': '[class*="event"], [class*="activity"]',
    });
    await auditRoute(page, 'granfondo', '/granfondo', 'granfondo.png', {
      'Planner': '[class*="planner"], [class*="granfondo"]',
      'Stages': '[class*="stage"]',
    });
  });

  test('ZONA 9: Maps, POI, Itinerary, AetherMap', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'map', '/map', 'map-ride.png', {
      'Map container': '[class*="map"], #map',
      'Markers': '[class*="marker"], .leaflet',
    });
    await auditRoute(page, 'pois', '/pois', 'pois-map.png', {
      'POI list': '[class*="poi"], [class*="point"]',
    });
    await auditRoute(page, 'itinerary', '/itinerary', 'itinerary-builder.png', {
      'Itinerary builder': '[class*="itinerary"], [class*="stage"]',
    });
    await auditRoute(page, 'aethermap', '/aethermap', 'aethermap.png', {
      '3D map': 'canvas, [class*="aethermap"], [class*="3d"]',
    });
  });

  test('ZONA 10: Comparison, Heatmap, Badges, Weather, Zones', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'comparison', '/comparison', 'comparison.png', {
      'Comparison chart': 'canvas, svg',
    });
    await auditRoute(page, 'heatmap', '/heatmap', 'heatmap.png', {
      'Heatmap': 'canvas, svg, [class*="heat"]',
    });
    await auditRoute(page, 'badges', '/badges', 'badges.png', {
      'Badge list': '[class*="badge"]',
    });
    await auditRoute(page, 'weather', '/weather', 'weather.png', {
      'Weather info': '[class*="weather"], [class*="forecast"]',
    });
    await auditRoute(page, 'zones', '/zones', 'zones.png', {
      'Zone chart': 'canvas, svg',
    });
  });

  test('ZONA 11: Metabolism, Beck, Performance', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'metabolism', '/metabolism', 'metabolism.png', {
      'Metabolism info': '[class*="metabolism"], [class*="bmr"], [class*="tdee"]',
    });
    await auditRoute(page, 'beck', '/beck', 'beck.png', {
      'Beck analysis': '[class*="beck"]',
    });
    await auditRoute(page, 'performance', '/performance', 'performance.png', {
      'Performance charts': 'canvas, svg',
    });
  });

  test('ZONA 12: Admin, Client, Monitoring', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'admin', '/admin', 'admin.png', {
      'Admin panel': '[class*="admin"]',
    });
    await auditRoute(page, 'admin-bm2', '/admin/bm2', 'admin-bm2.png', {
      'BM2 admin': '[class*="admin"], [class*="bm2"]',
    });
    await auditRoute(page, 'admin-users', '/admin/users', 'admin-users.png', {
      'User management': '[class*="user"], table',
    });
    await auditRoute(page, 'client', '/client', 'client-panel.png', {
      'Client dashboard': '[class*="client"]',
    });
    await auditRoute(page, 'monitoring', '/monitoring', 'monitoring.png', {
      'Monitoring': '[class*="monitor"], table, [class*="log"]',
    });
  });

  test('ZONA 13: Tracking e HR 24h', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'track', '/track', 'tracking-live.png', {
      'Map container': '[class*="map"], #map, canvas',
      'Start/Stop button': 'button:has-text("Start"), button:has-text("Stop")',
    });
    await auditRoute(page, 'hr24h', '/hr24h', 'hr24h.png', {
      'HR chart': 'canvas, svg',
    });
  });

  test('ZONA 14: Settings e Connections', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'settings', '/settings', 'settings.png', {
      'Settings form': 'form',
      'Theme toggle': '[class*="theme"]',
    });
    await auditRoute(page, 'connections', '/settings/connections', 'connections.png', {
      'OAuth connections': '[class*="connection"], [class*="oauth"]',
    });
  });

  test('ZONA 15: Pubbliche statiche', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await auditRoute(page, 'privacy', '/privacy', 'privacy.png', {
      'Privacy text': 'p, .prose',
    });
    await auditRoute(page, 'about', '/about', 'about.png', {
      'About text': 'p, .prose',
    });
    await auditRoute(page, 'contact', '/contact', 'contact.png', {
      'Contact form': 'form',
    });
  });
});
