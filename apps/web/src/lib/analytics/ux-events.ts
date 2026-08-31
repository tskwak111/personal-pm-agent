/**
 * UX-001..UX-006 interaction-time instrumentation.
 *
 * Events are recorded client-side and delivered with a keepalive request so
 * page unload does not discard the final event. Durations use monotonic
 * performance.now(), never wall clocks.
 */

export type UxEventName = components["schemas"]["UxEventName"];

declare global {
  interface Window {
    __uxEvents?: { name: string; duration_ms: number; metadata: Record<string, string> }[];
  }
}

export function startUxTimer(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

export function recordUxEvent(
  name: UxEventName,
  startedAt: number,
  metadata: Record<string, string> = {},
): void {
  if (typeof window === "undefined") return;
  const durationMs = Math.round(
    (typeof performance !== "undefined" ? performance.now() : Date.now()) - startedAt,
  );
  // Debug/test hook: the E2E suite asserts on this array.
  (window.__uxEvents ??= []).push({ name, duration_ms: durationMs, metadata });

  void api
    .POST("/api/v1/analytics/ux-events", {
      body: { schema_version: 1, name, duration_ms: durationMs },
      keepalive: true,
    })
    .catch(() => undefined);
}
import type { components } from "@personal-pm/api-client";

import { api } from "../api";
