import { expect, test } from "./fixtures";

test("inbox confirms a sourced candidate", async ({ page }) => {
  await page.goto("/inbox");
  await expect(page.getByRole("heading", { name: "인박스" })).toBeVisible();
  await expect(page.getByText("금요일까지 제안서 초안")).toBeVisible();
  await page.getByRole("button", { name: "확정" }).click();
  await expect(page.getByText("표시할 항목이 없습니다")).toBeVisible();
});
