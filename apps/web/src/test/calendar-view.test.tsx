import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { CalendarView } from "../features/calendar/calendar-view";
import { SyncStatus } from "../features/calendar/sync-status";

const calendarEvents = [
  { id: "e1", title: "팀 회의", kind: "FIXED_BUSY", date: "2026-09-01" },
  { id: "e2", title: "CS101 마감", kind: "DATE_DEADLINE", date: "2026-09-20" },
];

const flexibleTasks = [{ id: "t1", title: "ERD 작성", minutes: 90 }];

it("distinguishes internal save from external failure", () => {
  render(<SyncStatus status={{ internal: "SAVED", external: "FAILED", reason: "AUTH_EXPIRED" }} />);
  expect(screen.getByText("앱 내부 저장 완료")).toBeVisible();
  expect(screen.getByText(/Google Calendar 반영 실패/)).toBeVisible();
});

it("keeps flexible tasks outside the calendar grid", () => {
  render(<CalendarView events={calendarEvents} flexibleTasks={flexibleTasks} />);
  expect(screen.getByRole("region", { name: "아직 배치되지 않은 작업" })).toBeVisible();
});

it("shows sync success state distinctly", () => {
  render(<SyncStatus status={{ internal: "SAVED", external: "SYNCED" }} />);
  expect(screen.getByText("Google Calendar 반영 완료")).toBeVisible();
});
