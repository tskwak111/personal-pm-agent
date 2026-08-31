import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { CandidateCard } from "../features/inbox/candidate-card";

const dateOnlyDeadlineCandidate = {
  id: "cand-1",
  title: "CS101 과제",
  kind: "HARD_DEADLINE",
  deadlineDate: "2026-09-20",
  timeKnown: false,
  sources: [
    {
      id: "s1",
      label: "강의계획서",
      snippet: "9월 20일 제출 (시각 미정)",
    },
  ],
};

const conflictingDeadlineCandidate = {
  id: "cand-2",
  title: "최종 발표",
  kind: "HARD_DEADLINE",
  deadlineDate: null,
  timeKnown: false,
  conflictChoices: [
    { sourceId: "s1", label: "강의계획서", date: "2026-09-20" },
    { sourceId: "s2", label: "최근 과제 공지", date: "2026-09-25" },
  ],
  sources: [],
};

it("shows unknown deadline time instead of invented time", () => {
  render(<CandidateCard candidate={dateOnlyDeadlineCandidate} />);
  expect(screen.getByText("마감 시각 미확인")).toBeVisible();
  expect(screen.queryByText("23:59")).not.toBeInTheDocument();
});

it("requires an explicit source choice for conflicting deadlines", () => {
  render(<CandidateCard candidate={conflictingDeadlineCandidate} />);
  expect(screen.getByRole("radio", { name: /강의계획서/ })).toBeVisible();
  expect(screen.getByRole("radio", { name: /최근 과제 공지/ })).toBeVisible();
});

it("renders original evidence snippets", () => {
  render(<CandidateCard candidate={dateOnlyDeadlineCandidate} />);
  expect(screen.getByText("근거 원본")).toBeVisible();
  expect(screen.getByText(/9월 20일 제출/)).toBeVisible();
});

it("confirms a candidate through the supplied mutation", async () => {
  const decide = vi.fn();
  render(<CandidateCard candidate={dateOnlyDeadlineCandidate} onDecision={decide} />);
  await userEvent.click(screen.getByRole("button", { name: "확정" }));
  expect(decide).toHaveBeenCalledWith("cand-1", "confirm");
});

import { InboxList } from "../features/inbox/inbox-list";
import { fireEvent } from "@testing-library/react";

it("filters candidates by processing status, not kind", () => {
  const candidates = [
    { ...dateOnlyDeadlineCandidate, status: "NEEDS_CONFIRMATION" },
    {
      id: "cand-ok",
      title: "정리됨",
      kind: "HARD_DEADLINE",
      status: "STRUCTURED",
      deadlineDate: null,
      timeKnown: false,
      sources: [],
    },
  ];
  render(<InboxList candidates={candidates} />);
  // Both visible under ALL
  expect(screen.getByText("CS101 과제")).toBeVisible();
  expect(screen.getByText("정리됨")).toBeVisible();
  // Switch to STRUCTURED: only the structured one remains
  fireEvent.click(screen.getByRole("tab", { name: "STRUCTURED" }));
  expect(screen.queryByText("CS101 과제")).not.toBeInTheDocument();
  expect(screen.getByText("정리됨")).toBeVisible();
});
