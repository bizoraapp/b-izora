# ADR-0003: Old records with a missing or unknown payment method are never rewritten or guessed

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decided by:** Ngwe (product owner)

## Decision
They display as "Not recorded" and are left out of Expected Cash, with a count in the drawer note.

## Why
Guessing would silently change historical cash figures. History is never rewritten to make new logic work.

## Consequences
No migration for payment methods. Applies to every future change that reads `payment.method`.

Do not reopen unless Ngwe asks.
