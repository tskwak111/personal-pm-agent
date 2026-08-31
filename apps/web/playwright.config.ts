import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "uv run alembic -c apps/api/alembic.ini upgrade head && uv run uvicorn personal_pm_api.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8001",
      cwd: "../..",
      env: {
        ...process.env,
        APP_ENVIRONMENT: "test",
        DATABASE_URL:
          process.env.PM_DATABASE_URL ??
          "postgresql+asyncpg://personal_pm:local_only_password@127.0.0.1:15432/personal_pm",
      },
      url: "http://127.0.0.1:8001/health/ready",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command:
        "pnpm --filter @personal-pm/web build && cp -R apps/web/.next/static apps/web/.next/standalone/apps/web/.next/static && cp -R apps/web/public apps/web/.next/standalone/apps/web/public && node apps/web/.next/standalone/apps/web/server.js",
      cwd: "../..",
      env: {
        ...process.env,
        API_INTERNAL_BASE_URL: "http://127.0.0.1:8001",
        HOSTNAME: "127.0.0.1",
        NEXT_PUBLIC_APP_ENVIRONMENT: "test",
        PORT: "3000",
      },
      url: "http://127.0.0.1:3000/sign-in",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
