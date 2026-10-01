# Bizora — product knowledge

What Bizora is, who uses it, and how money moves through it. Read this before designing or changing any workflow. Code locations refer to `index.html` 4.3.8; confirm them in the real code before relying on them.

## 1. Product in one paragraph

Bizora is an **offline-first business app for small shops in Cameroon** (and later other French-speaking African markets). A shop records its **cash sales**, **sales on credit** and the **repayments** customers make over the following weeks, plus **expenses**, **stock** and the **daily cash drawer**. In return it shows who owes what, how much cash should be in the drawer, and whether the business makes a profit. Currency: **FCFA**. Languages: **French and English**. Live at `bizora-cm.netlify.app` as an installable PWA.

**Mission:** the most trusted offline-first business app for African SMEs. **Trust is the product**: if a balance or a cash figure is wrong once, the owner stops relying on the app.

## 2. Who uses it

| User | Situation | What they need |
|---|---|---|
| **Business owner** (Owner) | Often not at the shop all day; may be the only person who knows the Owner password | Correct debts, cash and profit; control over what employees can do; proof of who did what |
| **Cashier** | Sells all day on a shared, low-end Android phone (2–4 GB RAM), often offline, frequent power cuts | Record a sale in a few seconds, with few taps and little typing |
| **Supervisor / sales rep / storekeeper** | Delegated work (customers, stock, reports) | Only the screens their role allows |
| **Customers of the shop** | Buy on credit, pay in instalments by cash or Mobile Money (MTN MoMo / Orange Money) | A receipt or WhatsApp message showing what they paid and what they still owe |

**Market:** retail shops, provision stores, pharmacies, mini-markets, wholesalers, hardware and clothing stores. **Constraints:** unstable internet, prepaid mobile data, power cuts, older phones, users with limited technical experience. Performance targets: startup < 2 s, dashboard < 1 s, record sale < 300 ms, customer search < 200 ms.

## 3. Modules (pages)

`PAGE_META` / `PAGE_LOADERS` list the pages: Dashboard, Customers, Products, Inventory, POS ("Start Selling"), Sales (credit invoices), Expenses, Financial Summary, Sales History, Payments, Collection (overdue follow-up), Debt Ledger, Reports (and Product Analytics), Calendar (due dates), Settings, Backup, About, Help.

Inventory has Stock In, Stock Adjustments (with approval above a threshold), Daily Stock Check, Monthly Reconciliation, Loss Register and Product History. The **Invoice feature** (manual "New Invoice") is being retired from the UI; the code and stored invoices stay. Credit sales are normally created from the POS.

## 4. Access control

- **Access Control off** (default for a one-person shop): everyone is effectively the Owner.
- **Access Control on:** an Owner password, employees with their own logins and roles. `Auth.can(perm)`, `Auth.isOwner()`, `Auth.canDelete()` (Owner only; deletion is never grantable to a role).
- **Rule:** permission checks go **inside the function that writes data**, never only on the button. Earlier releases shipped functions that trusted their caller; see `BUG_HISTORY.md` SEC-01/02.

Default permissions (`DEFAULT_ROLE_PERMISSIONS`; the Owner can customise each role):

| Permission | Cashier | Storekeeper | Sales rep | Supervisor |
|---|---|---|---|---|
| recordSales (POS, invoices, payments) | ✓ | | ✓ | ✓ |
| manageCustomers | | | ✓ | ✓ |
| viewReports | | | ✓ | ✓ |
| manageInventory (stock, cash drawer) | | ✓ | | ✓ |
| addProducts / editProducts | | ✓ | | ✓ |
| viewFinancials | | | | ✓ |
| exportReports | | | | ✓ |
| manageExpenses | | | | ✓ |
| accessSettings | | | | |
| approveAdjustments | | | | |
| viewHelp | | ✓ | ✓ | ✓ |

The Backup page is **Owner-only**. Cashiers get an external user manual instead of the in-app Help.

**Owner approvals (`OwnerApproval`):** some employee actions need the Owner to type their password on the employee's device. Each approval is **single-use** and **bound** to the exact action (customer, invoice, amount, method…). It is consumed only when the action is actually saved. Current approval kinds:
- POS selling-price changes (any discount or markup);
- invoice amount change, cancellation, customer change;
- credit over the customer's limit, and raising/removing a limit or unblocking a customer;
- overpayment kept as account credit;
- account-credit refund.

Never weaken, reuse or bypass these approvals.

## 5. Money concepts (the vocabulary of every financial rule)

| Term | Meaning in Bizora | Source of truth |
|---|---|---|
| **Cash sale** (`posSales.type 'cash'`) | Paid in full **now**. It says nothing about *how* (could be MoMo) | `posSales` |
| **Credit sale / invoice** | Goods taken now, paid later; creates debt | `creditSales` (key `sales`) |
| **Deposit** | Part paid at the moment of a credit sale; stored as a payment on that invoice | `repayments` (key `payments`) |
| **Repayment / payment** | Money received later against an invoice | `repayments`; `savePay()` |
| **Payment method** | `cash`, `mobile-money`, `bank-transfer`, `cheque`, `card`, `other` (`PAYMENT_METHODS`). Deposits: same without cheque (`DEPOSIT_METHODS`). Only `cash` is physical cash | `isPaymentMethod()` |
| **Invoice balance** | Amount − payments (never below 0) | `invBalance()` |
| **Customer debt** | Sum of open invoice balances | `custDebt()` |
| **Overpayment / account credit** | Paid more than owed; the excess is held for the customer (Owner approval) | `creditLedger`, `custCreditBalance()` |
| **Apply credit** | Use account credit to pay an invoice | `promptApplyCredit()` (BZ-003: needs a permission check and an audit entry) |
| **Credit refund** | Hand account credit back as money (method required) | `refundAccountCredit()` |
| **Credit limit** | Maximum debt for a customer; `≤ 0` means Unlimited. Over the limit needs Owner approval | customer record |
| **Expected Cash** | Opening cash + POS cash kept (paid − change) + cash payments + cash overpayments − cash expenses − cash refunds. **Non-cash methods never count.** Records with a missing or unknown method are excluded and counted in a note | `computeDrawerCash()` |
| **Actual Revenue** | Accrual: cash sales + credit sales when made (not repayments) | `computeRealizedProfit()` |
| **Cash Collections** | Cash basis: includes repayments | Financial Summary |
| **Gross / net profit** | Revenue − cost of goods / − expenses | `computeRealizedProfit`, `buildProfitIndex`, `computeNetProfit` |
| **Sale reversal** | Owner-only. **Deletes** the sale and resets linked records (stock back, payments and debt removed). Decided 2026-10-01: keep as is | `openReverseSale()` → `reversePosSale()` / `delSale()` / `cancelSale()` |

## 6. Core workflows (each should take under 10 seconds)

1. **Cash sale (POS):** pick products → (optional price change, needs Owner approval for employees) → amount received → change → receipt (print, PDF, WhatsApp). `checkoutPos()`.
2. **Credit sale (POS):** choose customer → optional deposit with **required** "Deposit paid with" method → credit-limit check → invoice + deposit payment + stock movement → receipt showing the deposit method. `checkoutPos()` → `finalizeCreditSale()`.
3. **Record payment:** customer → invoice → amount → method → receipt. Overpayment → account credit with approval. `savePay()`.
4. **Expense:** amount, category, "Paid with". `saveExpense()`.
5. **Find a balance:** Customers / Debt Ledger / global search.
6. **Close the day:** cash drawer opening and closing count against Expected Cash (`renderCashDrawer()`), End-of-Day report.
7. **Backup:** export JSON (all stores) and restore (merge by id, recovery point saved first). Owner only.

## 7. Licensing

- Offline ECDSA P-256 licence verification: the app only holds the public key; licences are signed by a separate Admin Suite.
- 30-day trial with tamper resistance.
- Monthly (5-day warning) and Annual (30-day warning) plans; an expired licence blocks writes through `License.guard()` but keeps reading.
- Never change the verification flow. Extend through the signed payload only.

## 8. Design principles

- **Brand:** navy `--navy #0B2C6B`, gold `--gold #F4B400`, plus success, warning and danger tokens. Use the CSS variables, never new hard-coded colours.
- **Mobile first:** 360 px width, one-handed use, large touch targets, minimal typing (numeric keypads, comma-formatted amount fields).
- **Android low-graphics mode:** `html[data-platform="android"]` disables blur, animation and fixed backgrounds, because they froze Samsung and Xiaomi GPUs. Never add `backdrop-filter`, heavy shadows or animation that bypasses it.
- **Feedback:** loading, empty, success and failure states on every screen. Confirm (`confirm2`) destructive or hard-to-undo actions.
- **Wording:** plain business words the shop owner uses ("Expected Cash", "Deposit paid with"), never technical terms.

## 9. What Bizora will never become

An overly complex ERP; an app that needs constant internet; software that trades speed for visual effects; a system with complicated workflows. A feature that solves one problem very well beats many mediocre features. If forced to choose, **sacrifice features before reliability or speed**.

## 10. Roadmap position (October 2026)

| Phase | Status |
|---|---|
| 1 Sales management, 2 Financial intelligence | Done |
| 3 Inventory intelligence, 4 Product intelligence | Built; awaiting formal sign-off |
| 5 Customer intelligence | Partial (risk level, pay speed) |
| 8 Operational excellence | In progress: access control, approvals, audit (4.3.x) |
| 9 Digital business services | Not started. The 4.3.8 payment-method model is its foundation |
| 10 Multi-business | Not started. There is no `storeId` anywhere yet, so **don't add anything that assumes a single shop forever** |

The live backlog and release plan are kept by the PM in the project tracker (`Bizora_Product_Backlog.md`), not in this repository.
