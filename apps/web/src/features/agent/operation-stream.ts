import { getToken } from "../../lib/session";

export type StreamOptions = {
  operationId: string;
  lastEventId?: string;
  signal: AbortSignal;
};

export type OperationStreamEvent = {
  step: string;
  status: string;
  sequence: number;
};

function decodeEvent(block: string): OperationStreamEvent | null {
  const data = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!data) return null;
  const value: unknown = JSON.parse(data);
  if (
    typeof value !== "object" ||
    value === null ||
    !("step" in value) ||
    !("status" in value) ||
    !("sequence" in value) ||
    typeof value.step !== "string" ||
    typeof value.status !== "string" ||
    typeof value.sequence !== "number"
  ) {
    return null;
  }
  return { step: value.step, status: value.status, sequence: value.sequence };
}

async function* decodeBody(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replaceAll("\r\n", "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const event = decodeEvent(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (event) yield event;
        boundary = buffer.indexOf("\n\n");
      }
      if (done) return;
    }
  } finally {
    reader.releaseLock();
  }
}

function retryDelay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 1_000));
}

export async function* streamOperationEvents({
  operationId,
  lastEventId,
  signal,
}: StreamOptions): AsyncGenerator<OperationStreamEvent> {
  let cursor = lastEventId;
  while (!signal.aborted) {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || window.location.origin;
    const url = new URL(`/api/v1/agent/operations/${operationId}/stream`, baseUrl);
    if (cursor) url.searchParams.set("last_event_id", cursor);
    const token = getToken();
    try {
      const response = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal,
      });
      if (response.status === 401 || response.status === 404) {
        throw new Error(`operation stream rejected: ${response.status}`);
      }
      if (!response.ok || !response.body) throw new Error("operation stream unavailable");
      for await (const event of decodeBody(response.body)) {
        cursor = String(event.sequence);
        yield event;
      }
    } catch (error) {
      if (signal.aborted) return;
      if (error instanceof Error && error.message.startsWith("operation stream rejected")) {
        throw error;
      }
    }
    if (!signal.aborted) await retryDelay();
  }
}
