import { APIRequestContext, APIResponse, expect, Page } from '@playwright/test';

export const apiBaseURL = process.env.PLAYWRIGHT_API_URL || 'http://127.0.0.1:8000';
const password = 'E2E-Password-2026!';

export async function expectJsonStatus(response: APIResponse, expected: number) {
  const text = await response.text();
  expect(response.status(), text).toBe(expected);
  return text ? JSON.parse(text) : {};
}

function resolveOtpCode(challenge: Record<string, unknown>, flow: string): string {
  const otp = String(challenge.dev_otp_preview ?? process.env.PLAYWRIGHT_OTP_CODE ?? '');
  if (!/^\d{6}$/.test(otp)) {
    throw new Error(`${flow} requires a six digit dev_otp_preview or PLAYWRIGHT_OTP_CODE.`);
  }
  return otp;
}

export async function registerEmailAccount(
  request: APIRequestContext,
  email: string,
  fullName: string,
  accountPassword: string,
) {
  const started = await request.post(`${apiBaseURL}/auth/register/initiate`, {
    data: { full_name: fullName, email, password: accountPassword },
  });
  const challenge = await expectJsonStatus(started, 202);
  expect(challenge.otp_required).toBe(true);
  expect(challenge.purpose).toBe('REGISTER_VERIFY');
  const verified = await request.post(`${apiBaseURL}/auth/register/verify-otp`, {
    data: {
      challenge_id: challenge.challenge_id,
      email: challenge.email ?? email,
      otp_code: resolveOtpCode(challenge, 'Email registration'),
    },
  });
  const auth = await expectJsonStatus(verified, 200);
  expect(auth.access_token).toBeTruthy();
  return auth;
}

export async function loginEmailAccount(
  request: APIRequestContext,
  email: string,
  accountPassword: string,
) {
  const started = await request.post(`${apiBaseURL}/auth/login/initiate`, {
    data: { email, password: accountPassword },
  });
  const challenge = await expectJsonStatus(started, 202);
  expect(challenge.otp_required).toBe(true);
  expect(challenge.purpose).toBe('LOGIN_2FA');
  const verified = await request.post(`${apiBaseURL}/auth/login/verify-otp`, {
    data: {
      challenge_id: challenge.challenge_id,
      email: challenge.email ?? email,
      otp_code: resolveOtpCode(challenge, 'Email login'),
    },
  });
  const auth = await expectJsonStatus(verified, 200);
  expect(auth.access_token).toBeTruthy();
  return auth;
}

export async function completeBrowserEmailOtp(page: Page) {
  const codeGroup = page.getByRole('group', { name: 'Six digit email verification code' });
  await expect(codeGroup).toBeVisible();

  let otp = process.env.PLAYWRIGHT_OTP_CODE ?? '';
  const preview = page.getByText(/Local development code:/);
  if (await preview.count()) {
    const previewText = await preview.innerText();
    otp = previewText.match(/\b\d{6}\b/)?.[0] ?? otp;
  }
  if (!/^\d{6}$/.test(otp)) {
    throw new Error('Email OTP UI flow requires the visible dev_otp_preview or PLAYWRIGHT_OTP_CODE.');
  }

  for (const [index, digit] of Array.from(otp).entries()) {
    await page.getByRole('textbox', { name: `Code digit ${index + 1}` }).fill(digit);
  }
  const verifyButton = page.getByRole('button', { name: /Verify (2FA & Sign In|OTP & Complete Registration)/ });
  await expect(verifyButton).toBeEnabled();
  const destination = page.waitForURL('**/workspaces', { timeout: 30000 });
  await verifyButton.click();
  await destination;
}

export async function completeLocalGoogleChooser(
  page: Page,
  mode: 'login' | 'register',
  email: string,
  fullName: string,
) {
  const buttonName = mode === 'register' ? /Register with Google/ : /Continue with Google/;
  const launch = page.getByRole('button', { name: buttonName });
  await expect(launch).toBeVisible();
  await launch.click();

  const chooser = page.getByRole('dialog', { name: 'Choose a Google account' });
  await expect(chooser).toBeVisible();
  await chooser.getByLabel('Name').fill(fullName);
  await chooser.getByLabel('Google account email').fill(email);
  const destination = page.waitForURL('**/workspaces', { timeout: 30000 });
  await chooser.getByRole('button', { name: 'Continue securely' }).click();
  await destination;
}

export async function createWorkspaceSession(request: APIRequestContext, label: string) {
  const nonce = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const email = `journey-${label}-${nonce}@arthlens.local`;
  const auth = await registerEmailAccount(request, email, `ArthLens ${label}`, password);
  const token = auth.access_token as string;
  expect(token).toBeTruthy();
  const headers = { Authorization: `Bearer ${token}` };
  const created = await request.post(`${apiBaseURL}/businesses`, {
    headers,
    data: { name: `E2E ${label} ${nonce}`, industry: 'Test workspace' },
  });
  const workspace = await expectJsonStatus(created, 201);
  return { email, userId: auth.id as string, token, headers, businessId: workspace.id as string };
}

export async function archiveWorkspace(request: APIRequestContext, token: string, businessId: string) {
  const response = await request.post(`${apiBaseURL}/businesses/${businessId}/archive`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { is_archived: true },
  });
  await expectJsonStatus(response, 200);
}

export function isoDate(offsetDays = 0): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

export { password };
