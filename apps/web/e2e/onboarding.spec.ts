import { expect, test } from "./fixtures";

test("onboarding completes the five approved stages", async ({ page }) => {
  await page.goto("/onboarding");
  const steps = ["기본 정보", "기존 자료", "자동 구조", "필요한 확인", "초기 상황 보고서"];
  for (const [index, step] of steps.entries()) {
    await expect(page.getByRole("heading", { name: step })).toBeVisible();
    if (index < steps.length - 1) await page.getByRole("button", { name: "계속" }).click();
  }
});
