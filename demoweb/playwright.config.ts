import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL(".", import.meta.url));
const repositoryRoot = path.resolve(webRoot, "..");
const apiPort = Number(process.env.VNEGUIDE_E2E_API_PORT ?? "38100");
const webPort = Number(process.env.VNEGUIDE_E2E_WEB_PORT ?? "38101");
const apiUrl = `http://127.0.0.1:${apiPort}`;
const webUrl = `http://127.0.0.1:${webPort}`;
const localPython = path.join(
  repositoryRoot,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const python = process.env.VNEGUIDE_E2E_PYTHON ?? (process.env.CI ? "python" : localPython);

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [
    ["line"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL: webUrl,
    locale: "vi-VN",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `"${python}" -m vneguide.api`,
      cwd: repositoryRoot,
      env: {
        ...process.env,
        VNEGUIDE_API_HOST: "127.0.0.1",
        VNEGUIDE_API_PORT: String(apiPort),
        VNEGUIDE_LLM_PROVIDER: "mock",
        VNEGUIDE_MODEL: "mock-scripted",
      },
      url: `${apiUrl}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run build && npm run start -- --hostname 127.0.0.1 --port ${webPort}`,
      cwd: webRoot,
      env: {
        ...process.env,
        VNEGUIDE_API_BASE_URL: apiUrl,
      },
      url: webUrl,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
