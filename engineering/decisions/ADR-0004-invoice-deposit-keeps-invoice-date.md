# ADR-0004: Invoice deposit keeps the invoice date

- **Date:** 2026-10-01
- **Status:** Accepted for now; open for a later decision
- **Decided by:** Ngwe (product owner)

## Decision
A deposit entered on the invoice form is dated with the invoice date, not today's date.

## Why
Changing it was outside 4.3.8. With a back-dated invoice, today's cash lands on a past day (backlog BZ-018, decision D4).

## Consequences
`saveSale` is unchanged in this respect.

Do not reopen unless Ngwe asks.
