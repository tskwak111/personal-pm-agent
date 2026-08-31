import { expect, test } from "./fixtures";

test("calendar separates flexible queue", async ({ page }) => {
  await page.goto("/calendar");
  await expect(page.getByRole("region", { name: "아직 배치되지 않은 작업" })).toBeAttached();
  await expect(page.getByText("오늘의 핵심 작업")).toBeVisible();
});
