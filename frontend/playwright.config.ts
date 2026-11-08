import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';

export default defineConfig({
  testDir: './e2e',
  testMatch: /.*\.spec\.ts$/,
  testIgnore: ['**/test/**', '**/*.test.ts', '**/*.test.tsx'],
  timeout: 30000,
  fullyParallel: false,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        baseURL,
      },
    },
  ],
});
