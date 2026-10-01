# Bizora 4.3.8 — Backup Restore + Payment-Method Integrity: Implementation Report

**Status:** CANDIDATE — NOT DEPLOYED, NOT MERGED, `/ship` not run.
**Open release gate:** real-Android validation (section 7) has not been done. It needs your phone.

## 1. Repository

| Item | Value |
|---|---|
| Branch | `release/4.3.8`, created from the 4.3.7 candidate |
| Base commit | `10a9760` (4.3.7), tagged `checkpoint-4.3.7-pre-4.3.8` |
| 4.3.8 commit | `09dc308` |
| Working tree | clean |
| `main` / `release/4.3.7-money-controls` | untouched (`b4b757d` / `10a9760`) |
| Files changed | `index.html`, `service-worker.js` (one line), `DEVELOPER.md` |
| Files not changed | `manifest.json`, `offline.html`, `icons/*` |
| Migration | **none**: `IDB_VERSION` stays 8, no schema change, no historical record rewritten |

**Versions**
- Version: **4.3.8**, build **2026.10.01a**.
- `CACHE_VERSION` **v131**.
- `PREVIOUS_CACHE_VERSION` **v120**, unchanged. The live site's service worker (`bizora-cm.netlify.app`) still reports **v120 (4.2.7)**, so neither 4.3.6 nor 4.3.7 has been deployed. Keeping v120 preserves the real rollback chain: after updating, the test device held `v120` + `v131`.
- If a different version goes live before 4.3.8, this value must be updated to match.

**Candidate zip:** `bizora-candidate-4_3_8.zip`, 16 files, SHA-256 `3423f6ea299a17a120dfb463b73bda20e90a6629d8993b45fd3f2d7a3194e9fd`.

## 2. Backup restore (Part A)

- **The failure (reproduced with a real export from the app):**
  - Restore shows "read started", then nothing happens.
  - A page error `Cannot read properties of undefined (reading '_req')` is thrown.
  - No confirmation is shown and nothing is imported.
  - The same failure occurs in production 4.2.7, 4.3.6 and 4.3.7.
- **Root cause:** `SecurityManager.BackupValidator.validate()` passes `ValidationService.validateCustomer`, `validateSale` and `validateProduct` as detached functions.
  - Those methods use `this._req`, so `this` is undefined and they throw on the first customer.
  - The throw happens inside the FileReader `onload` callback, where nothing catches it, so the user sees nothing.
- **Fix (restore path only):**
  1. The validators are now called on `ValidationService`.
  2. Invoices are checked using their real total field `amount`. The shared sale validator reads `total`, which would otherwise have flagged every real invoice.
  3. A validation crash or a failure part-way through the import shows *"Restore failed: … A recovery point was saved before the import started."* It is logged, and success is never reported.
  4. The confirm dialog is plain text, so the HTML tags it contained were printed literally; they are replaced with plain text.
  5. The warning wrongly said incomplete records "will be skipped". The merge never skipped any, and that behaviour is kept; the text now says they will still be imported as they are.
- **What stays the same:** the backup format, merge-by-id, which stores are restored and how, and the pre-import recovery point.
- **Compatibility:**
  - Backups exported by **production 4.2.7**, by **4.3.7** and by **4.3.8** all restore into 4.3.8 with every store, debt, credit balance, cash-drawer figure and payment method identical.
  - A 4.2.7 payment that has no method is still method-less after restore.
- **Same bug elsewhere, not fixed (outside the restore path):**
  - The unused `createEntityService` layer.
  - The diagnostics `runFullCheck` record check.
  - Neither is reachable from normal workflows. They are reported here for a later candidate.

## 3. Payment methods (Part B)

- **B1 One list of payment methods.** `PAYMENT_METHODS = cash, mobile-money, bank-transfer, cheque, card, other`, defined once next to the method labels.
  - `DEPOSIT_METHODS` is derived from it and is the same list without Cheque.
  - `isPaymentMethod()` accepts only an exact string from the list, so `'Cash'`, objects and arrays are refused.
  - The 4.3.7 separate refund list is removed; refunds and expenses now use the one list.
  - `'account credit'` is recognised when reading history but can never be chosen for new money.
- **B2 POS credit deposit.**
  - A "Deposit paid with *" selector appears only when the deposit is above 0. It has **no default** and offers Cash, Mobile Money, Bank Transfer, Card and Other.
  - `checkoutPos()` asks for the method before any credit-limit approval is requested.
  - `finalizeCreditSale()` reads the method at save time: an optional 7th argument for direct callers, otherwise the visible selector. A hidden selector is never trusted.
  - A missing or invalid method is refused and audited **before** the approval is used and before any sale, payment or stock write.
  - The hard-coded `method:'cash'` is removed.
- **B3 Invoice deposit.** The same selector and rules in `saveSale()` for new invoices. The deposit date behaviour is unchanged (it stays the invoice date).
- **B4 Record Payment.** `savePay()` checks the method against the list before any approval or write. A refusal is audited as `security`.
- **B5 Audit.**
  - POS deposit (new entry): `Deposit FCFA 3,000 (Mobile Money) from Amina on INV-…`, recorded under the acting user.
  - Invoice deposit: `Deposit FCFA 2,500 (Bank Transfer) from Bello on INV-…`.
  - Repayment: `Payment FCFA 1,000 (Cash) from Bello on INV-…`.
- **B6 Overpayment and refund.** The 4.3.7 behaviour is kept: the method is retained and the approval rules and binding are unchanged. The only change is that the refund check uses the canonical list.
- **B7 Expected Cash.** `computeDrawerCash()` has the same calculation. Deposits now reach it with their real method.
- **B8 History.** Missing or empty methods display as **"Not recorded"**, and non-standard ones as **"Not recorded (value)"**. This applies to:
  - the payments list
  - the payment receipt and customer statement
  - Sales History
  - global search
  - the POS receipt and PDF

  They are never shown as Cash, and stored values are never changed.
- **B9 Drawer note.** Missing or unrecognised methods on today's payments, POS sales, expenses and credit-ledger entries are excluded and counted. The note reads: "N record(s) from today were left out because their payment method is missing or not recognised." This runs in the same single pass, with no new scan.
- **B10 Payments filter.** The method filter gains "Other" and "Account Credit".
- **B11 Receipts.**
  - The credit receipt shows "Deposit paid with: Mobile Money" on screen and print, in the PDF and in the WhatsApp text.
  - With no deposit there is no method line.
  - The protected `_generateReceiptPdfBlob` is untouched; only its line builder `_buildReceiptPdfLines` changed.

## 4. Security (tested)

| Attempt | Result |
|---|---|
| Direct `finalizeCreditSale` with a missing, empty, `'undefined'`, `'cash2'`, `'bitcoin'`, `'Cash'`, `'cheque'`, 500-character, object (`toString` → `'cash'`), array, `null` or number deposit method (12 variants) | Refused and audited; no sale, payment, stock or credit change |
| Deposit amount set without the UI (selector hidden), even with a value forced into the selector | Refused, for both POS and invoice |
| Invalid method injected into Record Payment (`bitcoin`, `Cash`, empty, `account credit`) | Refused, no payment, audited |
| Refund with `cash2` | Refused, credit unchanged |
| Stale method: reset sale, deposit → 0 → new deposit, customer change, reopened invoice form, next sale after a completed one | Cleared every time; the method must be chosen again |
| Over-limit cashier sale with a deposit but no method | Asked for the method first; **no** approval requested |
| After a refusal | The next valid call saves exactly one record |
| 4.3.6 credit-limit approval | Still requested, still single-use, and the approver is recorded |

No new role or permission was added. All 4.3.7 approval keys are unchanged. The 28 protected functions are byte-identical to 4.3.7.

## 5. Tests (exact counts)

| Suite | Result |
|---|---|
| **New 4.3.8 suite** (`t438.py`): acceptance A–D + Other, zero deposit, 12 invalid direct calls, stale state, cashier approval, invoice deposits, 6 repayment methods, overpayment, refund, account credit, historical methods, FR, 360 px | **97/97** |
| **Backup:** real export → restore into a fresh profile (every store, methods, drawer, debts, credit), re-restore without duplicates, 4 malformed files, injected part-way failure, 4.3.8 deposits in the file | **25/25** |
| Backup compatibility: 4.2.7 and 4.3.7 backups → 4.3.8 | **4/4** |
| Offline: MoMo deposit + cash repayment, audit, close/reopen, export, restore, all without network | **6/6** |
| 4.3.7 money-control suite | **98/98**, with **one test adapted**: the "credit sale with 1,500 cash deposit" test now selects Cash, as 4.3.8 requires. Its expectation (+1,500) is unchanged; the original file is kept |
| 4.3.x regression (4.3.6, 4.3.5, 4.3.4, 4.3.3, 4.3.2, Smart Insights, grace period) | **390/390**, plus 3 value-reporting suites (workflows/roles/FR, real typing/Enter/Escape/360 px, offline upgrade): all correct, no errors |
| In-app self-tests | Same as 4.3.6: 30 pass, the same 1 known fail and 1 warning |
| Upgrade 4.3.7 → 4.3.8 | 24/24 data checks identical; the update waits for the user |
| Upgrade **production 4.2.7 → 4.3.8** | 16/16 identical; caches `v120` + `v131`; the credit-limit popup works on migrated data |
| EN/FR | 1352/1352 keys, none missing (+8 new keys, 1 updated) |
| 360 px | POS credit panel and invoice form: no horizontal overflow (screenshots taken) |
| JavaScript errors | none in any suite |
| **Real Android** | **NOT DONE: open gate** |

## 6. Data integrity and performance

- **Data integrity:**
  - No historical payment was rewritten; tested by comparing before and after byte for byte.
  - No duplicate payments were created: exactly one per deposit or payment, and a re-restore adds none.
  - Stock went down by exactly the quantity sold, and refusals made no stock change.
  - Debts and credit balances are identical after restore and upgrade.
  - Non-cash deposits and payments add **0** to Expected Cash.
  - Payment methods survive restore unchanged.
- **Performance** (100,000 transactions, CPU slowed 4×, run alone, 2 runs):

| Path | 4.3.7 | 4.3.8 |
|---|---|---|
| Drawer render | 8–16 ms | 13–16 ms |
| Cash sale | 5.7–5.8 s | 5.4–5.9 s |
| Payment | 7.2 s | 6.9–7.4 s |
| Credit sale with deposit | 6.0–6.1 s | 5.9 s |

  - All differences are within run-to-run noise. The multi-second totals were already there in 4.3.7 (the known notifications scan).
  - The method check itself costs about 50 ns.
  - No new scans, timers, indexes or startup work.

## 7. Real-Android checklist (your QA; required before deploy)

1. Install the 4.3.7 candidate, then upgrade to 4.3.8.
2. Credit sale with a MoMo deposit.
3. Credit sale with a cash deposit.
4. Expected Cash.
5. Receipt.
6. Audit.
7. MoMo repayment.
8. Cash repayment.
9. Cash drawer.
10. Backup export.
11. Backup restore.
12. Close and reopen the app.
13. Offline use.
14. 360 px screen.
15. No freezes, stuck overlays or stale selections.

## 8. Findings not changed (reported, outside scope)

1. **Sale reversals** (`reversePosSale`, and reversal of a paid credit invoice via `delSale`) are Owner-only. They **delete** the sale, and its payments for invoices, rather than recording a refund, so no refund method is captured. Reversing an earlier day's sale doesn't reduce today's Expected Cash. I missed this path in the payment-method investigation, and it needs its own design decision.
2. **Same detached-`this` bug** in the unused `createEntityService` layer and in diagnostics `runFullCheck` (section 2).
3. **French button text:** the POS button "Terminer la Vente et Imprimer le Reçu" is clipped at 360 px in French. That button isn't part of this change; I haven't checked whether 4.3.7 does the same.
4. **Carried over from the investigation:**
   - `promptApplyCredit` has no permission check and no audit entry.
   - `delPay` and `delSale` remove payments without a per-payment audit entry.

**Definition of Done:** everything is met except **real-Android validation**, which stays open until your device QA.
