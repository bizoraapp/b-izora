#!/usr/bin/env python3
"""PreToolUse hook for Edit / Write / MultiEdit / NotebookEdit.
Blocks (exit 2) file changes while on main, inside .git, outside the repository,
or that would put forbidden files (ZIP builds, backups, secrets) in this public repo."""
import json, os, re, subprocess, sys

ROOT = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
PROTECTED_BRANCHES = {'main', 'master', 'production'}


def block(reason):
    sys.stderr.write('BLOCKED by Bizora guard (.claude/hooks/guard_edit.py): ' + reason + '\n')
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get('tool_input') or {}
    path = ti.get('file_path') or ti.get('notebook_path') or ''
    if not path:
        return 0
    ap = os.path.realpath(path if os.path.isabs(path) else os.path.join(data.get('cwd') or ROOT, path))
    root = os.path.realpath(ROOT)
    inside = ap == root or ap.startswith(root + os.sep)
    if not inside:
        return 0  # scratch files elsewhere (e.g. /tmp) are fine
    rel = os.path.relpath(ap, root)
    if rel.split(os.sep)[0] == '.git':
        block('editing files inside .git is not allowed.')
    if re.search(r'\.(zip|pem|key|p12|jks|keystore)$', rel, re.I) or re.search(r'(^|/)\.env', rel):
        block(f'"{rel}" must not be created in this public repository.')
    try:
        branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=root,
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        branch = ''
    if branch in PROTECTED_BRANCHES:
        block(f'you are on "{branch}". Every change to main deploys to production. Create a work branch first '
              f'(git switch -c fix/<name> or release/<version>), after the scope is approved.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
