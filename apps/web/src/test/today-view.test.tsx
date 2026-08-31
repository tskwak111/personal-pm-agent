import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { TodayView } from "../features/today/today-view";

const todayPlanFixture = {
  coreOutcome: "보고서 초안 완성",
  selectionReason: "Base Pass 최상위 우선순위",
  fixedEvents: [{ title: "팀 회의", minutes: 60 }],
  mustDo: [
    {
      id: "t1",
      title: "ERD 작성",
      minutes: 90,
      status: "ready",
      version: 1,
      risks: [{ label: "마감 임박", ruleId: "PLAN-004" }],
    },
  ],
  queue: [],
  notToday: [],
};

it("shows why the core outcome is selected", () => {
  render(<TodayView plan={todayPlanFixture} onStartSession={vi.fn()} />);
  expect(screen.getByText("오늘의 핵심 결과")).toBeVisible();
  expect(screen.getByText(/Base Pass/)).toBeVisible();
});

it("starts a ready task with one action", async () => {
  const startSessionMock = vi.fn();
  render(<TodayView plan={todayPlanFixture} onStartSession={startSessionMock} />);
  await userEvent.click(screen.getByRole("button", { name: "ERD 작성 시작" }));
  expect(startSessionMock).toHaveBeenCalledTimes(1);
  expect(startSessionMock).toHaveBeenCalledWith(todayPlanFixture.mustDo[0]);
});

it("renders risk cards from planner rule ids", () => {
  render(<TodayView plan={todayPlanFixture} onStartSession={vi.fn()} />);
  expect(screen.getByText("마감 임박")).toBeVisible();
});

it("disables duplicate starts while the mutation is pending", async () => {
  let finish: () => void = () => {};
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  const start = vi.fn(() => pending);
  render(<TodayView plan={todayPlanFixture} onStartSession={start} />);

  await userEvent.click(screen.getByRole("button", { name: "ERD 작성 시작" }));

  const button = screen.getByRole("button", { name: "시작 중…" });
  expect(button).toBeDisabled();
  await userEvent.click(button);
  expect(start).toHaveBeenCalledTimes(1);
  finish();
});
