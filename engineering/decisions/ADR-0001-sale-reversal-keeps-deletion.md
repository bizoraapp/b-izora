# ADR-0001: Sale reversal keeps its current deletion behaviour

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decided by:** Ngwe (product owner)

## Decision
Reversing a sale deletes it and resets the records linked to it: stock is restored and payments and debt are removed. A reversal or refund record type was considered and not built.

## Why
Deletion is what the shops already rely on. A reversal record type would add accounting rules and change past days' figures. Known accepted side effects: a refund for an earlier day's sale is not shown in today's drawer, and past days' figures change.

## Consequences
`openReverseSale`, `reversePosSale`, `delSale`, `cancelSale` are not redesigned. Editing a completed cash sale is not planned (reverse and re-enter). Revisit only if real shops report problems (backlog BZ-002, BZ-012).

Do not reopen unless Ngwe asks.
