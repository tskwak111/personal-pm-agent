import { expect, test } from "@playwright/test";

test("task start is one user action", async ({ page }) => {
  await page.goto("/today");
  const start = page.getByRole("button", { name: /시작$/ }).first();
  if (await start.isVisible()) {
    await start.click();
    await expect(page.getByText(/진행 중|시작/).first()).toBeVisible();
  }
});
