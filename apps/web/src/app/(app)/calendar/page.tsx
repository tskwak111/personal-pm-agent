"use client";

import { useCallback, useState } from "react";
import type { components } from "@personal-pm/api-client";

import { ApiState } from "../../../components/api-state";
import { CalendarView } from "../../../features/calendar/calendar-view";
import { api, requireApiData } from "../../../lib/api";
import { connectCalendar } from "../../../lib/api-actions";
import { useApiResource } from "../../../lib/use-api-resource";

type CalendarData = components["schemas"]["CalendarResponse"];
const isEmpty = (value: CalendarData) =>
  value.connections.length === 0 && value.events.length === 0 && value.flexible_tasks.length === 0;

export default function CalendarPage() {
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState(false);
  const load = useCallback(async () => requireApiData(await api.GET("/api/v1/calendar")), []);
  const resource = useApiResource(load, isEmpty);
  async function beginConnection() {
    setConnecting(true);
    setConnectError(false);
    try {
      const connection = await connectCalendar();
      window.location.assign(connection.authorization_url);
    } catch {
      setConnectError(true);
    } finally {
      setConnecting(false);
    }
  }
  const connectionAction = (
    <>
      <button type="button" disabled={connecting} onClick={beginConnection}>
        {connecting ? "연결 준비 중…" : "Google Calendar 연결"}
      </button>
      {connectError ? <p role="alert">캘린더 연결을 시작하지 못했습니다</p> : null}
    </>
  );
  if (resource.state !== "ready" || !resource.data) {
    return (
      <main aria-label="캘린더 화면">
        <h1>캘린더</h1>
        {connectionAction}
        <ApiState state={resource.state}>캘린더</ApiState>
      </main>
    );
  }
  return (
    <CalendarView
      events={resource.data.events.map((event) => ({
        id: event.id,
        title: event.title,
        kind: event.kind,
        date: event.start_at,
      }))}
      flexibleTasks={resource.data.flexible_tasks.map((task) => ({
        id: task.id,
        title: task.title,
        minutes: task.remaining_minutes,
      }))}
      connectionAction={connectionAction}
    />
  );
}
