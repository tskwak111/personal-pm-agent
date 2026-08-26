import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, it } from "vitest";

import type { MetadataRoute } from "next";

it("manifest defines standalone display and product icons", async () => {
  const mod = await import("../app/manifest");
  const manifest = (mod.default as () => MetadataRoute.Manifest)();
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons?.length).toBeGreaterThan(0);
});

it("never caches authenticated API responses", () => {
  const source = readFileSync(resolve(__dirname, "../../public/sw.js"), "utf-8");
  expect(source).not.toMatch(/\/api\/v1.*cache\.put/);
});
