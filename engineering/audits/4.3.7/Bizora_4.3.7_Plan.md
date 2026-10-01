# Bizora 4.3.7 — Money Controls: Implementation Plan (for approval)

Status: PLAN ONLY. No code written. Baseline: 4.3.6 (build 2026.09.30e), to be deployed first/independently.
Scope: three money-control gaps found in the 4.3.6 audit. Nothing else.

## 1. Gaps, with code evidence (4.3.6 index.html)

| # | Gap | Where | What happens today |
|---|-----|-------|--------------------|
| G1 | Fake repayment / overpayment | `savePay()` ~L9299-9343 | Amount above invoice balance is split: applied part -> `payments`, excess -> `creditLedger` ('earned'). The excess branch writes NO audit entry (only the exact-payment branch calls `log()`). The excess cash is also not in `payments`, so the drawer never sees it. |
| G2 | Account-credit refund unguarded | `promptRefundCredit()` ~L8121 | Only a generic Confirm. No `Auth.can()` check, no Owner approval, no audit entry, no method recorded. Reachable by any logged-in user; also callable from the console. G1 + G2 = a clean extraction path: record an inflated "payment", then "refund" it as cash. |
| G3 | Wrong expected cash | `renderCashDrawer()` ~L13346 | `expected = opening + cashSales + ALL payments`. (a) payments of every method (mobile money, bank, card) are counted as cash; (b) cash expenses and cash credit-refunds are not subtracted; (c) cash sales use `s.paid` (cash handed over), not the sale total, so change given back inflates the figure (seed data shows paid 75,000 on a 70,000 sale); (d) POS credit deposits and `savePay` are hard-coded/selected method, see risk R3. |
| G4 | Drawer edits unlogged | `saveCashDrawer()` ~L13371 | Opening/closing overwritten with no audit, no previous value kept. Editing opening cash silently hides a shortage. |

## 2. Design (extension only, no rewrites)

**G1 - overpayment control (`savePay`)**
- If `amount > invBalance`, before saving show a confirm step: "Invoice balance X. Excess Y will be banked as account credit for <customer>." 
- Owner session: Confirm. Employee session: Owner password (same verify path as credit-limit approval, session NOT switched).
- Always write `logAuditEvent('payment', ...)` for the excess with amount, invoice, customer, method (new nullable `method` on the 'earned' credit entry).
- Exact or partial payments: flow unchanged (keeps the 300 ms / <10 s path).

**G2 - refund control (`promptRefundCredit`)**
- Require refund method choice (cash / mobile money / bank) - 1 tap.
- Employee: Owner password required. Owner: existing confirm is kept.
- `logAuditEvent('payment', 'Account credit refunded ...', {recordType:'customer', recordId, prevValue, newValue})`.
- `addCreditEntry` gets an optional trailing `method` argument (nullable, backward compatible; existing 4 call sites untouched).
- Owner-approval mechanics: prefer adding a third request kind to `OwnerApproval` (reuses modal, hash verify, single-use token). No new permission key, no change to `rolePermissions` schema.

**G3 - correct expected cash (`renderCashDrawer`)**
```
expected = opening
         + cash POS sales (total, not paid)
         + cash deposits / cash collections (payments.method==='cash')
         + cash overpayment excess (creditLedger earned, method cash)
         - cash expenses (new nullable expense.payMethod)
         - cash credit refunds (creditLedger refunded, method cash)
```
- Mobile money / bank / card / account-credit-applied are shown as separate "non-cash" lines and excluded from expected cash.
- Expense form: add a Cash / Non-cash selector, default Cash (1 tap, pre-selected).
- Drawer panel gets two new lines (cash expenses, cash refunds) using existing card styles. Today only; no other page reads this figure.

**G4 - drawer edit logging (`saveCashDrawer`)**
- Log opening and closing changes vs the stored value (prev/new, who).
- Changing opening cash after the day already has cash transactions: Owner password for employees.
- Keep small per-day `edits[]` (max 10) inside the existing `cashDrawer` object so history survives audit-log rotation (audit log caps at 5,000).

## 3. Files, schema, migration

- `index.html`: `savePay`, `promptRefundCredit`, `addCreditEntry` (optional arg), `renderCashDrawer`, `saveCashDrawer`, `saveExpense` + expense modal markup, `OwnerApproval` (one new kind), EN/FR keys.
- `service-worker.js`: CACHE_VERSION v129 -> v130; PREVIOUS stays v120 until 4.3.6 is live, then v129.
- `DEVELOPER.md`, changelog, APP_VERSION 4.3.7.
- IDB: NO version change (stays v8). Only additive nullable fields: `expenses.payMethod`, `creditLedger.method`, `cashDrawer[day].edits`.
- Legacy rows (field missing): treated as cash, the conservative reading (lowers expected cash, never hides a shortage). Affects today's drawer only.
- Reuses: `logAuditEvent`, `verifyOwnerPassword` path, `custCreditBalance`, `invBalance`, `confirm2`, existing toast/i18n.
- NOT touched: `computeRealizedProfit`, `buildProfitIndex`, `computeExpenseTotals`, `computeNetProfit`, series functions, sales/credit/inventory calculations, licensing, trial, access control. Hash check proves it.

## 4. Why existing behaviour is unaffected

- Payment records, invoice balances, debts, statuses: same formulas, same stores.
- Reports/Financial Summary/Dashboard read `payments`/`expenses` amounts only; new fields are ignored by them.
- Past days' drawer figures are not displayed anywhere, so no historical result changes. Stop condition respected: if the regression suite shows any existing figure moving, work stops.

## 5. Performance report (pre-implementation)

- Drawer render: ~5 single passes (posSales, payments, creditLedger, expenses, sales) filtered by today's date = O(N) each, only when Cash Drawer page is opened; no timers, no new stores, no new dependencies. Same pattern as today plus two passes.
- Optional follow-up (not in scope): by-date index if 100k-row timing is unacceptable.
- `savePay`/`promptRefundCredit`: O(1) extra work; `custCreditBalance` scan is pre-existing.
- To be measured on 1k / 10k / 50k / 100k transactions before sign-off, on the 2 GB-class profile used in 4.3.6 testing.

## 6. Risks and mitigations

- R1: `OwnerApproval` is sensitive code (the 4.3.6 stale-approval bug lived there). Mitigation: single-use, cleared on modal close, dedicated tests incl. replay of an unused approval for a different amount.
- R2: Employees blocked when Owner absent. Mitigation: they can still record normal payments; only excess/refund needs the Owner.
- R3: Payment method correctness depends on the cashier choosing it; POS deposits are hard-coded `'cash'` (L14130). Plan: use the selected POS method if one exists; otherwise report, not fix (no scope expansion).
- R4: Cash expenses default to Cash; a cashier paying by mobile money must flip the toggle or expected cash is understated (error direction = flags shortage, which is the safe direction).
- R5: Console calls bypass UI gates. Out of scope; noted as part of the separate security candidate.

## 7. Tests (must be green before candidate)

Functional: exact/partial/over payment; employee vs owner; refund by method; drawer formula with mixed methods, change, expenses, refunds; edit logging; FR/EN parity.
Edge: zero/negative/decimal amounts, double-tap, refund with zero credit, approval replay, midnight rollover, legacy rows without new fields.
Integrity: all 15 stores byte-identical after 4.3.6 -> 4.3.7 upgrade; 23/28 protected hashes unchanged (same 5 intentional 4.3.x changes); diff confinement.
Performance: drawer render timing at 1k/10k/50k/100k; checkout timing vs 4.3.6 baseline (9.4 s at 10k/100k).
Regression: startup, dashboard, POS, Financial Summary, navigation, `qa/run.js` single verdict.

## 8. Decisions needed from product owner

1. Legacy/missing method = cash (recommended) or unknown/excluded?
2. Employee overpayment: Owner password required (recommended) or allow up to a threshold?
3. Drawer opening-cash edit after transactions: Owner-only for employees (recommended)?

## 9. Out of scope (separate candidates)

Sign-in overlay flaw; recovery snapshot lost on update; plaintext developer password in source; notifications 9.9 s scan.
