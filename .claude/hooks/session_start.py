#!/usr/bin/env python3
"""SessionStart hook: tells Claude Code where it stands before it touches anything."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bizora_checks as bc  # noqa: E402


def main():
    branch = bc.git('rev-parse', '--abbrev-ref', 'HEAD') or '?'
    head = bc.git('log', '-1', '--format=%h %s') or '?'
    dirty = len([l for l in bc.git('status', '--porcelain').splitlines() if l.strip()])
    v = bc.app_versions()
    msg = f"""BIZORA SESSION START
Branch: {branch}  ({head}){'  UNCOMMITTED FILES: ' + str(dirty) if dirty else ''}
This checkout: APP_VERSION {v.get('APP_VERSION')} · BUILD {v.get('BUILD_NUMBER')} · CACHE {v.get('CACHE_VERSION')} · PREVIOUS {v.get('PREVIOUS_CACHE_VERSION')} · IDB {v.get('IDB_VERSION')}

Before doing anything:
1. Read CLAUDE.md fully, then the docs it points to for your task (docs/PRODUCT.md, docs/BUG_HISTORY.md, docs/I18N.md, docs/DECISIONS.md).
2. Every push or merge to main deploys to production for real shops. Never push to / merge into main, never deploy. Work on a branch and open a PR.
3. Start read-only. No code until Ngwe (or the PM brief he approved) confirms the scope.
4. Live production cache must be checked on https://bizora-cm.netlify.app/service-worker.js before any release; PREVIOUS_CACHE_VERSION = that live cache.
Hooks are active: dangerous git/deploy commands are blocked, and index.html edits are checked automatically (syntax, 28 protected functions, EN/FR parity)."""
    if branch in ('main', 'master'):
        msg += '\nYou are on main: edits are blocked here. Create a branch once the scope is approved.'
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': msg}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
