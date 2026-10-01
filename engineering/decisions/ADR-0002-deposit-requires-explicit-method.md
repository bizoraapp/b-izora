# ADR-0002: Credit deposits require an explicit payment method

- **Date:** 2026-10-01
- **Status:** Accepted (shipped in 4.3.8)
- **Decided by:** Ngwe (product owner)

## Decision
Every deposit on a credit sale or new invoice needs the cashier to choose Cash, Mobile Money, Bank Transfer, Card or Other. There is no default and Cheque is not offered for deposits.

## Why
Deposits were always saved as cash, which inflated Expected Cash when the customer paid by Mobile Money.

## Consequences
`PAYMENT_METHODS`, `DEPOSIT_METHODS` and `isPaymentMethod()` validate inside the save functions before any write.

Do not reopen unless Ngwe asks.
