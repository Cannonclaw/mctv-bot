/**
 * MCTV Client Portal — Service Worker
 *
 * Caching strategy:
 *   - Static assets (icons, CSS, fonts): Cache-first (fast loads)
 *   - API/data requests: Network-first (fresh data, offline fallback)
 *   - HTML pages: Network-first with offline fallback page
 *
 * © 2026 MCTV Digital, Inc.
 */

const CACHE_NAME = "mctv-portal-v1";
const OFFLINE_URL = "/";

// Assets to pre-cache on install
const PRECACHE_ASSETS = [
  "/app/static/icons/icon-192x192.png",
  "/app/static/icons/icon-512x512.png",
  "/app/static/manifest.json",
];

// ── Install: Pre-cache critical assets ────────────────────────────────────
self.addEventListener("install", (event) => {
  console.log("[SW] Installing MCTV Portal service worker...");
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        console.log("[SW] Pre-caching critical assets");
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// ── Activate: Clean up old caches ─────────────────────────────────────────
self.addEventListener("activate", (event) => {
  console.log("[SW] Activating service worker...");
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log("[SW] Deleting old cache:", name);
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// ── Fetch: Network-first for pages, cache-first for static assets ─────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") return;

  // Skip Streamlit WebSocket connections (_stcore/stream)
  if (url.pathname.includes("_stcore/stream") || url.pathname.includes("_stcore/host-config")) {
    return;
  }

  // Static assets (icons, images, fonts): Cache-first
  if (
    url.pathname.startsWith("/app/static/") ||
    url.pathname.match(/\.(png|jpg|jpeg|svg|gif|ico|woff2?|ttf|eot)$/)
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // Everything else: Network-first with cache fallback
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful responses for offline use
        if (response.ok && response.type === "basic") {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => {
        // Offline: try cache
        return caches.match(request).then((cached) => {
          if (cached) return cached;
          // If it's a navigation request, show the cached home page
          if (request.mode === "navigate") {
            return caches.match(OFFLINE_URL);
          }
          return new Response("Offline", { status: 503, statusText: "Offline" });
        });
      })
  );
});
