import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SignInPage from "../app/(auth)/sign-in/page";
import { ApiState } from "../components/api-state";
import { streamOperationEvents } from "../features/agent/operation-stream";
import { clearToken, getToken, setToken } from "../lib/session";

describe("API session state", () => {
  beforeEach(() => {
    sessionStorage.clear();
    clearToken();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps a bearer token in session storage and clears it", () => {
    expect(getToken()).toBeNull();
    setToken("abc");
    expect(getToken()).toBe("abc");
    expect(sessionStorage.getItem("personal-pm.session")).toBe("abc");
    clearToken();
    expect(getToken()).toBeNull();
  });

  it.each([
    ["loading", "불러오는 중"],
    ["unauthenticated", "로그인이 필요합니다"],
    ["empty", "표시할 항목이 없습니다"],
    ["error", "요청을 완료하지 못했습니다"],
  ] as const)("renders the %s state explicitly", (state, label) => {
    render(<ApiState state={state}>ready</ApiState>);
    expect(screen.getByText(label)).toBeVisible();
    expect(screen.queryByText("ready")).not.toBeInTheDocument();
  });

  it("renders children only in the ready state", () => {
    render(<ApiState state="ready">ready</ApiState>);
    expect(screen.getByText("ready")).toBeVisible();
  });

  it("never presents a calendar GET as a sign-in action", () => {
    render(<SignInPage />);
    expect(screen.queryByRole("link", { name: /Google로 계속/ })).not.toBeInTheDocument();
    expect(screen.getByText("로그인 공급자 미설정")).toBeVisible();
  });

  it("streams SSE with bearer auth and resumes from the last sequence", async () => {
    setToken("abc");
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(
          'id: 2\nevent: operation.step\ndata: {"step":"PLAN","status":"SUCCEEDED","sequence":2}\n\n',
          { status: 200, headers: { "Content-Type": "text/event-stream" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const abort = new AbortController();
    const stream = streamOperationEvents({
      operationId: "op-1",
      lastEventId: "1",
      signal: abort.signal,
    });

    const first = await stream.next();
    abort.abort();
    await stream.return(undefined);

    expect(first.value).toEqual({ step: "PLAN", status: "SUCCEEDED", sequence: 2 });
    const requestUrl = String(fetchMock.mock.calls[0]?.[0]);
    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(requestUrl).toContain("last_event_id=1");
    expect(new Headers(requestInit.headers).get("Authorization")).toBe("Bearer abc");
  });
});
