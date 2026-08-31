import { beforeEach, expect, it, vi } from "vitest";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { POST: post } }));

import { connectCalendar, decideCandidate, decideProposal, startTask } from "../lib/api-actions";

beforeEach(() => {
  post.mockReset();
  post.mockResolvedValue({ data: {}, error: undefined, response: { status: 200 } });
});

it("starts a version-bound task transition", async () => {
  await startTask({ id: "t1", version: 3 });
  expect(post).toHaveBeenCalledWith("/api/v1/tasks/{task_id}/transition", {
    params: { path: { task_id: "t1" } },
    body: {
      expected_version: 3,
      target_status: "in_progress",
      blocker_resolved: false,
      completion_confirmed: false,
      waiting_resolved: false,
    },
  });
});

it("confirms an owned inbox candidate", async () => {
  await decideCandidate("c1", "confirm");
  expect(post).toHaveBeenCalledWith("/api/v1/inbox/candidates/{candidate_id}/decision", {
    params: { path: { candidate_id: "c1" } },
    body: { decision: "confirm" },
  });
});

it("submits a version-bound proposal decision", async () => {
  await decideProposal("p1", 2, "approve");
  expect(post).toHaveBeenCalledWith("/api/v1/proposals/{proposal_id}/approve", {
    params: { path: { proposal_id: "p1" } },
    body: { decision: "approve", expected_version: 2 },
  });
});

it("requests a read-only calendar connection", async () => {
  await connectCalendar();
  expect(post).toHaveBeenCalledWith("/api/v1/calendar/connections", {
    body: { mode: "READ_ONLY" },
  });
});
