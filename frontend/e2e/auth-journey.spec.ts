import { request as playwrightRequest, test, expect } from '@playwright/test';
import {
  apiBaseURL,
  completeBrowserEmailOtp,
  completeLocalGoogleChooser,
  expectJsonStatus,
  password as apiPassword,
  registerEmailAccount,
} from './helpers';

const webBaseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const initialPassword = 'Password123!';
const newPassword = 'NewPassword123!';

async function fillLoginForm(page: import('@playwright/test').Page, email: string, password: string) {
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: /Continue with Password/ }).click();
  await completeBrowserEmailOtp(page);
}

test.describe('Email OTP and Google authentication journeys', () => {
  test('Email registration, OTP login, and password recovery lifecycle', async ({ page, context }) => {
    test.setTimeout(120000);
    const nonce = Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
    const email = `journey.${nonce}@arthlens.local`;

    await page.goto(`${webBaseURL}/register`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
    await page.getByLabel('Full name').fill('Priya Sharma');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', { exact: true }).fill(initialPassword);
    await page.getByLabel('Confirm password').fill(initialPassword);
    await page.getByRole('button', { name: /Register with Email/ }).click();
    await completeBrowserEmailOtp(page);

    const cookiesAfterRegistration = await context.cookies([apiBaseURL, webBaseURL]);
    expect(cookiesAfterRegistration.some((cookie) => cookie.name === 'arthlens_access_token')).toBe(true);

    await page.goto(`${webBaseURL}/login`, { waitUntil: 'domcontentloaded' });
    await fillLoginForm(page, email, initialPassword);
    await expect(page).toHaveURL(/\/workspaces$/);

    await page.goto(`${webBaseURL}/forgot-password`, { waitUntil: 'domcontentloaded' });
    await page.getByLabel('Email Address').fill(email);
    await page.getByRole('button', { name: 'Send Recovery Instructions' }).click();
    await expect(page.getByRole('heading', { name: 'Instructions Dispatched' })).toBeVisible();
    const recoveryLink = page.getByRole('link', { name: /Proceed with reset now/ });
    await expect(recoveryLink).toBeVisible();
    await recoveryLink.click();
    await page.waitForURL('**/reset-password**');

    await page.getByPlaceholder('At least 8 characters').fill(newPassword);
    await page.getByPlaceholder('Re-enter new password').fill(newPassword);
    await page.getByRole('button', { name: 'Set New Password' }).click();
    await expect(page.getByRole('heading', { name: 'Password Successfully Updated' })).toBeVisible();
    await page.getByRole('link', { name: /Proceed to Sign In/ }).click();
    await page.waitForURL('**/login');
    await fillLoginForm(page, email, newPassword);
  });

  test('Google Sign-In chooser completes login from /login', async ({ page }) => {
    const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const email = `google-login-seed-${suffix}@arthlens.local`;
    const api = await playwrightRequest.newContext({ baseURL: apiBaseURL });
    try {
      await registerEmailAccount(api, email, 'Google Login Seed', apiPassword);
    } finally {
      await api.dispose();
    }

    await page.goto(`${webBaseURL}/login`, { waitUntil: 'domcontentloaded' });
    await completeLocalGoogleChooser(page, 'login', email, 'Google Login Seed');
    await expect(page).toHaveURL(/\/workspaces$/);
  });

  test('Google Sign-In chooser completes registration from /register', async ({ page }) => {
    const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    await page.goto(`${webBaseURL}/register`, { waitUntil: 'domcontentloaded' });
    await completeLocalGoogleChooser(
      page,
      'register',
      `google-register-${suffix}@arthlens.local`,
      'Google Register Test',
    );
    await expect(page).toHaveURL(/\/workspaces$/);
  });

  test('IDOR protection: user cannot read or update another user workspace', async () => {
    const userARequest = await playwrightRequest.newContext({ baseURL: apiBaseURL });
    const userBRequest = await playwrightRequest.newContext({ baseURL: apiBaseURL });
    let tokenA: string | undefined;
    let businessId: string | undefined;
    try {
      const userA = await registerEmailAccount(
        userARequest,
        `usera.${Date.now()}@arthlens.local`,
        'User A',
        initialPassword,
      );
      tokenA = userA.access_token;
      const userB = await registerEmailAccount(
        userBRequest,
        `userb.${Date.now()}@arthlens.local`,
        'User B',
        initialPassword,
      );

      const createWorkspace = await userARequest.post('/businesses', {
        headers: { Authorization: `Bearer ${tokenA}` },
        data: { name: 'User A Bakery', industry: 'Food & Beverage' },
      });
      const workspace = await expectJsonStatus(createWorkspace, 201);
      businessId = workspace.id;
      const headersB = { Authorization: `Bearer ${userB.access_token}` };

      const read = await userBRequest.get(`/businesses/${businessId}`, { headers: headersB });
      expect(read.status()).toBe(403);
      const update = await userBRequest.put(`/businesses/${businessId}`, {
        headers: headersB,
        data: { name: 'Hacked Bakery' },
      });
      expect(update.status()).toBe(403);
    } finally {
      if (businessId && tokenA) {
        await userARequest.post(`/businesses/${businessId}/archive`, {
          headers: { Authorization: `Bearer ${tokenA}` },
          data: { is_archived: true },
        });
      }
      await Promise.all([userARequest.dispose(), userBRequest.dispose()]);
    }
  });

  test('Workspace roles remain tenant scoped and archived workspaces reject writes', async () => {
    const ownerRequest = await playwrightRequest.newContext({ baseURL: apiBaseURL });
    const collaboratorRequest = await playwrightRequest.newContext({ baseURL: apiBaseURL });
    let ownerHeaders: { Authorization: string } | undefined;
    let workspaceId: string | undefined;
    try {
      const ownerEmail = `owner.${Date.now()}@arthlens.local`;
      const owner = await registerEmailAccount(ownerRequest, ownerEmail, 'Workspace Owner', initialPassword);
      ownerHeaders = { Authorization: `Bearer ${owner.access_token}` };
      const collaboratorEmail = `collaborator.${Date.now()}@arthlens.local`;
      const collaborator = await registerEmailAccount(
        collaboratorRequest,
        collaboratorEmail,
        'Workspace Collaborator',
        initialPassword,
      );

      const create = await ownerRequest.post('/businesses', {
        headers: ownerHeaders,
        data: { name: `Governance ${Date.now()}`, industry: 'Testing' },
      });
      const workspace = await expectJsonStatus(create, 201);
      workspaceId = workspace.id;
      const added = await ownerRequest.post(`/businesses/${workspaceId}/members`, {
        headers: ownerHeaders,
        data: { user_id: collaborator.id, role: 'ANALYST' },
      });
      await expectJsonStatus(added, 201);
      const updated = await ownerRequest.patch(`/businesses/${workspaceId}/members/${collaborator.id}`, {
        headers: ownerHeaders,
        data: { role: 'ADMIN' },
      });
      expect((await expectJsonStatus(updated, 200)).role).toBe('ADMIN');

      const archive = await ownerRequest.post(`/businesses/${workspaceId}/archive`, {
        headers: ownerHeaders,
        data: { is_archived: true },
      });
      await expectJsonStatus(archive, 200);
      const read = await ownerRequest.get(`/businesses/${workspaceId}`, { headers: ownerHeaders });
      expect(read.status()).toBe(200);
      const blockedWrite = await ownerRequest.put(`/businesses/${workspaceId}`, {
        headers: ownerHeaders,
        data: { name: 'Should stay archived' },
      });
      expect(blockedWrite.status()).toBe(409);
      await ownerRequest.post(`/businesses/${workspaceId}/archive`, {
        headers: ownerHeaders,
        data: { is_archived: false },
      });
    } finally {
      if (workspaceId && ownerHeaders) {
        await ownerRequest.post(`/businesses/${workspaceId}/archive`, {
          headers: ownerHeaders,
          data: { is_archived: true },
        });
      }
      await Promise.all([ownerRequest.dispose(), collaboratorRequest.dispose()]);
    }
  });
});
