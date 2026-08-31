"use client";

import { useCallback } from "react";
import type { components } from "@personal-pm/api-client";

import { ApiState } from "../../../components/api-state";
import { InboxList } from "../../../features/inbox/inbox-list";
import { api, requireApiData } from "../../../lib/api";
import { decideCandidate } from "../../../lib/api-actions";
import { useApiResource } from "../../../lib/use-api-resource";

type InboxData = components["schemas"]["InboxResponse"];
const isEmpty = (value: InboxData) => value.candidates.length === 0;

export default function InboxPage() {
  const load = useCallback(async () => requireApiData(await api.GET("/api/v1/inbox")), []);
  const resource = useApiResource(load, isEmpty);
  if (resource.state !== "ready" || !resource.data) {
    return (
      <main>
        <h1>인박스</h1>
        <ApiState state={resource.state}>인박스</ApiState>
      </main>
    );
  }
  return (
    <main>
      <h1>인박스</h1>
      <InboxList
        candidates={resource.data.candidates.map((candidate) => {
          const title = candidate.interpretation.title;
          const deadline = candidate.interpretation.deadline_date;
          const timeKnown = candidate.interpretation.time_known;
          return {
            id: candidate.id,
            title: typeof title === "string" ? title : candidate.kind,
            kind: candidate.kind,
            status: candidate.status,
            deadlineDate: typeof deadline === "string" ? deadline : null,
            timeKnown: typeof timeKnown === "boolean" ? timeKnown : false,
            sources: candidate.source_text
              ? [
                  {
                    id: candidate.inbox_item_id,
                    label: "원본 입력",
                    snippet: candidate.source_text,
                  },
                ]
              : [],
          };
        })}
        onDecision={async (id, decision) => {
          await decideCandidate(id, decision);
          resource.reload();
        }}
      />
    </main>
  );
}
