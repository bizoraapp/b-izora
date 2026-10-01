#!/usr/bin/env python3
"""Stop hook: before Claude finishes a turn, re-run the Bizora checks when app files
changed on this branch. Blocks (once) if a check fails or work sits uncommitted on main.
Respects stop_hook_active so it can never loop."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bizora_checks as bc  # noqa: E402

APP_FILES = ('index.html', 'service-worker.js', 'manifest.json', 'offline.html')


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    if data.get('stop_hook_active'):
        return 0
    branch = bc.git('rev-parse', '--abbrev-ref', 'HEAD')
    dirty = [l[3:] for l in bc.git('status', '--porcelain').splitlines() if l.strip()]
    problems = []
    if branch in ('main', 'master') and dirty:
        problems.append(f'Uncommitted changes on "{branch}": {dirty[:8]}. Move them to a work branch '
                        '(git switch -c fix/<name>) and never commit them to main.')
    base = bc.git('merge-base', 'HEAD', 'origin/main') or bc.git('merge-base', 'HEAD', 'main')
    changed = set(dirty)
    if base:
        changed |= set(bc.git('diff', '--name-only', base).splitlines())
    if any(f in changed for f in APP_FILES):
        f, w, s = bc.check_app()
        sf, sw = bc.check_sw()
        if f or sf:
            problems.append('Checks failing (' + s + '):\n- ' + '\n- '.join(f + sf))
    if problems:
        print(json.dumps({'decision': 'block',
                          'reason': 'Bizora stop check:\n' + '\n'.join(problems) +
                                    '\nFix it, or if you cannot, say so plainly in your report (never claim success).'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
