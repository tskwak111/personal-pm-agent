import { expect, test } from "./fixtures";

test("task start is one user action", async ({ page }) => {
  await page.goto("/today");
  const start = page.getByRole("button", { name: "오늘의 핵심 작업 시작" });
  await expect(start).toBeVisible();
  await start.click();
  await expect(page.getByText("진행 중")).toBeVisible();
  const events = await page.evaluate(() => window.__uxEvents ?? []);
  expect(events.filter((event) => event.name === "task_started")).toHaveLength(1);
});
