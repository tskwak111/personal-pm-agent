import { afterEach, describe, expect, it, vi } from "vitest";

import { createPersonalPmClient } from "./client.js";

describe("createPersonalPmClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("adds bearer auth and sends typed JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "plan-1", status: "valid" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = createPersonalPmClient({
      baseUrl: "https://api.test",
      token: () => "abc",
    });

    const result = await client.POST("/api/v1/plans", {
      body: { reason: "manual" },
    });

    const request = fetchMock.mock.calls[0]?.[0] as Request;
    expect(request.url).toBe("https://api.test/api/v1/plans");
    expect(request.headers.get("Authorization")).toBe("Bearer abc");
    await expect(request.clone().json()).resolves.toEqual({ reason: "manual" });
    expect(result.error).toBeUndefined();
  });

  it("omits authorization when no token is available", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = createPersonalPmClient({
      baseUrl: "https://api.test/",
      token: () => null,
    });

    await client.GET("/api/v1/workstreams");

    const request = fetchMock.mock.calls[0]?.[0] as Request;
    expect(request.headers.has("Authorization")).toBe(false);
  });
});
