import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const CRITICAL_PAGES = ["/today", "/inbox", "/projects", "/calendar", "/review"];

test.describe("accessibility coverage", () => {
  for (const path of CRITICAL_PAGES) {
    test(`page ${path} has no serious or critical axe violations`, async ({ page }) => {
      await page.goto(path);
      const results = await new AxeBuilder({ page }).analyze();
      const serious = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious",
      );
      // Surface violation ids in the assertion message for fast triage.
      expect(
        serious.map((v) => `${v.id}(${v.impact})`),
        "serious/critical axe violations",
      ).toEqual([]);
    });

    test(`page ${path} renders a main landmark`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator("main")).toBeAttached();
    });
  }
});
