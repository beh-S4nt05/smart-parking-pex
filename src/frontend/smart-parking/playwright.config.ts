import { defineConfig } from "@playwright/test";

const databasePath = process.env.UI_DATABASE_PATH || "/tmp/smartparking-ui-tests.db";
const python = process.env.UI_PYTHON || "python";
const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
const backendEnv = {
  ...process.env,
  ENVIRONMENT: "test",
  DEBUG: "False",
  DATABASE_URL: `sqlite:///${databasePath}`,
  DB_AUTO_SQLITE: "False",
  SEED_DEMO_ON_STARTUP: "False",
  SECRET_KEY: "ui-tests-secret-key-com-mais-de-32-caracteres",
  APP_SIGNING_SECRET: "ui-tests-signing-key-com-mais-de-32-caracteres",
  UI_DATABASE_PATH: databasePath,
  UI_API_PORT: "8010",
  UI_TEST_RESET_TOKEN: "smart-parking-ui-local-tests",
};

export default defineConfig({
  testDir: "./tests/ui",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  timeout: 60_000,
  globalTimeout: 10 * 60_000,
  expect: { timeout: 15_000 },
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:8000",
    viewport: { width: 1440, height: 900 },
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    launchOptions: {
      executablePath: chromiumExecutable || undefined,
    },
  },
  webServer: [
    {
      command: `${python} ../../../scripts/prepare_ui_backend.py && ${python} ../../../scripts/ui_backend_server.py`,
      url: "http://127.0.0.1:8010/health",
      cwd: process.cwd(),
      env: backendEnv,
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: "node ../../../scripts/ui_web_server.cjs",
      url: "http://127.0.0.1:8000/__ui_health",
      cwd: process.cwd(),
      env: { ...process.env, UI_WEB_PORT: "8000", UI_API_PORT: "8010" },
      timeout: 30_000,
      reuseExistingServer: false,
    },
  ],
});
