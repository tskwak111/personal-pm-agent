export type StreamOptions = {
  operationId: string;
  lastEventId?: string;
};

export function createOperationStream({ operationId, lastEventId }: StreamOptions) {
  const url = new URL(`/api/v1/agent/operations/${operationId}/stream`, window.location.origin);
  if (lastEventId) url.searchParams.set("last_event_id", lastEventId);
  // EventSource may be unavailable in non-browser environments (tests/SSR).
  const source = typeof EventSource !== "undefined" ? new EventSource(url) : null;
  return { url, source };
}
