import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { OnboardingFlow } from "../features/onboarding/onboarding-flow";

const analysisWithKnownTimezone = {
  foundFacts: ["timezone: Asia/Seoul"],
  conflicts: [
    { id: "c1", label: "날짜 충돌" },
    { id: "c2", label: "날짜 충돌 2" },
  ],
  conflictCount: 2,
};

it("does not ask facts already found in imported sources", async () => {
  render(<OnboardingFlow initialAnalysis={analysisWithKnownTimezone} />);
  await userEvent.click(screen.getByRole("button", { name: "계속" }));
  expect(screen.queryByLabelText("시간대")).not.toBeInTheDocument();
});

it("shows grouped conflict count on the questions step", async () => {
  render(<OnboardingFlow initialAnalysis={analysisWithKnownTimezone} />);
  await userEvent.click(screen.getByRole("button", { name: "계속" }));
  await userEvent.click(screen.getByRole("button", { name: "계속" }));
  await userEvent.click(screen.getByRole("button", { name: "계속" }));
  expect(screen.getByText("날짜 충돌 2개")).toBeVisible();
});
