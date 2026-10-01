# Bizora — bug history and lessons

Every significant defect fixed so far: **what happened, why, how it was fixed, and the rule it left behind**. Before changing an area, read its section. Most of these bugs came back in a new form at least once.

Sources: the project bug logs (PWA conversion → 3.6.1, the July 2026 session, the stabilisation and QA pass, the license-security session), the Engineering Knowledge Base (3.8.7) and the 4.3.x release reports. IDs are kept from the original logs, so they repeat across logs (each log restarted at BUG-01); the prefix in brackets says which log.

> **Public repository.** Security fixes that are not yet live in production are described here only at the level of "what kind of control was added". Exploit details and open findings live in the private project tracker. Keep it that way when you add entries.

---

## 1. Data integrity and money (highest impact)

| ID | Version | What happened | Root cause | Fix | Lesson / rule |
|---|---|---|---|---|---|
| [QA] #14 | stabilisation pass | **Backups silently left out half the data**: expenses, employees, licences, stock movements, reconciliations, reminders, notifications, suppliers | `exportBackup()` listed stores by hand; new stores were never added | All stores added to export **and** restore, same merge-by-id | Every new store or settings key must be added to backup, restore **and** the rehydration list. Test with a real export → fresh profile → restore |
| 4.3.8-A | 4.3.8 | **Every restore failed silently** after "read started" (also in live 4.2.7) | `BackupValidator` passed `ValidationService.validateX` as a detached function, so `this` was undefined and it threw inside a FileReader callback that nothing caught; the sale validator also read `total` while invoices use `amount` | Call the validators as methods; check invoices on `amount`; try/catch with a visible "Restore failed" error; plain-text warning | Never pass an object's method detached. Wrap async callbacks in try/catch and show failures; never report success without checking. **Same pattern still dormant** in `createEntityService` and `DatabaseHealthManager.runFullCheck` (BZ-016) |
| 4.3.8-B | 4.3.8 | **Credit-sale deposits were always recorded as cash**, even when paid by Mobile Money, inflating Expected Cash | `finalizeCreditSale()` hard-coded `method:'cash'`; the invoice deposit had no method at all | Explicit "Deposit paid with" selector with **no default**, validated against `DEPOSIT_METHODS` inside the save function before any write; method in the audit and on the receipt | Never default, guess or convert a payment method. `posSales.type 'cash'` means "paid now", not "physical cash". Old records with no method are shown as "Not recorded", never rewritten |
| 4.3.7 G1–G4 | 4.3.7 | Money could leave the business without a trace: overpayments, account-credit refunds and drawer edits had no approval or audit; Expected Cash counted non-cash money | Controls were never designed for these paths | Owner approval for overpayment and refund, a required refund method, an audit entry for every drawer edit, and Expected Cash from physical cash only (`computeDrawerCash`) | Every money-affecting action needs a permission check inside the function, an audit entry (who, amount, method, before→after), and, for employees, Owner approval where money can leave |
| [QA] #7 | stabilisation pass | **Reports showed a customer as fully paid while a newer invoice was unpaid** | Outstanding = invoices in period − payments in period, even when those payments were for older invoices | Sum `invBalance()` per invoice; Paid derived from it, so Invoiced = Paid + Outstanding always | Never re-derive balances: use `invBalance` / `custDebt`. Prove a formula with concrete numbers before trusting it |
| [QA] #11 | stabilisation pass | **Loss Register counted the same shortage twice** (Daily Check, then Monthly Reconciliation) | Reconciliation is read-only, so an uncorrected shortage is found again | Derived, never-stored classifier (New / Previously Detected / Resolved); only "Previously Detected" is excluded from the total | Fix double counting with read-only derivation, never by deleting or editing history |
| [QA] #13 | stabilisation pass | **Deleting a product erased its historical loss values and history** | `delProduct()` hard-deleted with no history check | Block deletion when movements, reconciliations or stock exist; offer "Discontinued" | Deletion must check dependants. Prefer a status over deletion |
| [QA] #12 | stabilisation pass | **Double taps created duplicate sales, payments, expenses and products** on slow phones | No duplicate-submit guard on the five core saves | Disable the save button just before the commit (not during validation); re-enable on every form open/reset; all three `checkoutPos` commit branches covered | Every save path needs a duplicate-submit guard. Test with rapid double taps |
| [Jul] BUG-05 | July 2026 | Cash-drawer closing amount saved as text ("10,000") | Raw input value stored without parsing | Parse to a number; keep "empty" distinct from 0 | Every number field is parsed before saving. `parseFloat` is wrapped app-wide to strip commas; don't rely on it for new storage code without checking |
| [3.6] BUG-04 | 3.2.1 | Selling price ≥ 1,000 gave the wrong discount | `parseFloat('4,500')` = 4 (comma-formatted input) | `cleanNum()` before parsing (later a global `parseFloat` wrapper) | Formatted inputs must be cleaned before parsing |
| [3.6] BUG-05/06/07 | 3.3.0 | Multi-unit selling price compared per unit vs line total; markups blocked; "-FCFA -4,000" display | Mixed units, a 0–100 % clamp, sign handling | Line totals throughout; negative discount = markup; signed display "Total Markup" | Keep one unit convention per screen; test quantity > 1 |
| [3.6] BUG-01 | 3.0.1 | "Reset database" reported success but data came back | `deleteDatabase()` blocked by the app's own open connection | Clear each store explicitly, then close and delete, with real error handling | Never assume an IndexedDB operation succeeded; await and check it |
| [3.6] BUG-02 | 3.0.2 | **Fresh installs showed fake demo customers** | `initApp()` seeded demo data whenever stores were empty | Automatic seeding removed | No automatic test/demo data in production paths |
| 4.3.3 | 4.3.3 | Invoices could be changed in ways that broke the money trail (total below amount paid, POS-linked invoices drifting on an unchanged save) | Invoice total read from a hidden field; no payment guard | Total computed from rows; total never below the amount paid (everyone, Owner included); Owner approval for employee amount, cancellation and customer changes; old→new price audited | Derive totals from the source rows, never from a hidden field |
| 4.3.4 | 4.3.4 | Duplicate product names (by case or spacing) split stock and reports | No uniqueness check on add, rename or CSV import | Block duplicates (trim, collapse spaces, case-insensitive) on all three paths; historical duplicates reported, never merged | New validation applies to new data only; history is never auto-merged |

## 2. Dates and time

| ID | What happened | Root cause | Fix | Rule |
|---|---|---|---|---|
| [Jul] BUG-02 | **Every chart was off by one month** in Cameroon | `.toISOString()` converts local midnight to UTC (the previous day in UTC+1), so the month key shifted | 13 places switched to local date parts (`localISODate()`) | **Never** build a date key with `.toISOString()`. The post-edit hook warns on new occurrences |
| [Jul] BUG-01 | **Trial stuck at 30 days** | `trialInfo` was saved but missing from the settings **rehydration list**, so it looked new on every reload | Key added; elapsed time from an absolute timestamp; high-water mark against clock rollback | **Any new persisted settings key must be added to the rehydration list** |
| [Jul] BUG-03 | Monthly chart showed only the current month | Fixed 6-month window, no history | Range from the earliest record to now | Charts derive their range from data |
| BIZ-BUG-001/002 | Licence "days left" reads one day high (`Math.ceil`); a −0 boundary case | Rounding | **Intentionally not changed** (reviewed twice) | Change only with an explicit decision; `daysLeft()` and `status()` change together |

## 3. Security and access control

| ID | What happened | Fix | Rule |
|---|---|---|---|
| SEC-01/02 (BIZ-SEC-001/002) | `resetEmployeePassword()` and `saveRolePermissionsForm()` trusted their caller; only the button was gated | Owner check inside each function | **Authorization lives inside the function that writes**, never only in the UI. Copy the `requireDeletePermission()` pattern |
| 4.3.1 | Restricted pages were reachable through links that called `go()` directly (Help, licence badge, Getting Started) | Permission check inside `go()` (`canOpenPage`); export, End-of-Day and Backup guards; `viewHelp` permission | Hiding a menu item is not authorization |
| 4.3.2 | Employee price changes at the POS needed no approval | Owner approval for every non-owner selling-price change, enforced at input **and** at checkout | Enforce at the save, not only in the form |
| 4.3.5 | An Owner account-recovery weakness on the lock screen (details in the private tracker) | Recovery hardened; unverified recoveries are logged and attributed as such | Recovery flows are part of the security model. Any "reset" path needs the same scrutiny as login |
| 4.3.6 | Employees could sell beyond a customer's credit limit and change limits freely | Owner approval for over-limit credit and for raising/removing limits or unblocking; lowering and blocking always audited; approvals single-use and bound to the exact action | Approvals are single-use, bound to customer/invoice/amount/method, consumed only on a successful save, and cleared when the context changes |
| [lic] BUG-01/02/03 | Licence and trial records could be altered on the device; `License.guard()` was missing from five write functions | Signature re-verified on every load; trial checksum with self-heal to "exhausted"; guard added to all write paths | Client-side checks raise the bar but are not absolute. Every write path calls `License.guard()` |
| SEC-04 | CSV exports could carry spreadsheet formulas | `csvSafe()` neutralises a leading `= + - @` | Every CSV cell goes through `csvSafe()` |
| SEC-03, SEC-05 | Developer Suite gated by a password in the client source; unencrypted backups | **Open, product decisions D2/D3** | Hashing a client-side secret is not a fix |

## 4. Performance (low-end Android)

| ID | What happened | Root cause | Fix | Rule |
|---|---|---|---|---|
| PERF-01…10 (3.3–3.4) | Customers, Ledger, Sales History, Payments, Reports, Collection and Calendar froze with real data | Full-array `.find()`/`.filter()` per row, even inside sort comparators, although indexes existed | Use `_salesByCid`, `_paymentsByCid`, `_custById`, `_salesById`, `_paymentsByInvId` | **Never scan a whole store per row.** Reuse the indexes. Invalidate them through the `S` side effects |
| PERF-07 | Every sortable table recomputed keys n·log n times | Key function called inside the comparator | Decorate-sort-undecorate in `applySorting()` | Compute expensive keys once |
| PERF-11/12 | Financial Summary rendered twice per checkout; monthly series computed twice | Two watched keys written back-to-back; table and chart both computing | Debounced render; series computed once and shared | Coalesce reactive renders |
| [QA] #2 | Product Analytics re-scanned all sales up to 8 times | No cache | Cache by date range, invalidated by the `S` write hooks | Cache derived data, with invalidation tied to writes |
| [QA] #2a | That cache's `let` was referenced by `S.set()` before its declaration line (temporal dead zone) | Declaration order | Declaration moved above `S` | New top-level `let`/`const` used by early code must be declared above it |
| [QA] #3 | Boot rebuilt every dropdown | Redundant call | Removed after proving every page builds its own | Prove a call is redundant before removing it |
| persistence | `S.set()` on a single record rewrote the whole store (≈ 88 s at 100k sales) | O(N) clear + rewrite | `S.add` / `S.update` / `S.remove` | Single-record writes use the single-record APIs. `S.update` still lacks the dashboard-redraw side effect (open) |
| BZ-009 (open) | Recording a sale takes several seconds at 100k transactions | Notifications scan inside the save path | Not yet fixed | Measure at 1k / 10k / 50k / 100k before claiming speed |

## 5. Android rendering

| ID | What happened | Root cause | Fix | Rule |
|---|---|---|---|---|
| [QA] #1 | Blur, launcher visible through the app, freezes on Samsung S22 Ultra and Xiaomi | Stacked `backdrop-filter` and a fixed background crash Adreno/Mali GPU compositors | Platform detection before first paint; `html[data-platform="android"]` disables blur, animation and fixed backgrounds | No `backdrop-filter`, heavy effects or fixed backgrounds outside that override. Diagnose with `?diag=1` and `?lowfx=1` |
| [Jul] BUG-04 | Sidebar menu items unreachable on short screens | `min-height:100vh` on a fixed flex container | `height:100vh`, a scrollable list with `min-height:0` | — |

## 6. Translation (EN / FR)

| ID | What happened | Fix | Rule |
|---|---|---|---|
| i18n-01 ([lic] BUG-04) | A tooltip in a dynamically rendered list stayed English | `t()` at render time instead of `data-i18n-title` | `data-i18n*` only works on static markup (see `I18N.md`) |
| 4.1.5 | Three French typography defects | Fixed (non-breaking spaces, apostrophes) | Follow the typography table in `I18N.md` |
| 4.2.x | Hundreds of hard-coded strings | Phases 2A–2I; full EN/FR parity | Parity is checked automatically; stored values stay English |
| `_pdfEsc` (open) | Curly apostrophe prints as `?` in PDF receipts | Deferred | Separate approved change only |

## 7. UI and consistency

| ID | What happened | Fix |
|---|---|---|
| [Jul] BUG-06 | 30 dashboard KPI cards with duplicates | Reduced to 16 unique cards |
| [Jul] BUG-07 | Card styled with an undefined CSS class | Mapped to an existing token |
| [3.6] BUG-09 | Three different version numbers in the UI | Everything reads `APP_VERSION` |
| [QA] #4/#5/#6/#8 | Missing empty state; no confirmation on Reject Adjustment; analytics excluding discontinued stock; misleading chart title | Each aligned with the existing app convention, which had been checked in 4 places |
| BIZ-REPORT-001 | Three Sales Analytics charts ignored the period filter | Use `getReportPeriodPredicate()` |

## 8. Deployment

| ID | What happened | Fix / rule |
|---|---|---|
| INFRA-01 | 404 at the site root | The entry file must be `index.html` |
| INFRA-02 | Site behind a Netlify password wall | Visitor password protection disabled |
| INFRA-03 | Phone-made ZIPs nested files in a folder | Build ZIPs with files at the root (`unzip -l` to check). Now replaced by Git → Netlify |
| 2026-10 setup | The whole repository root was publicly served (docs, tooling) | `netlify.toml` publishes only an allowlist into `dist/` |
| Cache chain | Candidates built but not deployed made `PREVIOUS_CACHE_VERSION` ambiguous | `PREVIOUS_CACHE_VERSION` = the cache **live right now**, checked on the live `service-worker.js` before release |

## 9. Process lessons (how bugs were missed or caught)

1. **Grep alone gives false conclusions.** Findings were reported as open after they had been fixed, and code paths were missed. The 4.3.8 payment-method investigation missed `openReverseSale` → `reversePosSale`. Trace every caller and confirm in a real browser.
2. **Test with real exports and real flows.** The restore bug survived because tests built synthetic backups. The QA suites now export from the running app.
3. **Test harness traps.** In Playwright:
   - modals hide with opacity and `.on`, so check `classList.contains('on')`;
   - toasts block clicks;
   - wait for `mConfirm` to be `.on` before confirming;
   - pass one argument to `page.evaluate` and destructure it;
   - select the real customer option before saving;
   - running about 10 browsers in parallel causes timing failures, so run release suites sequentially.
4. **A test changed for a new rule must say so.** In 4.3.8, one 4.3.7 test had to select Cash for the deposit. It was kept as a separate adapted file, with the original preserved and the change reported.
5. **"Wizard doesn't appear" is saved state, not a bug.** Check with `?devreset=1` first.
6. **When a mistake is found mid-change, go back to the checkpoint** and redo it; don't patch on top.
7. **Report exact counts** ("97/97", "28/28 protected"), never "all tests pass".
