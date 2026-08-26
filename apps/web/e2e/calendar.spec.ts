import { expect, test } from "@playwright/test";

test("calendar separates flexible queue", async ({ page }) => {
  await page.goto("/calendar");
  await expect(page.getByRole("region", { name: "아직 배치되지 않은 작업" })).toBeAttached();
});
