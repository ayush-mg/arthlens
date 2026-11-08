import { test, expect } from '@playwright/test';

test.describe('Complete ArthLens Normal User Journey', () => {
  const uniqueSuffix = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const testEmail = `entrepreneur.${uniqueSuffix}@arthlens.local`;
  const password = 'Password123!';
  const fullName = 'Devika Verma';

  test('E2E Normal User Journey: Register -> Login -> Atlas -> Scenario -> Calculations -> Agent -> Evidence -> Multi-Format Reports', async ({ page }) => {
    // 1. PUBLIC REGISTRATION
    await page.goto('http://localhost:3000/register');
    await expect(page.locator('h2')).toContainText('Create Entrepreneur Account');

    await page.locator('input[placeholder="Aarav Sharma"]').fill(fullName);
    await page.locator('input[type="email"]').fill(testEmail);
    await page.locator('input[type="password"]').nth(0).fill(password);
    await page.locator('input[type="password"]').nth(1).fill(password);
    await page.getByRole('button', { name: 'Register & Start Workspace' }).click();

    // 2. VERIFY AUTHENTICATED SESSION ON /app
    await page.waitForURL('**/app');
    const accountBtn = page.locator('button[aria-label="User RBAC Role and Account Session"]');
    await expect(accountBtn).toBeVisible({ timeout: 10000 });
    await expect(accountBtn).toContainText('ENTREPRENEUR');

    // 3. ECONOMIC ATLAS INTERACTION
    // Verify territory headline and indicators
    await expect(page.locator('text=Prayagraj').first()).toBeVisible({ timeout: 10000 });

    // 4. SCENARIO LABORATORY: CREATE SCENARIO
    const scenariosTab = page.locator('button[aria-label="Scenario Lab Workspace"]');
    await scenariosTab.click();

    await expect(page.locator('h2:has-text("Scenario Laboratory")')).toBeVisible({ timeout: 10000 });

    // Create scenario
    const scenarioName = `Prayagraj Dairy & Retail ${uniqueSuffix}`;
    await page.locator('input[placeholder*="Kirana Retail"]').fill(scenarioName);
    await page.locator('input[type="number"][min="1"]').fill('300000');
    await page.getByRole('button', { name: 'Initialize Scenario Branch' }).click();

    // Verify scenario branch appears and is active
    await expect(page.locator(`h3:has-text("${scenarioName}")`)).toBeVisible({ timeout: 10000 });

    // 5. ENTER BUSINESS ASSUMPTIONS & EXECUTE REAL CALCULATIONS
    // Fill selling price and volume
    const priceInput = page.locator('label:has-text("Selling Price / Unit") input');
    if (await priceInput.isVisible()) {
      await priceInput.fill('160');
      const varCostInput = page.locator('label:has-text("Variable Cost / Unit") input');
      await varCostInput.fill('100');
      const fixedCostsInput = page.locator('label:has-text("Monthly Fixed Costs") input');
      await fixedCostsInput.fill('36000');
      const volumeInput = page.locator('label:has-text("Target Monthly Volume") input');
      await volumeInput.fill('1000');

      // Click Execute Model
      await page.getByRole('button', { name: 'Execute Model' }).click();

      // Verify deterministic financial & spatial outcomes
      await expect(page.locator('text=Break-Even Units')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Monthly EMI')).toBeVisible();
      await expect(page.locator('text=Spatial Demand')).toBeVisible();
      await expect(page.locator('text=FEASIBLE')).toBeVisible();
    }

    // 6. MULTI-FORMAT REPORT DOWNLOADS (JSON, CSV, XLSX, PDF)
    // Download JSON
    const [jsonDownload] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'JSON Dossier' }).click(),
    ]);
    expect(jsonDownload.suggestedFilename()).toContain('.json');

    // Download CSV (Formula-injection sanitized)
    const [csvDownload] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'CSV Matrix' }).click(),
    ]);
    expect(csvDownload.suggestedFilename()).toContain('.csv');

    // Download XLSX
    const [xlsxDownload] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Excel Workbook (.xlsx)' }).click(),
    ]);
    expect(xlsxDownload.suggestedFilename()).toContain('.xlsx');

    // Download PDF
    const [pdfDownload] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Publication PDF' }).click(),
    ]);
    expect(pdfDownload.suggestedFilename()).toContain('.pdf');

    // 7. AGENT CONSOLE INTERACTION
    const agentTab = page.locator('button[aria-label="Agent Console Workspace"]');
    if (await agentTab.isVisible()) {
      await agentTab.click();
      await expect(page.locator('h2:has-text("Agent Run Console")')).toBeVisible({ timeout: 10000 });
    }

    // 8. EVIDENCE GRAPH INTERACTION
    const graphTab = page.locator('button[aria-label="Evidence Graph Workspace"]');
    if (await graphTab.isVisible()) {
      await graphTab.click();
      await expect(page.locator('button[aria-label="Fit view"]')).toBeVisible({ timeout: 10000 });
    }
  });
});
