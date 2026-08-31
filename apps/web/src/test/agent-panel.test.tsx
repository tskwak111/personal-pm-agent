import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { AgentPanel } from "../features/agent/agent-panel";

const operationBeforeVerify = {
  id: "op-1",
  steps: [
    { step: "OBSERVE", status: "SUCCEEDED" },
    { step: "PLAN", status: "SUCCEEDED" },
    { step: "ACT", status: "ATTEMPTED" },
  ],
  verified: false,
};

it("renders operation progress without claiming success before verify", () => {
  render(<AgentPanel initialOperation={operationBeforeVerify} />);
  expect(screen.getByText("외부 반영 확인 중")).toBeVisible();
  expect(screen.queryByText("완료되었습니다")).not.toBeInTheDocument();
});
