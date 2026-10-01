# ADR-0005: Claude Code builds, the PM briefs and audits, Ngwe approves, tests on Android and merges

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decided by:** Ngwe (product owner)

## Decision
Nothing reaches `main` without Ngwe. Claude Code works only on branches and pull requests. The PM (Claude, in the project chat) writes briefs and audits.

## Why
Every merge to `main` deploys to production for real shops.

## Consequences
Enforced by `CLAUDE.md`, the `.claude` permissions and hooks, and GitHub branch protection.

Do not reopen unless Ngwe asks.
