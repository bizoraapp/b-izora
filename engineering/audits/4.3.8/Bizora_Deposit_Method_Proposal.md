# Bizora — Deposit Payment Method: Investigation and Fix Proposal

**Status:** investigation done. **No code has been changed.** This proposal waits for PM approval.
**Baseline:** 4.3.7 candidate, branch `release/4.3.7-money-controls` @ `10a9760`. Not deployed.

## 1. Finding (reproduced on 4.3.7)

**Test:** a POS credit sale of 6,000 with a 3,000 deposit, paid by Mobile Money.
- **Payment record:** `{amount: 3000, method: 'cash'}`. The cashier has no way to record anything else.
- **Expected Cash:** 0 → 3,000. It is overstated by 3,000, which matches your report.
- **Audit Log:** it records only `Credit sale INV-… FCFA 6,000 for Amina`. The deposit amount does not appear at all, and neither does its method.

## 2. Root cause: two creation paths, same hard-coded value

| Path | Where | What it saves | Method selector? | Audit |
|---|---|---|---|---|
| POS credit sale | `finalizeCreditSale()`, deposit push | `method:'cash'` hard-coded | **None.** The credit panel holds Deposit, Credit Period and Due Date. The existing `posMethod` selector sits in the cash-sale panel and is hidden for credit sales | None for the deposit |
| New invoice form | `saveSale()`, `initPay` push | `method:'cash'` hard-coded | **None** | `Deposit {amount} from {customer}`, no method |

Every other payment path already saves a real method: Record Payment, overpayments, and account-credit apply (`'account credit'`).

## 3. Who reads `payment.method`, and what fixing it changes

The table lists every reader of the field. All of them display whatever method is stored, so storing the correct method fixes every screen at once, with no other code changes.

| Reader | What it does with the method | Effect of storing the real method |
|---|---|---|
| Cash drawer (`computeDrawerCash`) | Counts `cash` only | **Fixes the overstatement** |
| Payments list and method filter | Shows and filters by method | MoMo deposits appear under Mobile Money (correct) |
| Customer ledger / statement | Method label | Correct label |
| Payment receipt | Method row | Correct method |
| Payments CSV export | Method column | Correct column value; CSV layout unchanged |
| Global search | Matches on method | Correct |
| Profit, revenue, debt, invoice balance, credit limit | **Do not read the method** | **No change** |

The credit-limit approval (4.3.6) is keyed to the deposit **amount**, not its method. Its key stays exactly as it is.

## 4. Proposed fix (recommended: Option A)

### A. Add a "Deposit paid with" selector to both deposit fields (recommended)

- **POS credit panel:**
  - A new selector, `posDepositMethod`, sits directly under "Deposit Paid". It offers the same five options as the POS cash selector: Cash, Mobile Money, Bank Transfer, Card, Other.
  - It is **shown only when the deposit is above 0**, so credit sales with no deposit look and work exactly as today.
  - It is preselected to **Cash**, the same default as the Record Payment form.
- **New invoice form:** the same selector, `sDepositMethod`, sits next to "Deposit / Advance Paid".
- **The save functions decide, not the screen:**
  - `finalizeCreditSale()` and `saveSale()` read the method at save time, the same way 4.3.6 re-reads the cart total.
  - A value outside the allowed list is **refused**, the save is stopped, and nothing is written.
  - The payment record is the same as today except for the true `method`.
- **Audit:**
  - The POS deposit gets its own line: `Deposit FCFA 3,000 (Mobile Money) from Amina on INV-…`.
  - The invoice-form deposit line gains the method: `Deposit FCFA 3,000 (Mobile Money) from Amina`.
- **Reset:** both selectors return to Cash in `resetPosForm()` and `resetSaleForm()`.
- **Text:** two new strings in English and French: "Deposit paid with", and an error for an invalid method.

### B. Reuse the existing `posMethod` selector for credit sales (rejected)

- It lives in the cash-sale panel, next to "Amount Received" and "Change". Using it for credit sales means restructuring the POS layout and giving one field two meanings.
- It does not cover the invoice-form path.

### C. No default: force a choice whenever there is a deposit (possible alternative, see decision 2)

- **Benefit:** a hurried cashier cannot leave it on Cash by mistake.
- **Cost:** one extra tap on every sale with a deposit, and it is inconsistent with the Record Payment form, which defaults to Cash.

## 5. What does not change

- **Database:** no schema change and no migration. `payment.method` already exists; only the value written for new deposits changes.
- **Historical deposits:** they are **not rewritten**. Nobody can know today which past "cash" deposits were really Mobile Money.
  - The cash drawer only shows today, so past deposits do not affect it.
  - Past deposits will keep showing "cash" in the payments list, ledger and CSV. That is a known limitation of the old data.
- **Calculations:** invoice balance, debt, credit-limit checks, profit, reports and receipts are unchanged. None of them read the method.
- **Protected functions:** none are touched. The 28 SHA-256 hashes must stay identical.
- **Performance:** O(1) per sale, with no new scans, timers or stores.

## 6. Files and functions

`index.html` only:
- markup for the two selectors
- `finalizeCreditSale()`, deposit push + audit line
- `saveSale()`, deposit push + method in log
- `resetPosForm()`, `resetSaleForm()`
- `calcPosTotals()` or a small helper to show/hide the POS selector when the deposit is above 0
- two EN/FR strings

`DEVELOPER.md`: changelog line. There is no service-worker change beyond the release's version.

## 7. Risks

1. **Wrong choice by the cashier.** A cashier can still pick the wrong method. The default and decision 2 control how likely that is. The difference with this fix is that the audit line now shows the method chosen and who chose it.
2. **Reopening the 4.3.7 candidate.** This means the full 4.3.7 suite plus regression must run again. There is no approval-code change, so the risk is low.
3. **Old POS deposits stay "cash".** Owners who compare old statements may see the label mismatch. That is a documentation note, not a code risk.

## 8. Tests to add (they must pass before candidate)

- **Method recorded, POS:** a POS credit sale with a deposit paid by each method (cash, MoMo, bank, card, other) saves that method. Expected Cash rises only for cash; the reproduction case is 3,000 MoMo → +0.
- **Method recorded, invoice form:** the same for the new-invoice deposit.
- **No-deposit sale:** the selector stays hidden, the sale works exactly as before and no payment is created.
- **Bad values:**
  - An invalid method value (forced through the page) is refused and nothing is saved: no sale, no payment, no stock movement.
  - A negative deposit or a deposit above the total is still refused, as before.
- **Credit-limit approval (4.3.6):**
  - It still asks once and is still single-use.
  - Changing only the deposit method does **not** cancel an approval; changing the deposit amount still does.
- **Audit:** the deposit audit line shows amount, method, customer and invoice for both paths.
- **Reset and language:** the form resets to Cash after each sale, and the French labels are present.
- **Full re-runs:**
  - the 4.3.7 suite (98) and the 4.3.x regression (390)
  - protected-function hashes (28/28) and EN/FR parity
  - offline and upgrade tests
- **Performance and device:** POS checkout timing unchanged at 1k and 100k transactions, and the layout checked on a 360 px screen.

## 9. Decisions needed

1. **Release:** fold this into 4.3.7 as part of G3 (recommended; 4.3.7 is not deployed and G3 is inaccurate without it) or ship it as 4.3.8?
2. **Default method:** preselect Cash to match Record Payment (recommended), or force a choice whenever there is a deposit (Option C)?
