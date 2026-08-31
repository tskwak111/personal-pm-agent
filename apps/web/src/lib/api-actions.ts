import { api } from "./api";

function requireData<T>(result: { data?: T; error?: unknown }): T {
  if (result.error !== undefined || result.data === undefined) {
    const code =
      typeof result.error === "object" && result.error !== null && "code" in result.error
        ? String(result.error.code)
        : "API_REQUEST_FAILED";
    throw new Error(code);
  }
  return result.data;
}

export async function startTask(task: { id: string; version: number }) {
  return requireData(
    await api.POST("/api/v1/tasks/{task_id}/transition", {
      params: { path: { task_id: task.id } },
      body: {
        expected_version: task.version,
        target_status: "in_progress",
        blocker_resolved: false,
        completion_confirmed: false,
        waiting_resolved: false,
      },
    }),
  );
}

export async function decideCandidate(id: string, decision: "confirm" | "ignore") {
  return requireData(
    await api.POST("/api/v1/inbox/candidates/{candidate_id}/decision", {
      params: { path: { candidate_id: id } },
      body: { decision },
    }),
  );
}

export async function decideProposal(
  id: string,
  expectedVersion: number,
  decision: "approve" | "reject",
) {
  return requireData(
    await api.POST("/api/v1/proposals/{proposal_id}/approve", {
      params: { path: { proposal_id: id } },
      body: { decision, expected_version: expectedVersion },
    }),
  );
}

export async function connectCalendar() {
  return requireData(
    await api.POST("/api/v1/calendar/connections", { body: { mode: "READ_ONLY" } }),
  );
}
