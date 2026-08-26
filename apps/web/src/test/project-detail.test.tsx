import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { DependencyPanel } from "../features/projects/dependency-panel";
import { ProjectHeader } from "../features/projects/project-header";

const highProgressHighRiskProject = {
  title: "데이터 파이프라인",
  executionProgress: 82,
  riskLevel: "High",
  riskReasons: ["마감 3일 남음, 잔여 40시간"],
};

const externalDatasetDependency = {
  id: "dep-1",
  label: "외부 데이터셋 수신",
  owner: "민수",
  isExternal: true,
};

it("does not equate effort progress with deadline health", () => {
  render(<ProjectHeader project={highProgressHighRiskProject} />);
  expect(screen.getByText("실행 진행률 82%")).toBeVisible();
  expect(screen.getByText("마감 가능성 High")).toBeVisible();
});

it("shows external dependency owner without presenting it as our task", () => {
  render(<DependencyPanel dependencies={[externalDatasetDependency]} />);
  expect(screen.getByText(/담당: 민수/)).toBeVisible();
  expect(screen.queryByRole("button", { name: "완료 처리" })).not.toBeInTheDocument();
});
