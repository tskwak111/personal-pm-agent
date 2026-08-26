import { expect, test } from "@playwright/test";

test("inbox shows source evidence section", async ({ page }) => {
  await page.goto("/inbox");
  await expect(page.getByRole("heading", { name: "인박스" })).toBeVisible();
});
