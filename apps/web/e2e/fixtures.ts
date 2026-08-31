import { expect, test as base } from "@playwright/test";

let sharedToken: string | undefined;

export const test = base.extend({
  page: async ({ page, request }, run) => {
    if (!sharedToken) {
      const response = await request.post("/api/v1/identity/test-session", {
        data: { email: "browser-e2e@example.com", seed_demo: true },
      });
      expect(response.ok()).toBe(true);
      sharedToken = ((await response.json()) as { token: string }).token;
    } else {
      const response = await request.post("/api/v1/identity/test-reset", {
        headers: { Authorization: `Bearer ${sharedToken}` },
      });
      expect(response.ok()).toBe(true);
    }
    const token = sharedToken;
    if (!token) throw new Error("test session did not return a token");
    await page.addInitScript((sessionToken) => {
      sessionStorage.setItem("personal-pm.session", sessionToken);
    }, token);
    await run(page);
  },
});

export { expect };
