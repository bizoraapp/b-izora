# Bizora 4.3.7 — Money Controls: Implementation Report (for PM review)

**Status:** CANDIDATE — NOT DEPLOYED. `/ship` not run. Production untouched.
**Baseline:** 4.3.6, build 2026.09.30e, cache v129.
**Candidate:** 4.3.7, build 2026.09.30f, cache v130. Database schema v8 (unchanged).
**Checkpoint:** git tag `checkpoint-4.3.6-pre-4.3.7` (commit `b4b757d`). The clean tree was confirmed before any edit.
**Work branch:** `release/4.3.7-money-controls`, commit `10a9760`. `main` still points at 4.3.6.
**Candidate zip:** `bizora-candidate-4_3_7.zip`, 16 files. SHA-256 `512b88c371e9d7bb44ee1c148a2351ac9914dc7c5840dfd3bc4c9c4a0b5d8637`.

---

## A. Files changed

| File | Change |
|---|---|
| `index.html` | G1–G4 logic, one new modal (refund), one new expense field, three new drawer lines + note, 31 EN + 31 FR strings, APP_VERSION/BUILD_NUMBER |
| `service-worker.js` | `CACHE_VERSION` v129 → v130 (only line changed) |
| `DEVELOPER.md` | Header version; new §9 Money Controls; new §10 Changelog |

Diff: 3 files, +356 / −31 lines. No other file touched.

## B. Functions changed

| Function | Why |
|---|---|
| `savePay()` | G1: invoice/amount validation; overpayment confirm (Owner) or single-use Owner approval (employees); audit entry for every overpayment; method stored on the credit entry; uses the existing `_salesById` index |
| `resetPayForm()` | G1: a fresh payment form never inherits an overpayment approval |
| `addCreditEntry()` | Optional 6th argument `method`. It is stored only when given, so existing callers write the identical record shape |
| `promptRefundCredit()` | G2: now only the screen. It checks permission, shows the credit and asks for the refund method |
| `confirmRefundCredit()` *(new)* | G2: validates the method and re-checks that the credit did not change since the screen opened |
| `refundAccountCredit()` *(new)* | G2: the operation boundary. It checks permission, amount, method and Owner approval, then writes and audits |
| `OwnerApproval` (`bindKey`, `requestOwnerActionApproval`, `submitPriceApproval`) | Two new approval kinds, `overpay` and `creditRefund`, reusing the existing single-use slot. The existing kinds are unchanged |
| `computeDrawerCash()` *(new, read-only)* | G3: the business logic for physical cash. Separated from the UI |
| `renderCashDrawer()` | G3: now display only, using `computeDrawerCash()` |
| `saveCashDrawer()` | G4: Manage Inventory check; invalid values never saved; captures the value before the edit |
| `commitCashDrawerEdit()` *(new)* | G4: one audit entry per finished edit, plus `visibilitychange`/`pagehide` listeners (no timers) |
| `saveExpense()`, `openAddExpense()`, `editExpense()`, `_setExpPayMethod()` *(new)* | G3: expense "Paid with" |
| `_payMethodEn()`, `_payMethodLabel()`, `overpayFigures()`, `refundFigures()` *(new helpers)* | Canonical English method names in the Audit Log, translated names on screen |

Protected functions: **28/28 byte-identical to 4.3.6** (SHA-256). `invBalance`, `custDebt`, `computeExpenseTotals`, `computeNetProfit`, `computeRealizedProfit` and the other source-of-truth functions were not touched. `custCreditBalance` was not touched either.

## C. G1 result: overpayment / extraction path

- **Exact and partial payments are unchanged.** There is no extra step, and they are saved as before.
- **Overpayments by the Owner, or with Access Control off,** show a confirm first: "{amount} is more than the {balance} still owed on {invoice}. {extra} will be kept as account credit…". Nothing is written until the user taps Confirm.
- **Overpayments by an employee** open the Owner password pop-up. The approval is single-use and bound to customer, invoice, amount, balance and method. Nothing is written until the approval matches. A wrong password is logged as `login_failed`. A stale or cancelled approval can never cover a different amount; this was tested with a 25,000 approval against a 90,000 overpayment.
- **Every overpayment is audited** with type `payment`, recording amount, invoice, method, applied part, excess, credit before → after, the user and the approver.
- **New validation:** the invoice must exist, belong to the chosen customer and not be cancelled. `Infinity` and non-numeric amounts are refused. 4.3.6 accepted `Infinity`.
- **Extraction path closed:** an employee can no longer create withdrawable credit without the Owner, and cannot refund it either (G2).

## D. G2 result: account-credit refund

- **Permission:** Manage Customers, the existing permission for the customer profile where the Refund button lives. Cashiers and Storekeepers are refused by default. Sales Reps and Supervisors also need the Owner password.
- **Operation boundary:** `refundAccountCredit()` enforces every rule itself. Calling it directly from the console gets exactly the same checks. Refused attempts write nothing and are audited as `security`.
- **Rules:** amount > 0 and ≤ current credit. The method must be one of cash, mobile money, bank transfer, cheque, card or other. The refund screen has no preselected method, so the person must choose one.
- **Audit:** customer, amount, method, user, time, credit before → after, and the approver when there is one.
- **What stays open:** the low-level `addCreditEntry()` / `S.add()` can still be called from the browser console. That is a limit of a client-only app, not something this release can close. See J.

## E. G3 result: physical cash

**Expected Cash =** Opening
**+** cash kept from POS cash sales (paid − change)
**+** cash payments received (method `cash`, including deposits)
**+** cash overpayments kept as account credit
**−** cash expenses
**−** account credit refunded in cash.

| Transaction | Effect on Expected Cash (tested) |
|---|---|
| Cash sale 70,000, customer hands over 75,000, change 5,000 | +70,000 |
| Mobile Money / bank / card / cheque sale or payment | 0 |
| Cash payment on a credit invoice | + amount |
| Credit sale, no deposit | 0 |
| Credit sale with cash deposit | + deposit |
| Cash expense / non-cash expense | − amount / 0 |
| Cash refund / non-cash refund | − amount / 0 |
| Account credit created by a Mobile Money overpayment | 0 |
| Applying account credit to an invoice | 0 |

- **Required fixture passes:** opening 10,000 + cash sale 70,000 + MoMo sale 30,000 + cash payment 20,000 − cash expense 5,000 − cash refund 10,000 = **FCFA 85,000**, both on screen and in the logic. The 4.3.6 formula shows **105,000** for the same day.
- **Screen changes:** three new lines (Cash Payments Received, Cash Expenses, Cash Refunds) and a one-line note saying the figure counts physical cash only. The existing cards are unchanged, except that "Cash Sales Today" now shows cash kept, not cash handed over.
- **Historical data:** nothing was rewritten. Records saved before 4.3.7 carry no method, and they are **not guessed**. They are left out of Expected Cash, and the screen says "N record(s) from today have no payment method… not included." This only matters on upgrade day, because the drawer shows today only.

## F. G4 result: drawer edit audit

- **Permission:** Manage Inventory, the existing permission described as "Adjust stock levels and the daily cash drawer". It is enforced inside `saveCashDrawer()`. Cashiers and Sales Reps are refused, and the drawer is unchanged.
- **Autosave is unchanged:** the fields still save on every keystroke, so a count is not lost if the phone dies.
- **One audit entry per finished edit:** typing "84500" writes one entry, not five. For example: `Cash drawer closing count changed for 2026-09-30: (blank) → FCFA 84,500`. The entry records previous and new value, user, date and time.
- **Unfinished edits are still logged:** if the edit is still open when the app is hidden or closed, it is logged then.
- **Invalid values** (negative, not a number) are never saved. The field is restored and the user sees a message.
- **Owner corrections** are never blocked, only logged. The drawer record keeps its `{opening, closing}` shape, and there is no second history store.

## G. Data safety

- **No migration.** The IndexedDB version stays v8. There are two new optional fields, written only when known: `creditLedger[].method` and `expenses[].payMethod`. The drawer shape is unchanged.
- **4.3.6 → 4.3.7 upgrade test** (real service-worker update on the same origin):
  - All 24 integrity checks came out identical: 15 data stores, debts, credit balances, totals, stock, settings, drawer and access control.
  - The update waits for the user to accept it.
  - An offline relaunch after the update shows the same data.
- **Older expenses:** editing one shows "Not recorded". Saving without choosing a method keeps it without one.
- **Backup/restore:** the new fields are exported and restored (see the note in J).

## H. Tests

| Suite | Result |
|---|---|
| **4.3.7 focused (new, `t437.py`)**: G1, G2, G3, G4, role matrix, direct-call security, i18n FR | **98/98 pass.** Run 6 times: one early harness flake (confirm clicked before it opened) was fixed, and the last 5 runs are all green |
| Role matrix: Owner, Access Control off, Cashier, Storekeeper, Supervisor, Sales Rep | Included above |
| Offline (`offline437.py`): approvals, refund and drawer edit fully offline, persisted after offline reload | **7/7** |
| Upgrade 4.3.6 → 4.3.7 (`upgrade437.py`) | **24/24 data checks identical**, no JS errors |
| Backup/restore round trip of new fields (`backup437.py`) | **3/3** (see J for the pre-existing restore bug) |
| Existing 4.3.x regression: t436, t435, t434, t433, pa_test, pa_ui, grace, ins_qa, extra, offline | **390 checks pass, 0 fail.** extra/pa_ui/offline print pass/fail values instead of PASS lines; I read them and all are correct |
| In-app DevSuite (functional + edge cases + validator) | 4.3.7 = 4.3.6: 30 pass, the same 1 known fail and 1 warning as before |
| `node --check` | All app script blocks OK. Block 0 fails in both 4.3.6 and 4.3.7: it is the known false alarm from a `<script>` tag inside an HTML comment |
| Protected-function hashes | 28/28 unchanged vs 4.3.6 |
| EN/FR parity | 1345/1345 (+31 keys each), none missing |
| Diff confinement | Every change is inside G1–G4 code or markup, version constants or docs |
| `qa/run.js` | Not present in this repo. Equivalent checks were run individually (above) |

**Performance** (390 px viewport, CPU throttled 4× to stand in for a low-end Android; medians):

| Transactions | Drawer render 4.3.6 → 4.3.7 | Record cash sale | Record payment |
|---|---|---|---|
| 1,000 | 0.2 → 0.4 ms | 66 → 61 ms | 89 → 101 ms |
| 10,000 | 1.2 → 3.5 ms | 655 → 651 ms | 709 → 598 ms |
| 50,000 | 5.6 → 9.9 ms | 2,807 → 2,835 ms | 3,743 → 3,737 ms |
| 100,000 | 3–7 → 10–16 ms | ~5.7–5.9 s → ~5.8–6.3 s | ~7.2–7.4 s → ~7.4–7.5 s |

- **Complexity:** the drawer makes one pass over each of five stores (posSales, sales, payments, creditLedger, expenses), O(N), today's records only.
- **Resources:** no new timers, polling, dependencies or stores. Memory use is a single result object.
- **Where time goes at 100k:** the multi-second sale and payment times already exist in 4.3.6, mostly from the known notifications scan. At 100k, 4.3.7 adds about 5–10 ms to the drawer render. The payment-path differences at 100k (+50 to +290 ms) sit inside the run-to-run spread I measured and could not be separated from noise.

## I. Diff discipline

- **Scope:** changes are confined to the approved 4.3.7 scope.
- **Not touched:** reports, receipts, inventory logic, licensing, sync, subscriptions, the UI outside the drawer card, the expense form field and the refund modal, and the other permissions.
- **One addition beyond the plan:** the `Infinity` / wrong-invoice validation in `savePay()`. It is part of "validate payment amount against the invoice/customer balance" (directive §5).
- **Dropped per directive §8:** the plan's per-day `edits[]` history inside `cashDrawer`, and the employee lock on opening cash. G4 is traceability only, using the existing Audit Log.

## J. Remaining risks / not verified

1. **Release step:** set `PREVIOUS_CACHE_VERSION = 'v129'` once 4.3.6 is confirmed live, before deploying 4.3.7. It is currently `v120`, per the rule that it pins the last live cache. If it is left at v120, the 4.3.6 rollback cache is deleted on update (seen in the upgrade test).
2. **Real-device testing is not done.** Testing so far used emulated 390 px and a 4× CPU throttle. Your Android QA is still a release gate.
3. **POS and invoice-form deposits are always saved as `cash`.** This is existing behavior: there is no method choice for deposits. A deposit actually paid by Mobile Money will overstate Expected Cash. It is reported here, not fixed (scope).
4. **Console writes:** the browser console can still call low-level storage functions. The UI and operation-level functions are protected; a client-only app cannot stop raw storage writes. Belongs with the separate security candidate.
5. **Upgrade-day records:** records from the upgrade day saved before 4.3.7 are excluded from Expected Cash. The screen shows this, and it clears the next day.
6. **"Collections Received" label:** the card still shows all methods, as an informational figure. Next to "Cash Payments Received" it could confuse some users. It is worth a UX look, but was not changed.

### Separately found defect (pre-existing, NOT fixed, not a G1–G4 blocker)

**HIGH — JSON backup restore does not work in production 4.2.7, 4.3.6 or 4.3.7.**
- **Where it breaks:** `BackupValidator.validate()` calls `ValidationService.validateCustomer`, `validateSale` and `validateProduct` as detached functions, so `this` is undefined. Any backup that contains customers, sales or products throws `Cannot read properties of undefined (reading '_req')`.
- **What the user sees:** "read started", then nothing. There is no confirm dialog, no data imported and no error message.
- **Reproduced:** in all three builds with the real `handleFile()` path.
- **Suggested fix:** a one-line binding fix. It needs its own small candidate (4.3.8) because it touches backup/restore, which is outside this scope.
