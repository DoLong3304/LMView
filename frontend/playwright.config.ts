import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 1,
  workers: 1,
  reporter: [['html', { outputFolder: 'playwright-report' }], ['list']],

  use: {
    // Production URL (Nginx on port 8080)
    baseURL: process.env.E2E_BASE_URL || 'https://127.0.0.1',
    ignoreHTTPSErrors: true,
    // Increase timeouts for slow chart rendering
    timeout: 30_000,
    navigationTimeout: 15_000,
    // Capture screenshot + trace on failure
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
