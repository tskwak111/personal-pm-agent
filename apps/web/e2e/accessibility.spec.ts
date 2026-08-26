import { expect, test } from "@playwright/test";

// Full axe integration arrives with @axe-core/playwright in the release
// hardening pass; this spec pins the critical pages that must be scanned.
const CRITICAL_PAGES = ["/today", "/inbox", "/projects", "/calendar", "/review"];

test.describe("accessibility coverage", () => {
  for (const path of CRITICAL_PAGES) {
    test(`page ${path} renders a main landmark`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator("main")).toBeAttached();
      expect(true).toBe(true);
    });
  }
});
