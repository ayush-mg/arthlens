import { expect, test } from '@playwright/test';

const webBaseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const businessId = 'c17ae2d8-31a2-4b65-a3f1-26010f3ec7ea';
const authToken = 'workspace-route-audit-token';
const workspace = {
  id: businessId,
  name: 'Orbit Route Audit',
  industry: 'Test workspace',
  created_at: '2026-01-01T00:00:00Z',
  role: 'OWNER',
  is_active: true,
};
const workspaceRoutes = [
  '',
  'sales',
  'purchases',
  'inventory',
  'khata',
  'finance',
  'decisions',
  'scenarios',
  'goals',
  'analytics',
  'agent',
  'customers',
  'suppliers',
  'reports',
  'audit',
  'members',
  'settings',
  'constellation',
];

test('the solar workspace entry opens all 18 workspace modules without blank routes', async ({ page }) => {
  test.setTimeout(120000);
  page.setDefaultTimeout(10000);
  const pageErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));

  // Keep the navigation check deterministic without depending on SMTP OTP delivery or a seeded local database.
  await page.route('**/auth/me', (route) => route.fulfill({ status: 200, json: { id: 'route-audit-user', email: 'route-audit@arthlens.local', roles: ['ENTREPRENEUR'], full_name: 'Route Audit' } }));
  await page.route('**/auth/refresh', (route) => route.fulfill({ status: 200, json: { access_token: authToken } }));
  await page.route('**/businesses**', async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/\/$/, '');
    if (path === '/businesses') {
      await route.fulfill({ status: 200, json: [workspace] });
    } else if (path === '/businesses/' + businessId) {
      await route.fulfill({ status: 200, json: workspace });
    } else if (path === '/businesses/' + businessId + '/cash-position') {
      await route.fulfill({ status: 200, json: { total_liquid_cash: 0, total_receivables: 0, total_payables: 0 } });
    } else if (path === '/businesses/' + businessId + '/analytics/pnl') {
      await route.fulfill({ status: 200, json: { data_quality_warnings: [] } });
    } else if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, json: [] });
    } else {
      await route.fulfill({ status: 200, json: {} });
    }
  });
  await page.addInitScript((token) => localStorage.setItem('arthlens_token', token), authToken);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(webBaseURL + '/workspaces');

  const workspaceCard = page.getByTestId('workspace-card-' + businessId);
  await expect(workspaceCard).toBeVisible();
  const enterButton = workspaceCard.getByRole('button', { name: /Enter/i });
  await expect(enterButton).toBeVisible();
  await enterButton.click();

  const overviewUrl = webBaseURL + '/workspaces/' + businessId;
  await page.waitForURL('**/workspaces/' + businessId, { timeout: 15000 });
  await expect(page).toHaveURL(overviewUrl);

  const sidebar = page.locator('aside.workspace-sidebar, aside');
  await expect(sidebar).toBeVisible();

  for (const route of workspaceRoutes.slice(1)) {
    const hrefPath = '/workspaces/' + businessId + '/' + route;
    const href = webBaseURL + hrefPath;
    const moduleLink = sidebar.locator('a[href="' + hrefPath + '"]').first();
    await expect(moduleLink).toBeVisible();
    await moduleLink.click();
    await page.waitForURL('**' + hrefPath, { timeout: 15000 });
    await expect(page).toHaveURL(href);
    await expect(page.locator('h1, h2, h3, main').first(), 'Route ' + route + ' failed. Browser errors: ' + pageErrors.join('; ')).toBeVisible();
  }

  await page.goto(webBaseURL + '/workspaces', { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveURL(webBaseURL + '/workspaces');

  expect(pageErrors, 'Browser errors: ' + pageErrors.join('; ')).toEqual([]);
});
