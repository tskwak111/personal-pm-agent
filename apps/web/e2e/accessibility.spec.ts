import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures";

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

async function tabTo(page: Page, label: string) {
  const visited: string[] = [];
  for (let index = 0; index < 30; index += 1) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => ({
      label: document.activeElement?.getAttribute("aria-label"),
      tag: document.activeElement?.tagName,
      text: document.activeElement?.textContent?.trim(),
    }));
    visited.push(`${focused.tag}:${focused.label ?? focused.text ?? ""}`);
    if (focused.label === label || focused.text === label) return;
  }
  throw new Error(`keyboard focus did not reach ${label}: ${visited.join(" -> ")}`);
}

test("primary navigation and approval are keyboard reachable", async ({ page }) => {
  await page.goto("/review");
  await tabTo(page, "오늘");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/today$/);

  await page.goto("/review");
  await expect(page.getByRole("button", { name: "승인" })).toBeEnabled();
  await tabTo(page, "승인");
  await page.keyboard.press("Enter");
  await expect(page.getByText("제안이 실행되었습니다")).toBeVisible();
});
