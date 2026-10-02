# Bizora — Developer Documentation

**Version:** 4.3.8 · **Build:** 2026.10.01a · **Database schema:** v8
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

---

## 9. Money Controls (4.3.7)

Four controls close the money-extraction paths found in the 4.3.6 audit. No database version change (schema stays v8); only optional fields were added to existing records.

| Control | Where | Rule |
|---|---|---|
| G1 Overpayment | `savePay()` | An amount above the invoice balance becomes account credit only after the Owner confirms (Owner / Access Control off) or approves with their password (employees, single-use approval bound to customer, invoice, amount, balance and method). Every overpayment is audit-logged with the credit before → after. Invoice must exist, belong to the customer and not be cancelled; non-finite amounts are refused. |
| G2 Credit refund | `promptRefundCredit()` (screen) → `refundAccountCredit(cid, amount, method)` (operation boundary) | Requires Manage Customers; employees also need a single-use Owner approval; amount must be > 0 and ≤ current credit; the refund method is required and stored. Every refund and every refused attempt is audit-logged. |
| G3 Expected cash | `computeDrawerCash(td, opening)` (read-only logic) → `renderCashDrawer()` (display) | Opening + cash kept from POS cash sales (paid − change) + cash payments (method `cash`, incl. deposits) + cash overpayments kept as credit − cash expenses − cash credit refunds. Non-cash methods and account credit never count. Records saved before 4.3.7 without a method are not guessed: they are excluded and counted on screen. |
| G4 Drawer edits | `saveCashDrawer()` / `commitCashDrawerEdit()` | Requires Manage Inventory. Fields still save on every keystroke; one audit entry per finished edit (value before → after), written on change, or when the app is hidden/closed. Negative / non-numeric values are never saved. |

New optional fields: `creditLedger[].method`, `expenses[].payMethod` (both written only when known). `addCreditEntry()` takes an optional 6th `method` argument; callers without it write the old record shape.

Approval kinds `overpay` and `creditRefund` reuse the existing `OwnerApproval` single-use slot (`bindKey`, `requestOwnerActionApproval`, `submitPriceApproval`).

## 10. Changelog

### After 4.3.8 — UX-01 to UX-04 (merged to `main` 2 Oct 2026, PR #5; no version bump, still build 2026.10.01a / cache v131)
- **UX-01:** `input[type=tel].fc` added to the three `.fc` selector lists. `#frPhone` (first-run wizard) is the only tel input in the app.
- **UX-02:** `checkBackupReminderOnLoad()` returns early while `FirstRunWizard.shouldShow()` is true (fresh install), so the toast no longer covers the wizard. Existing users: unchanged.
- **UX-03:** `FirstRunWizard.complete()` refuses a blank name (`markErr` + `#frBizNameErr`, key `val_business_name_required`) and keeps the wizard open. `skip()` is unchanged and stores no default name.
- **UX-04:** `@media(max-width:768px){.bottom-nav{display:flex}}` placed after the `.bottom-nav{display:none}` base rule (the base rule used to override the phone rule). The print rule still hides the bar. The five `.bn-lbl` labels use `data-i18n` (`bn_home`, `bn_sales`, `bn_credit`, `bn_inventory`, `bn_more`).
- **Files:** `index.html` only. **Database:** no change. **i18n:** 6 new keys, EN/FR parity 1358/1358.
- **Rollout note:** `service-worker.js` is unchanged, so no new worker is installed and no update banner appears. The service worker serves `index.html` stale-while-revalidate, so an installed app should pick up the new file on a later open once a fresh copy has been fetched. This has not been tested on a device. A version and cache bump in the next release makes the update explicit.
- **Revert:** UX-04 alone with `git revert 5184d38`.

### 4.3.8 — build 2026.10.01a (cache v131, previous v120 = live production 4.2.7)
- **Status:** merged into `main` (PR #3, merge commit `f156eb6`). Production deployment is pending Netlify credits, so 4.3.8 is not confirmed live. See `engineering/release/RELEASE_HISTORY.md`.
- **Also in this build (carried from earlier work, documented here for the first time):** dashboard Smart Insights (section 11) and WhatsApp PDF receipts opening the native share sheet directly (section 12). The 4.3.0–4.3.6 changes are summarised in `RELEASE_HISTORY.md`; they have no separate entries in this changelog.
- **Fixed (backup restore):** every real backup failed silently after "read started". `BackupValidator.validate()` passed `ValidationService` methods detached, so `this._req` threw inside the FileReader callback. The validators are now called on `ValidationService`; credit invoices are checked on `amount`; a validation or import error is shown as an error (never as success); the warning text no longer claims records "will be skipped" (the merge never skipped any). Backup format and merge-by-id unchanged.
- **Added (payment-method integrity):** one canonical list `PAYMENT_METHODS` (+ `DEPOSIT_METHODS` without Cheque, `isPaymentMethod()`); POS credit deposit and new-invoice deposit get a "Deposit paid with" selector (shown only when deposit > 0, no default, cleared on reset / deposit 0 / customer change); `finalizeCreditSale()` (optional 7th argument `depositMethod`), `saveSale()`, `savePay()`, refunds and expenses validate against the canonical list at the save function, before any write; deposits and repayments audited with method and invoice; credit receipts (screen/print, PDF, WhatsApp text) show the deposit method; missing/unknown stored methods shown as "Not recorded" (never Cash) and reported in the cash-drawer note; payments filter gains Other and Account Credit.
- **Files:** `index.html`, `service-worker.js` (CACHE_VERSION v131), `DEVELOPER.md`.
- **Database:** no schema/IDB version change, no migration, no historical record rewritten.
- **Breaking changes:** a credit sale or new invoice with a deposit now requires choosing the deposit method (intended).

### 4.3.7 — build 2026.09.30f (cache v130)
- **Added:** G1–G4 money controls (section 9); expense "Paid with" field; refund-method screen; three drawer lines (Cash Payments Received, Cash Expenses, Cash Refunds) and a cash-only note; 31 EN/FR strings.
- **Changed:** Expected Cash now counts physical cash only; "Cash Sales Today" in the drawer shows cash kept (change handed back is no longer counted).
- **Files:** `index.html`, `service-worker.js` (CACHE_VERSION v130), `DEVELOPER.md`.
- **Database:** no schema/IDB version change; additive optional fields only; no migration; historical records untouched.
- **Breaking changes:** none. Employees now need Owner approval for overpayments and credit refunds (intended).
- **Release step:** set `PREVIOUS_CACHE_VERSION` to `'v129'` once 4.3.6 is confirmed live, before 4.3.7 is deployed.

## 11. Dashboard Smart Insights (in the 4.3.8 build)

The Dashboard shows an insights feed grouped as **Requires Action** and **Review**. The code is tagged v4.2.9 in `index.html`; it reaches production for the first time with 4.3.8. It is read-only: no new store, no new financial calculation, no new timer.

| Piece | Behaviour |
|---|---|
| `renderInsights()` | Renders into the existing `#insightsFeed` container, positioned after Quick Actions. Keeps at most 6 of the original insights; the "everything looks healthy" fallback line is replaced by the dashboard empty state (`ins_all_good`). **Requires Action** = urgent (danger/warn) original insights + Open loss records. **Review** = the product-activity alerts + the non-urgent original insights. |
| `generateInsights()` | Still the engine for the original insights, and still read by the Collection page (`renderCollInsights`). Two additive markers only: `nav:'overdue'` on the overdue summary and `empty:true` on the fallback line. |
| `generateActionInsights()` | Adds the new alerts. **Open loss records:** `collectLossRecords()` rows with `lossStatus` `'Open'`, shown only when `canViewLossRegister()`. **Review alerts:** products not sold in 30 days, never sold, inactive 6+ months. |
| `computeProductActivityBuckets()` | One pass over products using the existing `computeProductSalesAggregates(null,null)` (cached; invalidated when sales or products change). Buckets are mutually exclusive: never sold → inactive 6+ months → not sold in 30 days. Discontinued products are excluded. "Never sold" waits 30 days from the product's `added` date (a future or missing/unparseable `added` is handled as documented in the code). `_isoMonthsAgo()` clamps month-end dates. |
| Tap-through | `INSIGHT_NAV` maps a card to a page: overdue → Collection; loss → Inventory Loss Register filtered to Open; the three product alerts → Products with the new **Sales activity** filter (`#prodActivitySel`, applied in `filterProducts()` via `computeProductActivityBuckets().byId`). `openInsight()` and `_insightNavAllowed()` use `NAV_PERMISSION_MAP` and `Auth.can()`: a card is a link only for users who may open the target page. |
| Filter reset | `loadProducts()` clears the Sales activity filter on a normal visit to Products; `_openProductsActivity()` calls `go('products')` first and sets the filter after. |
| Dashboard chart | The Monthly Cash Sales card is hidden from the UI only (`#dashMonthlyCashCard`). Its canvas, the `drawAllCharts()` block and its data are untouched; remove the `display:none` and the grid override on that row to restore it. |

Notes: `loadProducts` and `drawAllCharts` are protected functions; `loadProducts` differs from 4.2.7 only by the filter reset above. Regression coverage lives in `tests/suites-4.3.x/` (`fin_r436_r435_r434_ins_qa13.py`, `fin_r436_r435_r434_grace13.py`); see `tests/README.md` for the known limitations of those scripts.

## 12. WhatsApp PDF receipt sharing (in the 4.3.8 build)

- **Now:** `shareReceiptPdfWhatsApp()` calls `_shareReceiptPdfFile(sale, type)` directly for every sale (linked customer with a phone number, customer without one, walk-in). There is no Bizora number-entry step. The call is made synchronously from the tap so the browser keeps the user activation that sharing needs.
- **How the share works:** `_shareReceiptPdfFile()` builds the PDF with `_generateReceiptPdfBlob()` and, when `navigator.canShare({files})` and `navigator.share` are available, opens the **native share sheet**; the recipient is chosen inside WhatsApp (the Web Share API cannot address a file to a phone number). Closing the sheet is not an error and the sale stands. If the platform cannot share files, the PDF is downloaded and a warning toast (`wa_pdf_unsupported`) says so.
- **Before (4.2.7):** a customer with a valid stored phone number went straight to sharing; every other sale first asked for a number in the `#mWaShare` prompt (`_waShareMode='pdf'`).
- **Unchanged:** the **text** receipt (`shareReceiptWhatsApp()` → `wa.me`, with the `#mWaShare` prompt for unknown numbers) still behaves as before. `confirmWaShareNumber()` still contains a `_waShareMode==='pdf'` branch, but no code path sets that mode any more, so it is not reached.
- `shareReceiptPdfWhatsApp` and `_generateReceiptPdfBlob` are protected functions; `shareReceiptPdfWhatsApp` differs from 4.2.7 as described here.
