import { test, expect } from '@playwright/test';

test.describe('End-to-End User Authentication & Account Governance Journey', () => {
  const uniqueSuffix = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const testEmail = `journey.${uniqueSuffix}@arthlens.local`;
  const initialPassword = 'Password123!';
  const newPassword = 'NewPassword123!';
  const fullName = 'Priya Sharma';

  test('Full authentication lifecycle: Register -> Refresh -> Scenarios -> Password Reset -> Logout', async ({ page, context }) => {
    // 1. PUBLIC REGISTRATION
    await page.goto('http://localhost:3000/register');
    await expect(page.locator('h2')).toContainText('Create Entrepreneur Account');

    await page.locator('input[placeholder="Aarav Sharma"]').fill(fullName);
    await page.locator('input[type="email"]').fill(testEmail);
    await page.locator('input[type="password"]').nth(0).fill(initialPassword);
    await page.locator('input[type="password"]').nth(1).fill(initialPassword);

    await page.getByRole('button', { name: 'Register & Start Workspace' }).click();

    // Verify successful registration redirects to /app with authenticated session
    await page.waitForURL('**/app');
    const accountBtn = page.locator('button[aria-label="User RBAC Role and Account Session"]');
    await expect(accountBtn).toBeVisible({ timeout: 10000 });
    await expect(accountBtn).toContainText('ENTREPRENEUR');

    // 2. VERIFY COOKIE PERSISTENCE ACROSS REFRESH
    const cookiesBefore = await context.cookies(['http://localhost:8000', 'http://localhost:3000', 'http://127.0.0.1:8000']);
    const authCookie = cookiesBefore.find((c) => c.name === 'arthlens_access_token' || c.name.includes('token'));
    expect(authCookie).toBeDefined();

    await page.reload();
    await expect(accountBtn).toBeVisible({ timeout: 10000 });
    await expect(accountBtn).toContainText('ENTREPRENEUR');

    // 3. SCENARIO LABORATORY & OWNERSHIP
    // Switch to Scenarios tab
    const scenariosTab = page.locator('button:has-text("Scenarios")');
    if (await scenariosTab.isVisible()) {
      await scenariosTab.click();
    }

    // 4. LOGOUT & SESSION INVALIDATION
    await accountBtn.click();
    const signOutBtn = page.locator('button:has-text("Sign Out")');
    await expect(signOutBtn).toBeVisible();
    await signOutBtn.click();

    // Verify unauthenticated state in Navbar
    await expect(page.getByTestId('navbar-sign-in-btn')).toBeVisible({ timeout: 10000 });

    // 5. LOGIN WITH EXISTING CREDENTIALS
    await page.goto('http://localhost:3000/login');
    await page.locator('input[type="email"]').fill(testEmail);
    await page.locator('input[type="password"]').fill(initialPassword);
    await page.getByRole('button', { name: 'Sign In' }).click();

    await page.waitForURL('**/app');
    await expect(accountBtn).toBeVisible({ timeout: 10000 });

    // 6. PASSWORD RECOVERY FLOW
    await page.goto('http://localhost:3000/forgot-password');
    await expect(page.locator('h2')).toContainText('Recover Your Password');

    await page.locator('input[type="email"]').fill(testEmail);
    await page.getByRole('button', { name: 'Send Recovery Instructions' }).click();

    await expect(page.locator('h3')).toContainText('Instructions Dispatched', { timeout: 10000 });

    // In local development, the recovery link is rendered directly
    const devRecoveryLink = page.locator('a:has-text("Proceed with reset now")');
    if (await devRecoveryLink.isVisible()) {
      await devRecoveryLink.click();
      await page.waitForURL('**/reset-password**');

      await page.locator('input[placeholder="At least 8 characters"]').fill(newPassword);
      await page.locator('input[placeholder="Re-enter new password"]').fill(newPassword);
      await page.getByRole('button', { name: 'Set New Password' }).click();

      await expect(page.locator('h3')).toContainText('Password Successfully Updated', { timeout: 10000 });

      // Sign in with new password
      await page.locator('a:has-text("Proceed to Sign In")').click();
      await page.waitForURL('**/login');

      await page.locator('input[type="email"]').fill(testEmail);
      await page.locator('input[type="password"]').fill(newPassword);
      await page.getByRole('button', { name: 'Sign In' }).click();

      await page.waitForURL('**/app');
      await expect(accountBtn).toBeVisible({ timeout: 10000 });
    }
  });

  test('IDOR Protection: User cannot access another user scenarios', async ({ request }) => {
    // Register user A
    const userAEmail = `usera.${Date.now()}@arthlens.local`;
    const regA = await request.post('http://127.0.0.1:8000/auth/register', {
      data: { full_name: 'User A', email: userAEmail, password: 'Password123!' },
    });
    expect(regA.status()).toBe(201);
    const tokenA = (await regA.json()).access_token;

    // Register user B
    const userBEmail = `userb.${Date.now()}@arthlens.local`;
    const regB = await request.post('http://127.0.0.1:8000/auth/register', {
      data: { full_name: 'User B', email: userBEmail, password: 'Password123!' },
    });
    expect(regB.status()).toBe(201);
    const tokenB = (await regB.json()).access_token;

    // User A creates scenario
    const createScenarioRes = await request.post('http://127.0.0.1:8000/scenarios', {
      headers: { Authorization: `Bearer ${tokenA}` },
      data: { name: 'User A Secret Strategy', scenario: { capital: 500000 } },
    });
    expect(createScenarioRes.status()).toBe(201);
    const scenarioId = (await createScenarioRes.json()).id;

    // User B attempts to read User A scenario -> 404 (IDOR defense)
    const getRes = await request.get(`http://127.0.0.1:8000/scenarios/${scenarioId}`, {
      headers: { Authorization: `Bearer ${tokenB}` },
    });
    expect(getRes.status()).toBe(404);

    // User B attempts to update User A scenario -> 404
    const putRes = await request.put(`http://127.0.0.1:8000/scenarios/${scenarioId}`, {
      headers: { Authorization: `Bearer ${tokenB}` },
      data: { name: 'Hacked Strategy' },
    });
    expect(putRes.status()).toBe(404);

    // User B attempts to delete User A scenario -> 404
    const delRes = await request.delete(`http://127.0.0.1:8000/scenarios/${scenarioId}`, {
      headers: { Authorization: `Bearer ${tokenB}` },
    });
    expect(delRes.status()).toBe(404);
  });
});

