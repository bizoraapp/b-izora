# Bizora — Developer Documentation

**Version:** 4.2.1 · **Build:** 2026.09.09a · **Database schema:** v8
**Maintainer:** Ngwe Lesley Mbom

This document exists so future work on Bizora can extend it without needing to re-read all ~10,400 lines to understand how the pieces fit together. It reflects the app as of Phase 6 (production hardening) of the PWA conversion.

---

## 1. Architecture at a Glance

Bizora is a **single self-contained HTML file** plus a small set of PWA support files. There is no build step, no bundler, no framework, and no server — this is intentional, not a limitation: it's what makes the app installable and fully offline on low-end Android devices with zero setup.

```
bizora-pwa/
├── index.html      ← the entire application (HTML + CSS + JS)
├── manifest.json         ← PWA install metadata
├── service-worker.js     ← offline caching + update engine
├── offline.html           ← shown only if the shell isn't cached yet
├── _redirects             ← Netlify root rewrite
└── icons/                 ← app icons (standard + maskable, 8 sizes)
```

**Why this structure won't need a rewrite as it grows:** every "module" described below is a plain JavaScript object living in the same `<script>` block, not a separate file. This looks unusual coming from a typical multi-file frontend project, but it's the correct choice for an app whose core requirement is "must run with zero network access, zero install step, on a shop owner's existing phone." Splitting into multiple JS files would only reintroduce the loading complexity this architecture avoids.

---

## 2. Data Layer

### 2.1 Storage stack
- **IndexedDB** (`CreditBossDB`, currently schema v8) — the source of truth for all business data.
- **`S` object** (`S.get/set/obj/setObj`) — an in-memory cache synced to IndexedDB, with automatic `localStorage` fallback if IndexedDB is unavailable. **Every** read/write in the app goes through this layer — never touch IndexedDB directly.
- **`localStorage`** — used only for device-local preferences that aren't business data: feature flags (`bizora_feature_flags`), theme, the update-dismissal marker.

### 2.2 Object stores (IDB_SCHEMA)
| Store | Purpose |
|---|---|
| `customers` | Customer records |
| `creditSales` | Credit sale invoices (accessed via `S.get('sales')`) |
| `repayments` | Payments against credit sales (`S.get('payments')`) |
| `products` | Inventory |
| `posSales` | Cash/POS sales |
| `creditLedger` | Ledger entries |
| `employees` | Staff accounts (Employee Access Control) |
| `expenses` | Expense records |
| `suppliers` | **Empty scaffold** — no UI yet, reserved for a future Suppliers module |
| `reminders`, `notifications` | In-app alerts |
| `settings` | Generic key→value store — business profile, prefs, feature flags source of truth, sync queue, recovery snapshots all live here |
| `licenses` | Current activated license record |
| `auditLogs`, `activities` | Audit trail |
| `devErrorLog` | Centralized error capture output |
| `stockMovements` | Append-only stock quantity change log (cash sale, credit sale, adjustment, stock-in, reconciliation, loss) — audit trail backbone for Product History |
| `stockReconciliations` | Append-only physical count records per product per period — never overwritten, latest record per productId+period is what the reconciliation view shows |

Note the `sales`/`payments` naming: the app-facing key names (`S.get('sales')`) don't always match the underlying IDB store name (`creditSales`) — this mapping lives in `KEY_TO_STORE`. Always add new entity keys there, never assume the names match.

### 2.3 Adding a new persistent key
1. If it's structured business data → add a store to `IDB_SCHEMA`, bump `IDB_VERSION`, add to `KEY_TO_STORE`.
2. If it's a single settings-like value → just add the key name to `LEGACY_OBJ_KEYS` and use `S.obj()/S.setObj()`. No schema change needed — this is the lower-friction path and should be preferred unless you genuinely need indexed queries or expect large record counts.

---

## 3. Service Layer (Phase 3+)

A generic factory (`createEntityService`) produces consistent CRUD services per entity: `SalesService`, `CreditSalesService`, `InventoryService`, `CustomerService`, `SupplierService`, `ExpenseService`, `EmployeeService`. Each has `getAll/getById/add/update/softDelete/count`.

**Important:** these services are **not** currently called by the existing UI — the UI still uses its original direct functions (`saveCustomer()`, `recordSale()`, etc.), which remain the source of truth for business logic. The service layer exists for future incremental adoption, particularly anywhere new automated logic (sync, integrations, bulk imports) needs a consistent API instead of duplicating UI-coupled logic.

Supporting services: `ValidationService` (per-entity validators), `AuditService`/`ErrorManager` (thin facades over the pre-existing `logAuditEvent()`/`DevSuite.logError()` — do not build a second logging system), `RecoveryManager` (auto-snapshots before destructive actions), `DatabaseManager`/`DatabaseHealthManager` (health checks, never auto-deletes anything), `FeatureFlags` (localStorage, all default off), `PerformanceManager` (debounce/throttle/paginate utilities, not yet wired into render loops).

---

## 4. PWA Layer

- **`service-worker.js`**: stale-while-revalidate for the app shell, cache-first for icons/manifest, stale-while-revalidate for Google Fonts. Keeps the *previous* cache version alive one extra deploy cycle as a rollback safety net (`PREVIOUS_CACHE_VERSION`).
- **`ServiceWorkerManager`** (in-page): shows the "Update Now / Remind Me Later" banner, driven by real version numbers the SW broadcasts via `postMessage`.
- **`OfflineManager`**: online/offline banner — informational only, never blocks a workflow.
- **`InstallManager`**: install prompt + "Bizora Installed Successfully" toast.

**Versioning convention:** `APP_VERSION` (in the HTML) and `CACHE_VERSION` (in `service-worker.js`) should be bumped together on any deploy that changes cached files. `BUILD_NUMBER` is a free-form string (currently date-based) shown on the About page for support purposes.

---

## 5. Licensing

Offline ECDSA (P-256) signature verification — no server, no network call for activation. The public key in `LICENSE_PUBLIC_KEY_JWK` can only *verify*; only the separate Developer Admin Suite holds the private key that *issues* licenses. Trial tracking resists simple clock-rollback (tracks the highest elapsed-day count ever observed, never lets it decrease).

**Do not modify the activation/verification flow.** If you need to extend licensing (e.g. multi-device, subscription tiers), add new fields to the signed payload on the Admin Suite side and read them in `License.info()` — the verification mechanism itself doesn't need to change.

---

## 6. Upgrade / Migration Process

1. **Schema changes**: add the new store/index to `IDB_SCHEMA`, bump `IDB_VERSION`. The existing `onupgradeneeded` handler only *adds* missing stores — it never touches existing ones. Document the change in `DatabaseManager.MIGRATIONS`.
2. **New settings-style keys**: add to `LEGACY_OBJ_KEYS` — no version bump needed.
3. **Deploys**: bump `APP_VERSION` + `CACHE_VERSION` together. Netlify (or your chosen host) picks up the new files; the service worker's stale-while-revalidate + update banner handle the rest — users are never forced to reload mid-task.
   The new worker installs and then **waits**; it must never call `skipWaiting()` on itself. Activation happens only when the user taps “Update now”, which posts `SKIP_WAITING`, and the page reloads only when `userInitiatedUpdate` is set. Both guards are required — removing either one reintroduces silent, forced reloads (this regressed once, in the 4.0.7–4.1.1 range). A critical-asset precache failure rejects the install so the broken worker is discarded rather than offered to the user.
4. **Testing before shipping a change**: run the internal Developer Test Suite (Ctrl+Alt+Shift+D in the running app), confirm a fresh-install boot, an upgrade-from-previous-version boot, and an offline boot all work.

---

## 7. Maintenance Guidelines

- **Never** rewrite a working function to "clean it up" without a specific bug or feature driving the change — this codebase's reliability comes from incremental, additive changes, not periodic rewrites.
- **Never** delete a `LEGACY_OBJ_KEYS`/`KEY_TO_STORE` entry, even if a feature using it is deprecated — existing user devices may still have that data.
- When adding a new page: follow the existing `<div class="page" id="page-X">` + `PAGE_LOADERS.X = loadX` + nav-item pattern (see the Help Center page as the most recent example).
- When touching anything financial (sale totals, balances, credit calculations): the existing indexed-Map optimizations (`_salesById`, `_paymentsByInvId`, etc.) exist specifically to keep O(1) lookups at scale — don't reintroduce full-array `.find()`/`.filter()` scans in hot paths without checking whether an index already exists.
- Before any release, sanity-check `node --check` against the extracted `<script>` contents (there are two blocks: the main app script and the PWA runtime script) — a syntax error in a 10,000+ line single file is otherwise easy to miss until a user hits it.

---

## 8. Known Scope Decisions (intentionally not done)

Documented here so they're not mistaken for oversights:
- No virtual scrolling / list pagination retrofit into existing render functions — flagged as a targeted future pass rather than a blanket change.
- No automatic wiring of `SyncManager.enqueue()` into sale/payment/inventory save functions — the queue infrastructure exists, but activating it is a cloud-sync-phase decision, not a hardening-phase one.
- No full touch-target/contrast accessibility retrofit — only OS-preference-respecting CSS (`prefers-reduced-motion`, `prefers-contrast`, `:focus-visible`) was added.
