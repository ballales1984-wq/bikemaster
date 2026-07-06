import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4174',
    serviceWorkers: 'block',
    launchOptions: { args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'] },
  },
  webServer: {
    command: 'npx vite preview --outDir dist_build --host 127.0.0.1 --port 4174',
    url: 'http://127.0.0.1:4174',
    reuseExistingServer: true,
    timeout: 60000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
