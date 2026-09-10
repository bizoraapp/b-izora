/* ============================================================================
   BIZORA SERVICE WORKER — PHASE 4: SAFE UPDATE ENGINE
   ============================================================================
   Builds on Phase 1 (foundation) and Phase 2 (offline engine / caching
   strategies) without altering their shape. Phase 4 adds: rollback-safe
   cache retention (previous version's cache is kept one extra cycle
   instead of deleted immediately), and version broadcasting to the page
   so the "Update available" banner shows real version info instead of a
   generic message.

   Still does NOT touch IndexedDB (CreditBossDB) — that remains 100%
   owned by the app's own S.get()/S.set()/S.obj()/S.setObj() layer.
   ========================================================================== */

const CACHE_VERSION = 'v114';
/* Rollback safety net: the cache from this version is kept alive one
   extra deploy cycle rather than deleted the moment v3 activates. If a
   deploy turns out broken, the previous version's cached assets are
   still present for one more cycle — a real (if modest) safety margin
   for a static single-file app with no server-side rollback mechanism. */
const PREVIOUS_CACHE_VERSION = 'v112';
const CACHE_NAME = `bizora-${CACHE_VERSION}`;
const FONT_CACHE_NAME = `bizora-fonts-${CACHE_VERSION}`;

/* App-shell files — Cache First. These rarely change without a deploy,
   so once cached they're served instantly with no network round-trip. */
const APP_SHELL = [
  './index.html',
  './manifest.json',
  './offline.html',
  './icons/icon-72x72.png',
  './icons/icon-96x96.png',
  './icons/icon-128x128.png',
  './icons/icon-144x144.png',
  './icons/icon-152x152.png',
  './icons/icon-192x192.png',
  './icons/icon-384x384.png',
  './icons/icon-512x512.png',
  './icons/icon-maskable-192x192.png',
  './icons/icon-maskable-512x512.png'
];

/* The single HTML file IS the app (HTML+CSS+JS combined) — it's treated
   with Stale-While-Revalidate rather than pure Cache First: users get an
   instant response from cache (same speed benefit as Cache First), while
   a fresh copy is fetched silently in the background for next time. This
   is the correct professional strategy for a shell that updates on
   deploy, versus icons/fonts which are immutable between versions. */
const SWR_PATHS = ['./index.html', './', './index.html'];

const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

/* ---------------------------------------------------------------------------
   CACHE MANAGER
   Small set of pure helper functions — versioning, integrity checking,
   and recovery all live here so the fetch/install/activate handlers
   below stay readable. Future phases (cloud sync) can extend this
   object without touching the event wiring.
--------------------------------------------------------------------------- */
const CacheManager = {
  async precache() {
    const cache = await caches.open(CACHE_NAME);
    // allSettled so one missing/renamed file (e.g. a dev testing a partial
    // deploy) never blocks the rest of the shell from being cached.
    const results = await Promise.allSettled(APP_SHELL.map((url) => cache.add(url)));
    const failed = results
      .map((r, i) => (r.status === 'rejected' ? APP_SHELL[i] : null))
      .filter(Boolean);
    if (failed.length) {
      console.warn('[Bizora SW] Precache incomplete, missing:', failed);
    }
    return failed;
  },

  /* Integrity check: confirm every expected app-shell file is actually
     present in the cache. Called on activate so a corrupted or partially
     populated cache from a previous failed deploy self-heals instead of
     silently serving a broken offline experience. */
  async verifyIntegrity() {
    const cache = await caches.open(CACHE_NAME);
    const missing = [];
    for (const url of APP_SHELL) {
      const match = await cache.match(url);
      if (!match) missing.push(url);
    }
    return missing;
  },

  async recover(missingUrls) {
    if (!missingUrls.length) return;
    const cache = await caches.open(CACHE_NAME);
    await Promise.allSettled(
      missingUrls.map((url) =>
        fetch(url, { cache: 'no-store' })
          .then((res) => {
            if (res && res.status === 200) return cache.put(url, res);
          })
          .catch((err) => console.warn('[Bizora SW] Recovery failed for', url, err))
      )
    );
  },

  async cleanupOldCaches() {
    const keys = await caches.keys();
    /* Phase 4: keep current + previous version's caches; only delete
       anything two or more versions back. This is the rollback safety
       net described above. */
    const retained = [
      CACHE_NAME, FONT_CACHE_NAME,
      `bizora-${PREVIOUS_CACHE_VERSION}`, `bizora-fonts-${PREVIOUS_CACHE_VERSION}`
    ];
    return Promise.all(
      keys
        .filter((key) => key.startsWith('bizora-') && !retained.includes(key))
        .map((key) => caches.delete(key))
    );
  }
};

/* ---------------------------------------------------------------------------
   INSTALL
   The new worker installs and then WAITS. It does not activate itself.

   Activation is the user's decision: the page shows the "Update available"
   banner, and only when the merchant taps "Update now" does the page post
   SKIP_WAITING (see the message handler at the bottom of this file) and
   release this worker. Tapping "Remind me later" leaves the current
   session completely untouched.

   This deliberately reverses the earlier automatic self.skipWaiting()
   call. That call was added to rescue legacy 3.6.1 clients, whose
   cache-first worker had no way to release a waiting replacement — for
   them the lifecycle had to do the upgrading because their page had no
   banner. It worked, but it applied to every client, so modern
   installations lost their consent step too: a successful update
   activated immediately, clients.claim() took the page over, and
   controllerchange reloaded it underneath whatever the merchant was
   doing. A POS cart lives in memory (posItems) and does not survive a
   reload, so this could discard a sale in progress.

   Every install now in the field is 4.0.7 or newer and has a working
   banner and SKIP_WAITING handler, so nothing depends on the automatic
   rescue any more.

   A critical-asset failure now REJECTS the install rather than returning
   quietly. Previously the worker stayed installed-and-waiting, which was
   harmless while the banner was unreachable — but now that the banner is
   the normal path, a half-cached worker would be offered to the user as a
   legitimate update and could break offline mode when activated. Throwing
   makes the browser discard this worker; the previous one keeps serving
   the app, and the next update check retries cleanly.
--------------------------------------------------------------------------- */
const CRITICAL_SHELL = ['./index.html', './manifest.json', './offline.html'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const failed = await CacheManager.precache();
      const criticalFailed = failed.filter((url) => CRITICAL_SHELL.includes(url));
      if (criticalFailed.length) {
        console.warn('[Bizora SW] Critical asset(s) failed to precache, discarding this worker:', criticalFailed);
        throw new Error('Critical precache failed: ' + criticalFailed.join(', '));
      }
      // Installed and cached successfully. Now wait for the user.
    })()
  );
});

/* ---------------------------------------------------------------------------
   ACTIVATE
   Cleanup only happens after this activation succeeds, and integrity
   verification + recovery runs every activation (cheap — it's a handful
   of cache.match() calls) so a broken cache from any prior session gets
   repaired automatically without user intervention.
--------------------------------------------------------------------------- */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      await CacheManager.cleanupOldCaches();
      const missing = await CacheManager.verifyIntegrity();
      if (missing.length) {
        console.warn('[Bizora SW] Cache integrity check found gaps, recovering:', missing);
        await CacheManager.recover(missing);
      }
      await self.clients.claim();

      // Phase 4: let every open tab know which version is now active, so
      // the page's UpdateManager can show real version info rather than a
      // generic "a new version is ready" message.
      const clients = await self.clients.matchAll({ type: 'window' });
      clients.forEach((client) => client.postMessage({ type: 'SW_VERSION', version: CACHE_VERSION }));
    })()
  );
});

/* ---------------------------------------------------------------------------
   FETCH
   Three strategies, chosen per request:
   - Cache First   → icons, manifest (immutable between deploys)
   - Stale-While-Revalidate → the HTML app shell, Google Fonts
   - Network First → reserved for future cloud API calls (Phase 3+);
     unused today since Bizora has no backend yet.
--------------------------------------------------------------------------- */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isFontHost = FONT_HOSTS.includes(url.hostname);

  if (!isSameOrigin && !isFontHost) return; // untouched passthrough

  const isIcon = isSameOrigin && url.pathname.includes('/icons/');
  const isManifest = isSameOrigin && url.pathname.endsWith('manifest.json');
  const isShell =
    isSameOrigin &&
    (request.mode === 'navigate' || SWR_PATHS.some((p) => url.pathname.endsWith(p.replace('./', ''))));

  if (isIcon || isManifest) {
    event.respondWith(cacheFirst(request, CACHE_NAME));
    return;
  }

  if (isFontHost) {
    event.respondWith(staleWhileRevalidate(request, FONT_CACHE_NAME));
    return;
  }

  if (isShell) {
    event.respondWith(staleWhileRevalidate(request, CACHE_NAME, './offline.html'));
    return;
  }

  // Any other same-origin GET: network-first with cache fallback, same as
  // Phase 1's conservative default.
  event.respondWith(networkFirst(request, CACHE_NAME));
});

/* Cache First: serve from cache immediately; only hit network on a miss,
   then populate the cache for next time. */
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response && response.status === 200) cache.put(request, response.clone());
    return response;
  } catch (err) {
    return cached; // undefined — nothing we can do offline for a never-cached asset
  }
}

/* Stale-While-Revalidate: return cache instantly if present, but always
   kick off a background fetch to refresh the cache for the *next* load.
   Falls back to offlineFallback (if provided) only when there's neither
   a cached copy nor network. */
async function staleWhileRevalidate(request, cacheName, offlineFallback) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const networkFetch = fetch(request)
    .then((response) => {
      if (response && response.status === 200) cache.put(request, response.clone());
      return response;
    })
    .catch(() => undefined);

  if (cached) {
    // Don't await — let the revalidation happen in the background.
    networkFetch;
    return cached;
  }

  const fresh = await networkFetch;
  if (fresh) return fresh;

  if (offlineFallback) {
    const fallback = await caches.match(offlineFallback);
    if (fallback) return fallback;
  }
  return new Response('Offline', { status: 503, statusText: 'Offline' });
}

/* Network First: try the network, fall back to cache, then to nothing.
   Reserved today for any same-origin request that isn't shell/icon/font —
   this is also the strategy future cloud API calls (Phase 3+) will use. */
async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response && response.status === 200 && response.type === 'basic') {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    if (request.mode === 'navigate') {
      const offline = await caches.match('./offline.html');
      if (offline) return offline;
    }
    throw err;
  }
}

/* ---------------------------------------------------------------------------
   MESSAGE — user-triggered update activation (see InstallManager /
   ServiceWorkerManager in the HTML for the "Update available" banner
   that sends this).
--------------------------------------------------------------------------- */
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

/* ---------------------------------------------------------------------------
   BACKGROUND SYNC — STILL A STUB
   Bizora has no server yet. The tag below matches SyncManager's
   placeholder registration in the HTML so the plumbing is provably
   connected end-to-end, without doing anything (Promise.resolve()) until
   Phase 3 introduces real cloud sync.
--------------------------------------------------------------------------- */
self.addEventListener('sync', (event) => {
  if (event.tag === 'bizora-sync-queue') {
    event.waitUntil(Promise.resolve());
  }
});
