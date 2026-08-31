import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, it } from "vitest";

import type { MetadataRoute } from "next";

it("manifest defines standalone display and product icons", async () => {
  const mod = await import("../app/manifest");
  const manifest = (mod.default as () => MetadataRoute.Manifest)();
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons).toEqual([
    { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
  ]);

  for (const size of [192, 512]) {
    const png = readFileSync(resolve(__dirname, `../../public/icons/icon-${size}.png`));
    expect(png.subarray(1, 4).toString()).toBe("PNG");
    expect(png.readUInt32BE(16)).toBe(size);
    expect(png.readUInt32BE(20)).toBe(size);
  }
});

it("never caches authenticated API responses", () => {
  const source = readFileSync(resolve(__dirname, "../../public/sw.js"), "utf-8");
  expect(source).not.toMatch(/\/api\/v1.*cache\.put/);
});

it("registers the service worker from the production root layout", () => {
  const layout = readFileSync(resolve(__dirname, "../app/layout.tsx"), "utf-8");
  const registration = readFileSync(
    resolve(__dirname, "../app/service-worker-registration.tsx"),
    "utf-8",
  );
  expect(layout).toContain("<ServiceWorkerRegistration />");
  expect(registration).toContain('navigator.serviceWorker.register("/sw.js")');
  expect(registration).toContain('process.env.NODE_ENV !== "production"');
});
