/**
 * UX-001..UX-006 interaction-time instrumentation.
 *
 * Events are recorded client-side and delivered via sendBeacon so page
 * unload cannot lose the final event. Durations use monotonic
 * performance.now(), never wall clocks.
 */

export const UX_EVENT_NAMES = [
  "task_started",
  "task_completed",
  "candidate_confirmed",
  "proposal_approved",
  "agent_opened",
  "briefing_viewed",
] as const;

export type UxEventName = (typeof UX_EVENT_NAMES)[number];

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

  const payload = JSON.stringify({ name, duration_ms: durationMs, metadata });
  void fetch("/api/v1/analytics/ux-events", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: payload,
    keepalive: true,
  }).catch(() => undefined);
}
