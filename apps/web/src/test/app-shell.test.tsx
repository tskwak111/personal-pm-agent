import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { AppShell } from "../features/navigation/app-shell";
import AppLayout from "../app/(app)/layout";

it("exposes the five primary destinations", () => {
  render(
    <AppShell>
      <div>content</div>
    </AppShell>,
  );
  for (const name of ["오늘", "인박스", "프로젝트", "캘린더", "리뷰"]) {
    expect(screen.getAllByRole("link", { name })[0]).toBeVisible();
  }
});

it("has a keyboard reachable agent trigger", () => {
  render(
    <AppShell>
      <div>content</div>
    </AppShell>,
  );
  const trigger = screen.getAllByRole("button", { name: "에이전트 열기" })[0];
  expect(trigger).toHaveAttribute("aria-expanded", "false");
});

it("wraps application routes in the shared shell", () => {
  render(<AppLayout>today</AppLayout>);
  expect(screen.getByRole("navigation", { name: "주요 메뉴" })).toBeVisible();
  expect(screen.getByText("today")).toBeVisible();
});
