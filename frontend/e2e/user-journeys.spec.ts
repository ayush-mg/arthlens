import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const SCREENSHOT_DIR = path.resolve(__dirname, '../screenshots');

async function ensureAuthenticated(page: any) {
  const sessionBtn = page.locator('button[aria-label="User RBAC Role and Account Session"]');
  if (await sessionBtn.isVisible()) {
    return;
  }
  const signInBtn = page.getByTestId('navbar-sign-in-btn');
  try {
    if (await signInBtn.isVisible()) {
      await signInBtn.click();
      await page.locator('input[type="email"]').fill('entrepreneur@arthlens.org');
      await page.locator('input[type="password"]').fill('Password123!');
      await page.locator('form').getByRole('button', { name: 'Sign In with Credentials' }).click();
      await expect(sessionBtn).toBeVisible({ timeout: 10000 });
    }
  } catch {
    if (await sessionBtn.isVisible()) {
      return;
    }
  }
}

test.beforeAll(() => {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
});

test.describe('ArthLens Architecture: Dedicated Homepage & Dedicated /app Route', () => {

  test('Route Architecture: Root Homepage (/) vs Workspace (/app)', async ({ page }) => {
    // 1. Visit root route /
    await page.goto('/');
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Verify CinematicNavbar is present
    await expect(page.getByRole('navigation', { name: 'Story Chapters' })).toBeVisible();
    await expect(page.locator('header').getByRole('link', { name: 'LAUNCH ATLAS' })).toBeVisible();
    await expect(page.locator('header').getByRole('link', { name: 'Evidence Graph' })).toBeVisible();

    // Verify workspace components are NOT on root route
    await expect(page.locator('input[placeholder*="Search 800"]')).not.toBeVisible();
    await expect(page.locator('button[aria-label="User RBAC Role and Account Session"]')).not.toBeVisible();
    await expect(page.locator('#atlas-workspace')).not.toBeVisible();

    // Verify 9-scene narrative is present
    await expect(page.locator('#scene-01-prologue')).toBeVisible();
    await expect(page.locator('#scene-02-landscape')).toBeVisible();
    await expect(page.locator('#scene-03-problem')).toBeVisible();
    await expect(page.locator('#scene-04-atlas')).toBeVisible();
    await expect(page.locator('#scene-05-evidence')).toBeVisible();
    await expect(page.locator('#scene-06-simulation')).toBeVisible();
    await expect(page.locator('#scene-07-policy')).toBeVisible();
    await expect(page.locator('#scene-08-agentic')).toBeVisible();
    await expect(page.locator('#scene-09-enter')).toBeVisible();

    // 2. Click "LAUNCH ATLAS" in CinematicNavbar -> Navigates to /app
    await page.locator('header').getByRole('link', { name: 'LAUNCH ATLAS' }).click();
    await page.waitForURL('**/app');
    expect(page.url()).toContain('/app');

    // Verify /app contains functional workspace Navbar
    await expect(page.locator('text=Epistemic Atlas')).toBeVisible();
    await expect(page.locator('button:has-text("Atlas Map")')).toBeVisible();
    await expect(page.locator('button:has-text("Evidence Graph")')).toBeVisible();
    await expect(
      page.locator('button[aria-label="User RBAC Role and Account Session"]').or(page.getByTestId('navbar-sign-in-btn'))
    ).toBeVisible();

    // Verify workspace components are present on /app
    await expect(page.locator('#atlas-workspace')).toBeVisible();
    await expect(page.locator('input[placeholder*="Search 800"]')).toBeVisible();

    // 3. Test Navigation to Evidence Graph via URL parameter (?view=graph)
    await page.goto('/app?view=graph');
    await page.waitForTimeout(600);
    // Verify Evidence Graph is active tab
    await expect(page.locator('text=Cytoscape Evidence Graph')).toBeVisible();

    // 4. Test Brand Link returns to /
    const returnLink = page.getByTitle('Return to Overview');
    await expect(returnLink).toBeVisible();
    await returnLink.click();
    await page.waitForURL('**/');
    expect(page.url()).not.toContain('/app');
    await expect(page.getByRole('navigation', { name: 'Story Chapters' })).toBeVisible();
  });

  test('Journey 1: Geographic Discovery across 800-Unit Baseline (/app)', async ({ page }) => {
    await page.goto('/app');
    await ensureAuthenticated(page);

    // Verify page loads with authoritative brand header
    await expect(page.getByRole('banner').getByText('ArthLens', { exact: true })).toBeVisible();
    await expect(page.locator('text=Epistemic Atlas')).toBeVisible();

    // 1. Search for Bhopal (LGD: 396, State: Madhya Pradesh)
    const searchInput = page.locator('input[placeholder*="Search 800"]');
    const searchDropdown = page.locator('div.max-h-64');
    await searchInput.fill('Bhopal');
    await page.waitForTimeout(500);

    const bhopalOption = searchDropdown.locator('button:has-text("Bhopal")').first();
    await expect(bhopalOption).toBeVisible();
    await bhopalOption.click();

    // Verify breadcrumb shows Madhya Pradesh -> Bhopal
    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Madhya Pradesh');
    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Bhopal');
    await expect(page.locator('text=Canonical ID: in:district:396')).toBeVisible();

    // 2. Search for Lucknow (LGD: 162, State: Uttar Pradesh)
    await searchInput.fill('Lucknow');
    await page.waitForTimeout(500);
    const lucknowOption = searchDropdown.locator('button:has-text("Lucknow")').first();
    await expect(lucknowOption).toBeVisible();
    await lucknowOption.click();

    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Uttar Pradesh');
    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Lucknow');
    await expect(page.locator('text=Canonical ID: in:district:162')).toBeVisible();

    // 3. Search for Jaipur (LGD: 102, State: Rajasthan)
    await searchInput.fill('Jaipur');
    await page.waitForTimeout(500);
    const jaipurOption = searchDropdown.locator('button:has-text("Jaipur")').first();
    await expect(jaipurOption).toBeVisible();
    await jaipurOption.click();

    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Rajasthan');
    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Jaipur');
    await expect(page.locator('text=Canonical ID: in:district:102')).toBeVisible();

    // 4. Search for Kanpur Dehat (LGD: 156, State: Uttar Pradesh)
    await searchInput.fill('Kanpur Dehat');
    await page.waitForTimeout(500);
    const kanpurOption = searchDropdown.locator('button:has-text("Kanpur Dehat")').first();
    await expect(kanpurOption).toBeVisible();
    await kanpurOption.click();

    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Uttar Pradesh');
    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Kanpur Dehat');
    await expect(page.locator('text=Canonical ID: in:district:156')).toBeVisible();

    // 5. Return to Prayagraj (LGD: 120, Pilot District)
    await searchInput.fill('Prayagraj');
    await page.waitForTimeout(500);
    const prayagrajOption = searchDropdown.locator('button:has-text("Prayagraj")').first();
    await expect(prayagrajOption).toBeVisible();
    await prayagrajOption.click();

    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Uttar Pradesh');
    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toContainText('Prayagraj');
    await expect(page.locator('text=Canonical ID: in:district:120')).toBeVisible();
  });

  test('Journey 2: Geographic Visualization (Prayagraj vs Varanasi)', async ({ page, request }) => {
    // 1. Authenticate with backend
    const loginRes = await request.post('http://127.0.0.1:8000/auth/login', {
      data: {
        email: 'entrepreneur@arthlens.org',
        password: 'Password123!',
      },
    });
    expect(loginRes.status()).toBe(200);
    const token = (await loginRes.json()).access_token;
    const authHeaders = { Authorization: `Bearer ${token}` };

    // Verify Canonical API records for Prayagraj and Varanasi
    const prayagrajApi = await request.get('http://127.0.0.1:8000/geo/in:district:120', { headers: authHeaders });
    expect(prayagrajApi.status()).toBe(200);
    const prayagrajJson = await prayagrajApi.json();
    expect(prayagrajJson.id).toBe('in:district:120');
    expect(prayagrajJson.lgd_code).toBe('120');
    expect(prayagrajJson.census_code).toBe('175');
    expect(prayagrajJson.geometry_status).toBe('GEOMETRY_VERIFIED');

    const varanasiApi = await request.get('http://127.0.0.1:8000/geo/in:district:187', { headers: authHeaders });
    expect(varanasiApi.status()).toBe(200);
    const varanasiJson = await varanasiApi.json();
    expect(varanasiJson.id).toBe('in:district:187');
    expect(varanasiJson.lgd_code).toBe('187');
    expect(varanasiJson.census_code).toBe('197');
    expect(varanasiJson.geometry_status).toBe('GEOMETRY_MISSING');

    // Track OpenStreetMap basemap tile network requests
    let osmTileRequested = false;
    let osmTileReceived = false;
    page.on('request', (req) => {
      if (req.url().includes('tile.openstreetmap.org')) {
        osmTileRequested = true;
      }
    });
    page.on('response', (res) => {
      if (res.url().includes('tile.openstreetmap.org') && (res.status() === 200 || res.status() === 304)) {
        osmTileReceived = true;
      }
    });

    await page.goto('/app');
    await ensureAuthenticated(page);

    // 1. Prayagraj (Pilot with Verified Geometry: LGD 120, Census 175, in:district:120)
    await page.locator('button:has-text("Prayagraj")').first().click();
    await expect(page.locator('text=LGD 120 • Census 175').first()).toBeVisible();
    await expect(page.locator('text=GEOM: GEOMETRY_VERIFIED').first()).toBeVisible();
    await expect(page.locator('text=Vector Overlay: Prayagraj')).toBeVisible();
    // Invariant: Source-gated limitation card must NOT appear for Prayagraj
    await expect(page.locator('text=Administrative Boundary Source-Gated')).not.toBeVisible();

    // Verify MapLibre loaded and verified boundary layer is rendered via queryRenderedFeatures()
    await page.waitForFunction(() => {
      const map = (window as any)._atlasMap;
      return map && (window as any)._atlasMapLoaded;
    }, { timeout: 15000 });

    // Wait slightly for boundary GeoJSON data to load into source and render
    await page.waitForTimeout(1200);

    const boundaryFeatures = await page.evaluate(() => {
      const map = (window as any)._atlasMap;
      if (!map) return [];
      const feats = map.queryRenderedFeatures({ layers: ['pilot-boundary-strokes'] });
      return feats.map((f: any) => ({
        id: f.id,
        properties: f.properties,
      }));
    });
    expect(boundaryFeatures.length).toBeGreaterThan(0);
    expect(boundaryFeatures[0].properties.lgd_code).toBe('120');

    // Confirm that OpenStreetMap basemap tiles were requested
    expect(osmTileRequested).toBe(true);

    // 2. Varanasi (Missing Geometry: LGD 187, Census 197, in:district:187)
    const varanasiPill = page.locator('button:has-text("Varanasi")').first();
    await varanasiPill.click();
    await page.waitForTimeout(1000); // Allow selection to settle

    await expect(page.locator('text=LGD 187 • Census 197').first()).toBeVisible();
    await expect(page.locator('text=GEOM: GEOMETRY_MISSING').first()).toBeVisible();

    // Verify compact unobtrusive status indicator is displayed (never a blocking oversized card or overlay)
    await expect(page.locator('[data-testid="missing-geometry-indicator"]')).toBeVisible();
    await expect(page.locator('text=Boundary unmapped')).toBeVisible();
    await expect(page.locator('text=Varanasi Administrative Boundary Source-Gated')).not.toBeVisible();

    // Verify geographic selector remains completely usable
    const searchInput = page.locator('input[placeholder*="Search 800 baseline districts"]');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).not.toBeDisabled();

    // Verify boundary layer for Varanasi has no rendered features
    const varanasiBoundaryFeatures = await page.evaluate(() => {
      const map = (window as any)._atlasMap;
      if (!map) return [];
      return map.queryRenderedFeatures({ layers: ['pilot-boundary-strokes'] });
    });
    expect(varanasiBoundaryFeatures.length).toBe(0);

    // 3. Switch back to Prayagraj (LGD 120) and verify immediate boundary re-render
    const prayagrajPill = page.locator('button:has-text("Prayagraj")').first();
    await prayagrajPill.click();
    await page.waitForTimeout(1000);

    // Back to Prayagraj
    await expect(page.locator('text=GEOM: GEOMETRY_VERIFIED').first()).toBeVisible();
    await expect(page.locator('[data-testid="missing-geometry-indicator"]')).not.toBeVisible();
    const returnBoundaryFeatures = await page.evaluate(() => {
      const map = (window as any)._atlasMap;
      if (!map) return [];
      return map.queryRenderedFeatures({ layers: ['pilot-boundary-strokes'] });
    });
    expect(returnBoundaryFeatures.length).toBeGreaterThan(0);

    // 4. Test basemap pan & zoom interaction
    await page.evaluate(() => {
      const map = (window as any)._atlasMap;
      if (map) {
        map.zoomTo(10, { duration: 0 });
        map.panBy([20, 20], { duration: 0 });
      }
    });
    const mapZoom = await page.evaluate(() => (window as any)._atlasMap?.getZoom());
    expect(mapZoom).toBeCloseTo(10, 0);

    // 5. Test rapid selection race condition guard (switch Prayagraj -> Varanasi rapidly)
    await prayagrajPill.click();
    await varanasiPill.click();
    await page.waitForTimeout(1200);
    // Final state must settle on Varanasi with 0 boundary features and no Prayagraj polygon
    await expect(page.locator('text=GEOM: GEOMETRY_MISSING').first()).toBeVisible();
    await expect(page.locator('[data-testid="missing-geometry-indicator"]')).toBeVisible();
    const rapidBoundaryFeatures = await page.evaluate(() => {
      const map = (window as any)._atlasMap;
      if (!map) return [];
      return map.queryRenderedFeatures({ layers: ['pilot-boundary-strokes'] });
    });
    expect(rapidBoundaryFeatures.length).toBe(0);

    // 6. Test simulated API failure shows error indicator, NOT missing geometry
    // Intercept boundary request to simulate 500 error (matches encoded or unencoded URL)
    const boundaryRoutePattern = /.*\/geo\/.*\/boundary/;
    await page.route(boundaryRoutePattern, async (route) => {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Simulated API failure' }) });
    });
    await prayagrajPill.click();
    await page.waitForTimeout(1000);
    // Boundary error indicator must appear; missing geometry indicator must NOT appear
    await expect(page.locator('[data-testid="boundary-error-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="missing-geometry-indicator"]')).not.toBeVisible();
    // Unroute to restore normal behavior
    await page.unroute(boundaryRoutePattern);

    // Restore Prayagraj with working API
    await varanasiPill.click();
    await page.waitForTimeout(500);
    await prayagrajPill.click();
    await page.waitForTimeout(1000);
    await expect(page.locator('text=GEOM: GEOMETRY_VERIFIED').first()).toBeVisible();

    // 7. Verify zero fabricated boundary for unmapped districts (e.g. Bhopal LGD 396)
    const searchDropdown = page.locator('div.max-h-64');
    await searchInput.fill('Bhopal');
    await page.waitForTimeout(500);
    const bhopalOption = searchDropdown.locator('button:has-text("Bhopal")').first();
    if (await bhopalOption.isVisible()) {
      await bhopalOption.click();
      await page.waitForTimeout(1000);
      await expect(page.locator('text=GEOM: GEOMETRY_MISSING').first()).toBeVisible();
      await expect(page.locator('[data-testid="missing-geometry-indicator"]')).toBeVisible();
      const bhopalBoundaryFeatures = await page.evaluate(() => {
        const map = (window as any)._atlasMap;
        if (!map) return [];
        return map.queryRenderedFeatures({ layers: ['pilot-boundary-strokes'] });
      });
      expect(bhopalBoundaryFeatures.length).toBe(0);
    }

    // Invariant: MapLibre has genuine PMTiles vector source registered
    const hasPmtilesSource = await page.evaluate(() => {
      const map = (window as any)._atlasMap;
      return map && map.getSource('pilot-pmtiles-source') !== undefined;
    });
    expect(hasPmtilesSource).toBe(true);
  });

  test('Journey 3: Economic Indicators Real Backend Data & Zero Synthetic Demo Values', async ({ page }) => {
    await page.goto('/app');
    await ensureAuthenticated(page);
    await page.locator('button:has-text("Prayagraj")').first().click();
    await page.waitForTimeout(800);

    // Scroll to economic indicators section
    const indicatorsSection = page.locator('section[aria-label="Economic Indicators"]');
    await expect(indicatorsSection).toBeVisible();

    // 1. Prayagraj (Pilot District with Verified Official Census 2011 DS-05 Ingestion)
    // Verify truthful Ledger-backed indicators header shows populated indicators
    await expect(page.locator('text=Ledger-backed Economic Indicators')).toBeVisible();

    // Real official population observation: 59,54,391 persons (formatted en-IN)
    await expect(page.locator('text=population.total')).toBeVisible();
    await expect(page.locator('text=59,54,391')).toBeVisible();
    await expect(page.locator('text=persons').first()).toBeVisible();

    // Real official households observation: 9,76,733 dimensionless
    await expect(page.locator('text=households.total')).toBeVisible();
    await expect(page.locator('text=9,76,733')).toBeVisible();

    // Verify STALE status badge (2011-03-01 is > 10 years old according to Handbook freshness rules)
    const staleBadges = page.locator('text=STALE');
    await expect(staleBadges.first()).toBeVisible();

    // Verify unpersisted indicators remain fail-closed UNAVAILABLE (never mock numbers)
    await expect(page.locator('text=demand.monthly')).toBeVisible();
    await expect(page.locator('text=Unavailable').first()).toBeVisible();

    // 2. Click population.total indicator card -> Opens Provenance Drawer
    const popCard = page.locator('button[aria-label*="population.total"]');
    await popCard.click();

    // Provenance Drawer verifies Epistemic Floor 4 & Official DS-05 Checksum
    await expect(page.locator('text=Epistemic Ledger Record')).toBeVisible();
    await expect(page.locator('text=Floor 4').first()).toBeVisible();
    await expect(page.locator('text=Source Registry Authority')).toBeVisible();
    await expect(page.locator('.max-w-md').getByText('Office of the Registrar General & Census Commissioner, India', { exact: true })).toBeVisible();
    await expect(page.locator('text=55a424884c0674b4464bfdfb7ee6357f8d615e4c2c187042c5880488999626db')).toBeVisible();
    await expect(page.locator('text=Observation date 2011-03-01 is STALE')).toBeVisible();

    // Close drawer
    await page.locator('button[aria-label="Close provenance drawer"]').click();
    await page.waitForTimeout(300);

    // 3. Switch to Varanasi (in:district:187 - Zero Ingested Quantities)
    await page.locator('button:has-text("Varanasi")').first().click();
    await page.waitForTimeout(1000);

    // Fail-closed invariant: Varanasi has no ingested indicators -> Indicators are UNAVAILABLE
    const unavailableBadges = page.locator('text=UNAVAILABLE');
    await expect(unavailableBadges.first()).toBeVisible();
    await expect(page.locator('text=Unavailable').first()).toBeVisible();
    // Invariant: Missing quantities are never presented as numeric zero
    await expect(page.locator('text=0 persons')).not.toBeVisible();
    // Stale guard invariant: Prayagraj's specific population observation must NOT be displayed under Varanasi
    await expect(page.locator('text=59,54,391')).not.toBeVisible();
  });

  test('Journey 4: Provenance Drawer Epistemic Attributes & Direct Ledger Query', async ({ page }) => {
    await page.goto('/app');
    await ensureAuthenticated(page);

    // Ensure Prayagraj is selected
    await page.locator('button:has-text("Prayagraj")').first().click();
    await page.waitForTimeout(800);

    // Open Provenance Drawer by clicking households.total
    const householdsCard = page.locator('button[aria-label*="households.total"]');
    await expect(householdsCard).toBeVisible();
    await householdsCard.click();

    // Verify Epistemic Attributes inside Provenance Drawer
    const drawer = page.locator('.max-w-md');
    await expect(drawer.locator('text=Epistemic Ledger Record')).toBeVisible();
    await expect(drawer.locator('text=Floor 4').first()).toBeVisible();
    await expect(drawer.locator('text=OBSERVED').first()).toBeVisible();
    await expect(drawer.locator('text=SUITABLE_HISTORICAL_ONLY')).toBeVisible();
    await expect(drawer.locator('text=Floor Monotonicity Ladder')).toBeVisible();
    await expect(drawer.locator('text=Invariant Validated')).toBeVisible();

    // Verify SHA-256 Checksum
    await expect(drawer.locator('text=55a424884c0674b4464bfdfb7ee6357f8d615e4c2c187042c5880488999626db')).toBeVisible();

    // Test "Explore in Evidence Graph" button
    const inspectGraphBtn = page.locator('button:has-text("Explore in Evidence Graph")');
    await expect(inspectGraphBtn).toBeVisible();
    await inspectGraphBtn.click();

    // Verifies view switched to graph and drawer closed
    await page.waitForTimeout(500);
    await expect(page.locator('text=Cytoscape Evidence Graph')).toBeVisible();
  });

  test('Journey 5: Cytoscape Evidence Graph DAG Rendering & Controls', async ({ page }) => {
    await page.goto('/app?view=graph');
    await ensureAuthenticated(page);

    // Verify Evidence Graph component is mounted
    await expect(page.locator('text=Cytoscape Evidence Graph')).toBeVisible();
    await expect(page.getByRole('button', { name: 'all', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'quantity', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'claim', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'calculation', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'source', exact: true })).toBeVisible();

    // Verify zoom controls are present and clickable
    const zoomInBtn = page.locator('button[aria-label="Zoom in"]');
    const zoomOutBtn = page.locator('button[aria-label="Zoom out"]');
    const fitBtn = page.locator('button[aria-label="Fit view"]');

    await expect(zoomInBtn).toBeVisible();
    await expect(zoomOutBtn).toBeVisible();
    await expect(fitBtn).toBeVisible();

    await zoomInBtn.click();
    await zoomOutBtn.click();
    await fitBtn.click();
  });

  test('Journey 6: Authentication, Authorization & Real Backend RBAC Matrix', async ({ page, request }) => {
    // 1. Unauthenticated request to protected endpoint fails with 401
    const unauthRes = await request.get('http://127.0.0.1:8000/geo/units');
    expect(unauthRes.status()).toBe(401);

    // 2. Authenticate as ENTREPRENEUR
    const loginRes = await request.post('http://127.0.0.1:8000/auth/login', {
      data: {
        email: 'entrepreneur@arthlens.org',
        password: 'Password123!',
      },
    });
    expect(loginRes.status()).toBe(200);
    const loginBody = await loginRes.json();
    expect(loginBody.email).toBe('entrepreneur@arthlens.org');
    expect(loginBody.roles).toContain('ENTREPRENEUR');

    const token = loginBody.access_token;
    expect(token).toBeDefined();

    // 3. Permitted access to /geo/units with authenticated token
    const authGeoRes = await request.get('http://127.0.0.1:8000/geo/units', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(authGeoRes.status()).toBe(200);

    // 4. Unauthorized 403 test: ENTREPRENEUR calling ADMIN-only /admin/users returns 403
    const forbiddenRes = await request.get('http://127.0.0.1:8000/admin/users', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(forbiddenRes.status()).toBe(403);

    // 5. Test real UI session in browser at /app
    await page.goto('/app');
    const signInBtn = page.getByTestId('navbar-sign-in-btn');
    if (await signInBtn.isVisible()) {
      await signInBtn.click();
      await page.locator('input[type="email"]').fill('entrepreneur@arthlens.org');
      await page.locator('input[type="password"]').fill('Password123!');
      await page.locator('form').getByRole('button', { name: 'Sign In with Credentials' }).click();
      await page.waitForTimeout(800);
    }

    // Check user profile pill shows authenticated user
    await expect(page.locator('text=entrepreneur@arthlens.org')).toBeVisible();
    await expect(page.locator('text=ENTREPRENEUR').first()).toBeVisible();

    // Switch account to STEWARD via UI
    await page.locator('button[aria-label="User RBAC Role and Account Session"]').click();
    const stewardQuickBtn = page.locator('button:has-text("Data Steward")');
    if (await stewardQuickBtn.isVisible()) {
      await stewardQuickBtn.click();
    } else {
      await page.locator('button:has-text("Authenticate Credentials...")').click();
      await page.locator('input[type="email"]').fill('steward@arthlens.org');
      await page.locator('input[type="password"]').fill('Password123!');
      await page.locator('button:has-text("Sign In with Credentials")').click();
    }
    await page.waitForTimeout(800);

    await expect(page.locator('text=steward@arthlens.org')).toBeVisible();
    await expect(page.locator('text=STEWARD').first()).toBeVisible();

    // Switch account to ADMIN via UI
    await page.locator('button[aria-label="User RBAC Role and Account Session"]').click();
    const adminQuickBtn = page.locator('button:has-text("Administrator")');
    if (await adminQuickBtn.isVisible()) {
      await adminQuickBtn.click();
    } else {
      await page.locator('button:has-text("Authenticate Credentials...")').click();
      await page.locator('input[type="email"]').fill('admin@arthlens.org');
      await page.locator('input[type="password"]').fill('Password123!');
      await page.locator('button:has-text("Sign In with Credentials")').click();
    }
    await page.waitForTimeout(800);

    await expect(page.locator('text=admin@arthlens.org')).toBeVisible();
    await expect(page.locator('text=ADMIN').first()).toBeVisible();
  });

  test('Capture Authoritative Browser Screenshots: Root Homepage, /app, and /app?view=graph', async ({ page }) => {
    test.setTimeout(120000);
    // 1. Root route (/) with CinematicNavbar at 1920x1080
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_cinematic_homepage_1920x1080.png'), fullPage: false });

    // 2. Dedicated /app route at 1920x1080 with Atlas Map & Workspace Navbar (Prayagraj verified boundary + real basemap)
    await page.goto('/app');
    await ensureAuthenticated(page);
    await page.locator('button:has-text("Prayagraj")').first().click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_workspace_atlas_1920x1080.png'), fullPage: false });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_workspace_atlas_prayagraj_1920x1080.png'), fullPage: false });

    // Open Provenance Drawer for population.total and capture screenshot
    const popCard = page.locator('button[aria-label*="population.total"]');
    if (await popCard.isVisible()) {
      await popCard.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_provenance_drawer_population_stale_1920x1080.png'), fullPage: false });
      await page.locator('button[aria-label="Close provenance drawer"]').click();
      await page.waitForTimeout(300);
    }

    // 3. Dedicated /app route at 1920x1080 with Varanasi selected (unblocked basemap + compact status pill)
    await page.locator('button:has-text("Varanasi")').first().click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_workspace_varanasi_source_gated_1920x1080.png'), fullPage: false });

    // 4. Evidence Graph View at 1920x1080 (Authenticated DAG)
    const graphTab = page.locator('button[aria-label="Evidence Graph Workspace"]');
    if (await graphTab.isVisible()) {
      await graphTab.click();
    } else {
      await page.goto('/app?view=graph');
    }
    await expect(page.locator('text=Cytoscape Evidence Graph')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_workspace_graph_view_1920x1080.png'), fullPage: false });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_evidence_graph_population_dag_1920x1080.png'), fullPage: false });

    // 4b. Scenario Laboratory View (/app?view=scenarios)
    const scenarioTab = page.locator('button[aria-label="Scenario Lab Workspace"]');
    if (await scenarioTab.isVisible()) {
      await scenarioTab.click();
    } else {
      await page.goto('/app?view=scenarios');
    }
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '14_scenario_laboratory_1920x1080.png'), fullPage: false });

    // 4c. Policy Rules View (/app?view=policy)
    const policyTab = page.locator('button[aria-label="Policy Rules Workspace"]');
    if (await policyTab.isVisible()) {
      await policyTab.click();
    } else {
      await page.goto('/app?view=policy');
    }
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '15_policy_workspace_1920x1080.png'), fullPage: false });

    // 4d. Agent Console View (/app?view=agent)
    const agentTab = page.locator('button[aria-label="Agent Console Workspace"]');
    if (await agentTab.isVisible()) {
      await agentTab.click();
    } else {
      await page.goto('/app?view=agent');
    }
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '16_agent_console_1920x1080.png'), fullPage: false });

    // 4e. Decision Dossier Modal
    const dossierBtn = page.locator('button:has-text("Dossier")');
    if (await dossierBtn.isVisible()) {
      await dossierBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '17_decision_dossier_modal_1920x1080.png'), fullPage: false });
      const closeBtn = page.locator('button[aria-label="Close dossier modal"]').or(page.locator('button:has-text("Print")').locator('..').locator('button').last());
      await closeBtn.click();
      await page.waitForTimeout(300);
    }

    // 5. Laptop Viewport (1440x900)
    await page.setViewportSize({ width: 1440, height: 900 });
    const atlasTab = page.locator('button[aria-label="Atlas Map Workspace"]');
    if (await atlasTab.isVisible()) {
      await atlasTab.click();
    } else {
      await page.goto('/app');
    }
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_desktop_laptop_1440x900.png'), fullPage: false });

    // 6. Mobile Viewport (390x844)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/');
    await page.waitForTimeout(800);
    // Invariant: Zero horizontal navigation clipping or page overflow
    const homepageOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(homepageOverflow).toBe(false);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_mobile_iphone_390x844.png'), fullPage: false });

    // 7. Mobile Workspace Viewport (390x844)
    await page.goto('/app');
    await page.waitForTimeout(1000);
    const workspaceOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(workspaceOverflow).toBe(false);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_mobile_workspace_iphone_390x844.png'), fullPage: false });
  });

  test('Journey 7: Responsive Multi-Viewport Matrix and Zero-Clipping Invariants (390x844, 768x1024, 1440x900, 1920x1080)', async ({ page }) => {
    const viewports = [
      { name: 'iphone_390x844', width: 390, height: 844 },
      { name: 'tablet_768x1024', width: 768, height: 1024 },
      { name: 'laptop_1440x900', width: 1440, height: 900 },
      { name: 'desktop_1920x1080', width: 1920, height: 1080 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/app');
      await page.waitForTimeout(800);

      // Check document overflow
      const isOverflowing = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      expect(isOverflowing).toBe(false);

      // Check brand header link is within viewport
      const brandWithin = await page.evaluate(() => {
        const brand = document.querySelector('header a');
        if (!brand) return false;
        const rect = brand.getBoundingClientRect();
        return rect.left >= 0 && rect.right <= window.innerWidth;
      });
      expect(brandWithin).toBe(true);

      // Check right controls (session button or sign-in button) are within viewport
      const controlsWithin = await page.evaluate(() => {
        const rightContainer = document.querySelector('header > div > div:last-child');
        if (!rightContainer) return false;
        const rect = rightContainer.getBoundingClientRect();
        return rect.left >= 0 && rect.right <= window.innerWidth;
      });
      expect(controlsWithin).toBe(true);
    }
  });

  test('Journey 8: Complete 9-Scene Narrative Sequence & Workspace Launch Hand-off', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');

    // Scene 01: Prologue
    await expect(page.locator('#scene-01-prologue')).toBeVisible();
    await expect(page.locator('text=GEODETIC DATUM: WGS-84')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('EPISTEMIC');

    // Scene 02: Multi-Scale Territory
    const scene2 = page.locator('#scene-02-landscape');
    await scene2.scrollIntoViewIfNeeded();
    await expect(scene2.locator('text=Scene 02 // Multi-Scale Territory')).toBeVisible();

    await scene2.getByRole('button', { name: 'NATION' }).click();
    await expect(scene2.getByRole('heading', { name: 'The Sovereign Union' })).toBeVisible();

    // Scene 03: The Problem
    const scene3 = page.locator('#scene-03-problem');
    await scene3.scrollIntoViewIfNeeded();
    await expect(scene3.locator('text=The Conventional Fragility')).toBeVisible();

    // Scene 04: The Atlas
    const scene4 = page.locator('#scene-04-atlas');
    await scene4.scrollIntoViewIfNeeded();
    await expect(scene4.locator('text=Dynamic Geodetic HUD')).toBeVisible();

    // Scene 05: Monotonicity Ladder
    const scene5 = page.locator('#scene-05-evidence');
    await scene5.scrollIntoViewIfNeeded();
    await expect(scene5.locator('text=The Epistemic Monotonicity Ladder')).toBeVisible();
    await expect(scene5.getByText('FLOOR 4', { exact: true })).toBeVisible();
    await expect(scene5.getByText('FLOOR 1', { exact: true })).toBeVisible();

    // Scene 06: Simulation Engine (Loop B)
    const scene6 = page.locator('#scene-06-simulation');
    await scene6.scrollIntoViewIfNeeded();
    await expect(scene6.locator('text=Loop B: Economic Simulation Engine')).toBeVisible();

    // Scene 07: Policy Intelligence (Loop C)
    const scene7 = page.locator('#scene-07-policy');
    await scene7.scrollIntoViewIfNeeded();
    await expect(scene7.locator('text=Loop C: Policy & Scheme Intelligence')).toBeVisible();

    // Scene 08: Agentic Engine
    const scene8 = page.locator('#scene-08-agentic');
    await scene8.scrollIntoViewIfNeeded();
    await expect(scene8.locator('text=The Agentic Analytical Engine')).toBeVisible();

    // Scene 09: Enter ArthLens -> Launches /app
    const scene9 = page.locator('#scene-09-enter');
    await scene9.scrollIntoViewIfNeeded();
    await expect(scene9.locator('text=Verifiable Spatial Economics for India.')).toBeVisible();

    const launchAtlasBtn = scene9.getByRole('button', { name: 'LAUNCH GEOSPATIAL ATLAS' });
    await expect(launchAtlasBtn).toBeVisible();
    await launchAtlasBtn.click();

    // Verifies hand-off smoothly transitions into /app route
    await page.waitForURL('**/app');
    expect(page.url()).toContain('/app');
    await expect(page.locator('#atlas-workspace')).toBeVisible();
  });

  test('Journey 10: GSAP ScrollTrigger Choreography & Fail-Closed Typed API Semantics', async ({ page, request }) => {
    // 1. Visit root route and verify GSAP ScrollTriggers are genuinely registered
    await page.goto('/');
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForTimeout(1000);

    const triggerCount = await page.evaluate(() => {
      const st = (window as any).ScrollTrigger;
      if (st && typeof st.getAll === 'function') {
        return st.getAll().length;
      }
      return 0;
    });
    // Non-tautological verification: at least 1 ScrollTrigger must be registered
    expect(triggerCount).toBeGreaterThan(0);

    // 2. Verify Horizontal Pinned Pipeline (.pin-spacer and translation)
    const pipelineSection = page.locator('#epistemic-pipeline-section');
    await pipelineSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(600);

    // Verify .pin-spacer element created by ScrollTrigger pinning
    const pinSpacer = page.locator('.pin-spacer');
    await expect(pinSpacer.first()).toBeVisible();

    // Measure horizontal track position before scrolling
    const track = page.locator('.epistemic-track');
    await expect(track).toBeVisible();
    const initialTrackBox = await track.boundingBox();
    expect(initialTrackBox).not.toBeNull();

    // Scroll further down through the pinned scrub sequence
    await page.evaluate(() => {
      const el = document.getElementById('epistemic-pipeline-section');
      if (el) {
        const top = el.getBoundingClientRect().top + window.scrollY;
        window.scrollTo(0, top + 600);
      }
    });
    await page.waitForTimeout(600);

    // Measure track position after scroll: horizontal x translation must have occurred
    const scrolledTrackBox = await track.boundingBox();
    expect(scrolledTrackBox).not.toBeNull();
    if (initialTrackBox && scrolledTrackBox) {
      // The track translates horizontally leftward (smaller x) as scroll proceeds
      expect(scrolledTrackBox.x).toBeLessThan(initialTrackBox.x);
    }

    // 3. Verify Fail-Closed Typed Backend API Semantics
    // Unauthorized request strictly returns 401
    const unauthUnits = await request.get('http://127.0.0.1:8000/geo/units');
    expect(unauthUnits.status()).toBe(401);

    // Authenticate with valid session
    const loginRes = await request.post('http://127.0.0.1:8000/auth/login', {
      data: {
        email: 'entrepreneur@arthlens.org',
        password: 'Password123!',
      },
    });
    expect(loginRes.status()).toBe(200);
    const token = (await loginRes.json()).access_token;
    const authHeaders = { Authorization: `Bearer ${token}` };

    // Non-existent unit returns 404 when authenticated
    const nonExistent = await request.get('http://127.0.0.1:8000/geo/in:district:999999', { headers: authHeaders });
    expect(nonExistent.status()).toBe(404);

    // Non-existent ledger quantity returns 404 when authenticated
    const nonExistentQuantity = await request.get('http://127.0.0.1:8000/ledger/non-existent-uuid-999', { headers: authHeaders });
    expect(nonExistentQuantity.status()).toBe(404);

    // 4. Verify Genuine PMTiles Vector Endpoint & Range Support
    const pmtilesRes = await request.get('http://127.0.0.1:8000/geo/pilot-pmtiles', { headers: authHeaders });
    expect(pmtilesRes.status()).toBe(200);
    expect(pmtilesRes.headers()['content-type']).toContain('application/vnd.pmtiles');
    const pmtilesBody = await pmtilesRes.body();
    expect(pmtilesBody.length).toBeGreaterThan(1000);
    // Spec check: PMTiles v3 magic header starts with "PMTiles" (0x50 0x4D 0x54 0x69 0x6C 0x65 0x73)
    expect(pmtilesBody.subarray(0, 7).toString('utf-8')).toBe('PMTiles');

    // Range request check (HTTP 206 Partial Content)
    const rangeRes = await request.get('http://127.0.0.1:8000/geo/pilot-pmtiles', {
      headers: { ...authHeaders, Range: 'bytes=0-127' },
    });
    expect(rangeRes.status()).toBe(206);
    expect(rangeRes.headers()['content-range']).toBeDefined();
    expect((await rangeRes.body()).length).toBe(128);
  });

});
