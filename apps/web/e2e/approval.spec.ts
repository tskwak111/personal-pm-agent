import { expect, test } from "./fixtures";

test("approval executes its version-bound proposal", async ({ page }) => {
  await page.goto("/review");
  const approve = page.getByRole("button", { name: "승인" });
  await expect(approve).toBeVisible();
  await approve.click();
  await expect(page.getByText("제안이 실행되었습니다")).toBeVisible();
});
