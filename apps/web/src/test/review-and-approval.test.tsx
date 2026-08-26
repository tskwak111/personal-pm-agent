import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { ProposalCard } from "../features/review/proposal-card";
import { WeeklyReview } from "../features/review/weekly-review";

const overloadProposal = {
  id: "p1",
  beforeState: "High",
  proposedState: "Medium",
  minutesSavedOrAdded: 180,
  resultingRisk: "Medium",
  reversible: true,
};

const irreversibleProposal = {
  id: "p2",
  beforeState: "Medium",
  proposedState: "Low",
  minutesSavedOrAdded: 0,
  resultingRisk: "Low",
  reversible: false,
};

it("shows before, after, saved time and resulting risk", () => {
  render(<ProposalCard proposal={overloadProposal} />);
  expect(screen.getByText("예상 절감 180분")).toBeVisible();
  expect(screen.getByText("High → Medium")).toBeVisible();
  expect(screen.getByRole("button", { name: "승인" })).toBeVisible();
});

it("does not show undo for irreversible proposal", () => {
  render(<ProposalCard proposal={irreversibleProposal} />);
  expect(screen.queryByRole("button", { name: "되돌리기" })).not.toBeInTheDocument();
});

it("weekly review compares planned vs actual capacity", () => {
  render(<WeeklyReview week={{ plannedMinutes: 1200, actualMinutes: 1050, missedMinutes: 150 }} />);
  expect(screen.getByText(/계획 1200분/)).toBeVisible();
  expect(screen.getByText(/실제 1050분/)).toBeVisible();
});
