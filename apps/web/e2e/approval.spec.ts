import { expect, test } from "@playwright/test";

test("approval center exposes approve action", async ({ page }) => {
  await page.goto("/review");
  await expect(page.getByText(/주간 리뷰/)).toBeVisible();
});
