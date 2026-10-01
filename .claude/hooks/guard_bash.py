#!/usr/bin/env python3
"""PreToolUse hook for Bash: blocks commands that could reach production,
destroy history or lose work. Exit 2 = blocked (stderr is shown to Claude).

Why a hook as well as settings.json "deny" rules: deny rules match command
prefixes only, so `cd x && git push origin main` or `git push origin HEAD:main`
slip past them. This script parses every segment of the command line."""
import json, os, re, shlex, subprocess, sys

PROTECTED_BRANCHES = {'main', 'master', 'production'}
DEPLOY_TOOLS = {'netlify', 'netlify-cli', 'wrangler', 'vercel', 'firebase', 'surge'}
FORBIDDEN_COMMIT = [
    (re.compile(r'\.zip$', re.I), 'ZIP build'),
    (re.compile(r'(^|/)\.env', re.I), 'environment / secrets file'),
    (re.compile(r'backup.*\.json$|bizora.*\.json$|\.bizora$', re.I), 'possible business backup / export'),
    (re.compile(r'\.(pem|key|p12|jks|keystore)$', re.I), 'key or certificate'),
    (re.compile(r'(^|/)node_modules/'), 'node_modules'),
]
SAFE_RM_TARGETS = re.compile(r'^(/tmp/|dist/?$|dist/|qa/out/?|qa/tmp/?|\.pytest_cache)')


def block(reason):
    sys.stderr.write(
        'BLOCKED by Bizora guard (.claude/hooks/guard_bash.py): ' + reason +
        '\nSee CLAUDE.md section 1. Ngwe merges and deploys; Claude Code never does. '
        'If this is genuinely needed, stop and ask Ngwe to run it himself.\n')
    sys.exit(2)


def current_branch(cwd):
    try:
        r = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=cwd,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception:
        return ''


def staged_files(cwd):
    try:
        r = subprocess.run(['git', 'diff', '--cached', '--name-only'], cwd=cwd,
                           capture_output=True, text=True, timeout=10)
        return [l for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def split_segments(cmd):
    """Split on ; && || | and newlines (outside quotes, best effort)."""
    parts, buf, q = [], '', None
    i = 0
    while i < len(cmd):
        c = cmd[i]
        if q:
            buf += c
            if c == q:
                q = None
        elif c in '\'"':
            q = c; buf += c
        elif cmd.startswith('&&', i) or cmd.startswith('||', i):
            parts.append(buf); buf = ''; i += 1
        elif c in ';|\n':
            parts.append(buf); buf = ''
        else:
            buf += c
        i += 1
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def tokens(seg):
    try:
        t = shlex.split(seg)
    except ValueError:
        t = seg.split()
    # drop leading env assignments, sudo, command wrappers
    while t and (re.match(r'^\w+=', t[0]) or t[0] in ('sudo', 'command', 'env', 'nohup', 'time')):
        t = t[1:]
    return t


def git_args(t):
    """Return git subcommand args with global options (-C x, -c k=v) removed."""
    args = t[1:]
    out, i = [], 0
    while i < len(args):
        a = args[i]
        if not out and a in ('-C', '-c', '--git-dir', '--work-tree'):
            i += 2; continue
        if not out and (a.startswith('--git-dir=') or a.startswith('--work-tree=')):
            i += 1; continue
        out.append(a); i += 1
    return out


def refspec_dest(spec):
    spec = spec.lstrip('+')
    dest = spec.split(':', 1)[1] if ':' in spec else spec
    return re.sub(r'^refs/heads/', '', dest)


def check_git(args, cwd, branch, whole):
    if not args:
        return
    sub, rest = args[0], args[1:]
    flags = [a for a in rest if a.startswith('-')]
    pos = [a for a in rest if not a.startswith('-')]

    if sub == 'push':
        bad_flags = {'--force', '-f', '--force-with-lease', '--force-if-includes', '--delete', '-d',
                     '--mirror', '--all', '--prune', '--tags'}
        for f in flags:
            if f in bad_flags or f.startswith('--force') or (re.match(r'^-[a-zA-Z]+$', f) and ('f' in f[1:] or 'd' in f[1:])):
                block(f'"git push {f}" (force / delete / mirror pushes are never allowed).')
        specs = pos[1:]  # pos[0] is the remote
        if any(s.startswith('+') for s in specs):
            block('a "+refspec" push is a force push.')
        if any(s.startswith(':') for s in specs):
            block('a ":branch" push deletes a remote branch.')
        for s in specs:
            if refspec_dest(s) in PROTECTED_BRANCHES:
                block(f'pushing to "{refspec_dest(s)}" deploys to production.')
        if not specs and branch in PROTECTED_BRANCHES:
            block(f'you are on "{branch}"; a bare "git push" would update production.')
        if not specs and branch == 'HEAD':
            block('detached HEAD with a bare push; name the branch explicitly.')
        return

    if sub == 'merge':
        if branch in PROTECTED_BRANCHES or re.search(r'\b(checkout|switch)\s+(main|master)\b', whole):
            block('merging into main is Ngwe\'s step, after review and the Android test.')
        return

    if sub in ('commit', 'cherry-pick', 'revert', 'am', 'apply') and branch in PROTECTED_BRANCHES:
        if sub == 'apply' and '--check' in flags:
            return
        block(f'you are on "{branch}". Create a branch first: git switch -c fix/<name> (or release/<version>).')

    if sub == 'commit':
        for f in staged_files(cwd):
            for rx, what in FORBIDDEN_COMMIT:
                if rx.search(f):
                    block(f'staged file "{f}" looks like a {what}. This repository is public; unstage it '
                          f'(git restore --staged "{f}") and keep such files out of the repo.')

    if sub == 'reset' and ('--hard' in flags or '--merge' in flags or '--keep' in flags):
        block('"git reset --hard" discards work. To go back to a checkpoint, start a new branch from it: '
              'git switch -c <branch>-redo <checkpoint>.')
    if sub in ('rebase', 'filter-branch', 'filter-repo', 'replace'):
        block(f'"git {sub}" rewrites history.')
    if sub == 'clean':
        shorts = ''.join(f.lstrip('-') for f in flags if not f.startswith('--'))
        if ('f' in shorts or '--force' in flags) and 'n' not in shorts and '--dry-run' not in flags:
            block('"git clean -f" permanently deletes untracked files. Use -n to preview, then delete specific files.')
    if sub == 'tag' and any(f in ('-d', '--delete', '-f', '--force') for f in flags):
        block('deleting or moving tags (checkpoints) is not allowed.')
    if sub == 'branch':
        shorts = ''.join(f.lstrip('-') for f in flags if not f.startswith('--'))
        if any(c in shorts for c in 'DMCf') or '--force' in flags:
            block('force-deleting, renaming, copying over or moving branches is not allowed.')
        if ('d' in shorts or '--delete' in flags) and any(p in PROTECTED_BRANCHES for p in pos):
            block('deleting main is not allowed.')
    if sub in ('checkout', 'restore'):
        # discarding all working-tree changes in one go
        if any(p in ('.', ':/', '*') for p in pos) and '--staged' not in flags:
            block(f'"git {sub} ." discards all uncommitted work. Restore specific files by name.')
        if sub == 'checkout' and ('-f' in flags or '--force' in flags):
            block('"git checkout -f" discards uncommitted work.')
        if sub == 'checkout' and ('-B' in flags):
            block('"git checkout -B" resets an existing branch.')
    if sub == 'switch' and any(f in ('-C', '--force-create', '-f', '--force', '--discard-changes') for f in flags):
        block(f'"git switch {" ".join(flags)}" can discard work or reset a branch.')
    if sub == 'stash' and pos[:1] in (['drop'], ['clear']):
        block('dropping stashes loses work.')
    if sub == 'update-ref' or (sub == 'symbolic-ref' and pos):
        block(f'"git {sub}" edits refs directly.')
    if sub == 'remote' and pos[:1] in (['remove'], ['rm'], ['set-url'], ['rename']):
        block('changing git remotes is not allowed.')
    if sub == 'config' and any(re.match(r'^(remote\.|branch\.(main|master)\.|core\.hooksPath)', p) for p in pos):
        block('changing remote / main-branch / hooks configuration is not allowed.')


def check_gh(args, branch):
    if not args:
        return
    a0 = args[0]
    a1 = args[1] if len(args) > 1 else ''
    if a0 == 'pr' and a1 == 'merge':
        block('"gh pr merge": Ngwe merges, after the Android test on the deploy preview.')
    if a0 == 'pr' and a1 == 'review' and ('--approve' in args or '-a' in args):
        block('Claude Code must not approve its own pull requests.')
    if a0 == 'pr' and a1 == 'create':
        base = None
        for i, x in enumerate(args):
            if x in ('--base', '-B') and i + 1 < len(args):
                base = args[i + 1]
            elif x.startswith('--base='):
                base = x.split('=', 1)[1]
        head = None
        for i, x in enumerate(args):
            if x in ('--head', '-H') and i + 1 < len(args):
                head = args[i + 1]
        if (head or branch) in PROTECTED_BRANCHES:
            block('a pull request must come from a work branch, not from main.')
    if a0 == 'repo' and a1 in ('edit', 'delete', 'rename', 'archive', 'sync'):
        block(f'"gh repo {a1}" changes the repository itself.')
    if a0 == 'release' and a1 in ('create', 'delete', 'edit', 'upload'):
        block('creating or changing GitHub releases is Ngwe\'s step.')
    if a0 in ('secret', 'variable', 'ruleset') or (a0 == 'workflow' and a1 in ('run', 'enable', 'disable')):
        block(f'"gh {a0} {a1}" changes repository settings or runs workflows.')
    if a0 == 'api':
        method = None
        for i, x in enumerate(args):
            if x in ('-X', '--method') and i + 1 < len(args):
                method = args[i + 1].upper()
            elif x.startswith('--method='):
                method = x.split('=', 1)[1].upper()
            elif x.startswith('-X') and len(x) > 2:
                method = x[2:].upper()
        has_body = any(x in ('-f', '-F', '--field', '--raw-field', '--input') for x in args)
        if method in ('DELETE', 'PUT', 'PATCH') or (method == 'POST') or (method is None and has_body):
            path = ' '.join(a for a in args[1:] if not a.startswith('-'))
            if not re.search(r'/pulls/\d+/comments|/issues/\d+/comments', path):
                block('"gh api" write calls can change branches, protection rules or settings.')


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get('tool_name') != 'Bash':
        return 0
    cmd = (data.get('tool_input') or {}).get('command', '') or ''
    cwd = data.get('cwd') or os.getcwd()
    branch = current_branch(cwd)
    low = cmd.lower()

    # Network deploy endpoints, whatever tool is used
    if re.search(r'api\.netlify\.com|api\.vercel\.com|api\.cloudflare\.com/.*/pages', low):
        block('direct calls to a hosting API deploy or change production.')

    for seg in split_segments(cmd):
        t = tokens(seg)
        if not t:
            continue
        exe = os.path.basename(t[0])
        if exe in ('npx', 'pnpm', 'yarn', 'bunx') and len(t) > 1:
            inner = [x for x in t[1:] if not x.startswith('-')]
            if inner and os.path.basename(inner[0]).split('@')[0] in DEPLOY_TOOLS:
                block(f'"{inner[0]}" is a deploy tool.')
        if exe in DEPLOY_TOOLS:
            block(f'"{exe}" is a deploy tool. Deployment happens only when Ngwe merges into main.')
        if exe == 'git':
            check_git(git_args(t), cwd, branch, cmd)
        if exe == 'gh':
            check_gh(t[1:], branch)
        if exe in ('rm', 'shred') or (exe == 'find' and '-delete' in t):
            if exe == 'find':
                block('"find -delete" can remove many files at once; delete specific files by name.')
            fl = ''.join(x.lstrip('-') for x in t[1:] if x.startswith('-') and not x.startswith('--'))
            longf = [x for x in t[1:] if x.startswith('--')]
            recursive = 'r' in fl.lower() or '--recursive' in longf
            force = 'f' in fl or '--force' in longf
            targets = [x for x in t[1:] if not x.startswith('-')]
            if exe == 'shred':
                block('"shred" destroys files.')
            if recursive and not all(SAFE_RM_TARGETS.match(x) for x in targets):
                block(f'recursive delete of {targets}. Only /tmp, dist/ and qa/out may be removed recursively.')
            for x in targets:
                base = x.rstrip('/').split('/')[-1]
                if base in ('index.html', 'service-worker.js', 'manifest.json', 'offline.html', 'icons',
                            '.git', 'CLAUDE.md', '.claude', 'qa', 'docs', 'netlify.toml') and not x.startswith('/tmp/'):
                    block(f'deleting "{x}" (an app, guardrail or history file).')
        if exe in ('mv',) and any(x.rstrip('/').split('/')[-1] in ('index.html', 'service-worker.js', '.git') for x in t[1:-1] if not x.startswith('-')):
            block('moving / renaming core app files is not allowed.')
        if exe in ('chmod', 'chown') and any('.git' in x for x in t[1:]):
            block('changing .git permissions is not allowed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
