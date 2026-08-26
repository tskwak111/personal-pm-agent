// Personal PM Agent service worker.
// Policy: cache only the static app shell; NEVER cache /api/v1 responses.
const CACHE_NAME = "pma-shell-v1";
const SHELL_ASSETS = ["/", "/today"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Authenticated API calls always go to the network — never cached.
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(
    caches.match(event.request).then(
      (hit) =>
        hit ||
        fetch(event.request).then((response) => {
          const isStatic =
            event.request.method === "GET" &&
            (url.pathname.startsWith("/_next/static") ||
              url.pathname.startsWith("/icons"));
          if (isStatic) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        }),
    ),
  );
});

self.addEventListener("push", (event) => {
  const payload = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(payload.title || "Personal PM Agent", {
      body: payload.body || "",
    }),
  );
});
