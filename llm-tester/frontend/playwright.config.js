const { defineConfig } = require('@playwright/test')

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:3010',
    headless: true,
    launchOptions: { executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe' },
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: '"C:\\Users\\zoode\\AppData\\Local\\Programs\\Python\\Python311\\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8020',
      cwd: '../backend',
      env: { DATABASE_URL: 'sqlite+aiosqlite:///./e2e_test.db' },
      url: 'http://127.0.0.1:8020/health',
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: 'npm.cmd run build && npm.cmd run preview -- --host 127.0.0.1 --port 3010',
      cwd: '.',
      env: { VITE_API_PROXY_TARGET: 'http://127.0.0.1:8020' },
      url: 'http://127.0.0.1:3010',
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
})
