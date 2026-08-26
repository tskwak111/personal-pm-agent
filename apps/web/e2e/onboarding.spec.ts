import { expect, test } from "@playwright/test";

test("onboarding completes the five approved stages", async ({ page }) => {
  await page.goto("/onboarding");
  for (const step of ["기본 정보", "기존 자료", "자동 구조", "필요한 확인", "초기 상황 보고서"]) {
    await expect(page.getByRole("heading", { name: step })).toBeVisible();
    const next = page.getByRole("button", { name: "계속" });
    if (await next.isVisible()) await next.click();
  }
});
