"use client";

import { useCallback } from "react";
import type { components } from "@personal-pm/api-client";

import { ApiState } from "../../../components/api-state";
import { TodayView } from "../../../features/today/today-view";
import { api, requireApiData } from "../../../lib/api";
import { startTask } from "../../../lib/api-actions";
import { useApiResource } from "../../../lib/use-api-resource";

type TodayData = components["schemas"]["TodayResponse"];

const isEmpty = (value: TodayData) => value.plan_status === "EMPTY";

function minutes(start: string, end: string): number {
  return Math.max(0, Math.round((Date.parse(end) - Date.parse(start)) / 60_000));
}

export default function TodayPage() {
  const load = useCallback(async () => requireApiData(await api.GET("/api/v1/today")), []);
  const resource = useApiResource(load, isEmpty);
  if (resource.state !== "ready" || !resource.data) {
    return (
      <main aria-label="오늘 화면">
        <h1>오늘</h1>
        <ApiState state={resource.state}>오늘 계획</ApiState>
      </main>
    );
  }
  const data = resource.data;
  const mapTask = (task: components["schemas"]["TaskSummary"]) => ({
    id: task.id,
    title: task.title,
    minutes: task.remaining_minutes,
    status: task.status,
    version: task.version,
  });
  return (
    <TodayView
      plan={{
        coreOutcome: data.core_outcome?.title ?? "",
        selectionReason: "현재 Planner Snapshot",
        fixedEvents: data.fixed_events.map((event) => ({
          title: event.title,
          minutes: minutes(event.start_at, event.end_at),
        })),
        mustDo: data.must_do.map(mapTask),
        queue: data.queue.map(mapTask),
        notToday: data.not_today.map(mapTask),
      }}
      onStartSession={async (task) => {
        await startTask(task);
        resource.reload();
      }}
    />
  );
}
