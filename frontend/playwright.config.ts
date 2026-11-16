import path from 'path';
import { defineConfig, devices } from '@playwright/test';

if (!process.env.NO_PROXY) {
  process.env.NO_PROXY = 'localhost,127.0.0.1';
  process.env.no_proxy = 'localhost,127.0.0.1';
} else if (!process.env.NO_PROXY.includes('localhost')) {
  process.env.NO_PROXY += ',localhost,127.0.0.1';
  process.env.no_proxy += ',localhost,127.0.0.1';
}

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const webPort = new URL(baseURL).port || '3000';

export default defineConfig({
  testDir: path.join(__dirname, 'e2e'),
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
  ...(process.env.PLAYWRIGHT_EXTERNAL_SERVER ? {} : {
    webServer: {
      command: `npm run start -- --hostname 127.0.0.1 --port ${webPort}`,
      url: baseURL,
      reuseExistingServer: true,
      timeout: 30000,
    },
  }),
});
