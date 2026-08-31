"use client";

import { useCallback } from "react";
import type { components } from "@personal-pm/api-client";

import { ApiState } from "../../../components/api-state";
import { ApprovalCenter } from "../../../features/review/approval-center";
import { WeeklyReview } from "../../../features/review/weekly-review";
import { api, requireApiData } from "../../../lib/api";
import { decideProposal } from "../../../lib/api-actions";
import { useApiResource } from "../../../lib/use-api-resource";

type ReviewData = components["schemas"]["ReviewResponse"];
const isEmpty = (value: ReviewData) =>
  value.planned_minutes === 0 && value.actual_minutes === 0 && value.pending_proposals.length === 0;

function targetText(targets: Record<string, unknown>[], key: "before_values" | "values") {
  const value = targets[0]?.[key];
  return value && typeof value === "object" ? JSON.stringify(value) : "정보 없음";
}

export default function ReviewPage() {
  const load = useCallback(async () => requireApiData(await api.GET("/api/v1/review")), []);
  const resource = useApiResource(load, isEmpty);
  if (resource.state !== "ready" || !resource.data) {
    return (
      <main>
        <h1>리뷰</h1>
        <ApiState state={resource.state}>리뷰</ApiState>
      </main>
    );
  }
  const data = resource.data;
  return (
    <main>
      <WeeklyReview
        week={{
          plannedMinutes: data.planned_minutes,
          actualMinutes: data.actual_minutes,
          missedMinutes: data.missed_minutes,
        }}
      />
      <ApprovalCenter
        proposals={data.pending_proposals.map((proposal) => ({
          id: proposal.id,
          version: proposal.version,
          beforeState: targetText(proposal.targets, "before_values"),
          proposedState: targetText(proposal.targets, "values"),
          minutesSavedOrAdded: proposal.minutes_saved_or_added,
          resultingRisk: "승인 후 재계획",
          reversible: false,
        }))}
        onDecision={async (proposal, decision) => {
          await decideProposal(proposal.id, proposal.version, decision);
          resource.reload();
        }}
      />
    </main>
  );
}
