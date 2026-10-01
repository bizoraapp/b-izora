#!/usr/bin/env python3
"""Shared checks for the Bizora Claude Code hooks (not deployed).

Runs fast (< 2 s on the 19k-line index.html):
  1. syntax      every inline <script> block passes `node --check`
  2. protected   the 28 protected functions match the baseline for this APP_VERSION
                 (minus names listed in qa/approved_protected_changes.txt)
  3. i18n        EN and FR dictionaries have identical keys
plus warnings for known traps that newly appear compared with HEAD."""
import os, re, subprocess, sys, json

ROOT = os.environ.get('CLAUDE_PROJECT_DIR') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'qa', 'tools'))


def _run(args, timeout=60):
    try:
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError as e:
        return 0, f'(skipped: {e.filename} not installed)'
    except subprocess.TimeoutExpired:
        return 1, 'timed out'


def git(*args):
    rc, out = _run(['git'] + list(args), timeout=15)
    return out if rc == 0 else ''


def check_app(index='index.html'):
    """Returns (failures:list[str], warnings:list[str], summary:str)."""
    path = os.path.join(ROOT, index)
    fails, warns, lines = [], [], []
    if not os.path.exists(path):
        return ['index.html is missing'], [], 'index.html missing'

    rc, out = _run([sys.executable, 'qa/tools/check_syntax.py', index])
    lines.append('syntax: ' + ('OK' if rc == 0 else 'FAIL'))
    if rc != 0:
        fails.append('JavaScript syntax error:\n' + '\n'.join(l for l in out.splitlines() if 'ERR' in l and 'known false positive' not in l))

    rc, out = _run([sys.executable, 'qa/tools/protected_hash.py', index, 'auto'])
    lines.append(out.splitlines()[-1] if out else 'protected: ?')
    if rc != 0:
        fails.append('Protected function changed without approval: ' + out +
                     '\nRevert it, unless Ngwe explicitly approved this exact function change; then add its name to '
                     'qa/approved_protected_changes.txt (asks permission) and state the approval in the report.')

    rc, out = _run(['node', 'qa/tools/i18n_parity.js', index])
    lines.append('i18n: ' + (out.splitlines()[0] if out else '?'))
    if rc != 0:
        fails.append('EN/FR dictionary mismatch: ' + out + '\nEvery key needs both English and French (see docs/I18N.md).')

    warns.extend(trap_warnings(path, index))
    return fails, warns, ' | '.join(lines)


TRAPS = [
    (r'\.toISOString\(\)\s*\.(slice|split|substr|substring)\(', 'new .toISOString() date key: it converts to UTC and shifts dates in Cameroon (UTC+1). Build YYYY-MM-DD from getFullYear/getMonth/getDate (use the existing localISODate(d)).'),
    (r"method\s*:\s*'cash'", "new hard-coded method:'cash'. Never default or guess a payment method (4.3.8 rule); read the user's explicit choice and check isPaymentMethod() inside the save function."),
    (r'\blocalStorage\.setItem\(', 'new localStorage write: business data belongs in IndexedDB through S.*; localStorage is only for small UI preferences.'),
    (r'\bsetInterval\(', 'new setInterval: no new timers or polling without approval (performance policy).'),
    (r'<script[^>]+src=|import\s+[^;]+from\s+[\'"]https?:', 'new external script/library: Bizora has no runtime dependencies.'),
    (r'\bS\.set\(\s*[\'"](posSales|sales|payments|stockMovements|auditLog)[\'"]', 'new S.set() on a large store: S.set rewrites the whole store (O(N)); use S.add / S.update / S.remove for single records.'),
]


def trap_warnings(path, index):
    try:
        now = open(path, encoding='utf-8').read()
    except Exception:
        return []
    before = git('show', f'HEAD:{index}')
    if not before:
        return []
    out = []
    for rx, msg in TRAPS:
        if not msg:
            continue
        a, b = len(re.findall(rx, before)), len(re.findall(rx, now))
        if b > a:
            out.append(f'{msg} (count {a} -> {b})')
    # stored values must stay English: flag new t()/tf() inside audit / log writes
    a = len(re.findall(r'(logAuditEvent|\blog)\([^;\n]*\bt\(', before))
    b = len(re.findall(r'(logAuditEvent|\blog)\([^;\n]*\bt\(', now))
    if b > a:
        out.append(f'translated text (t()) inside an audit/activity write: stored text stays canonical English (count {a} -> {b}).')
    return out


def check_sw():
    path = os.path.join(ROOT, 'service-worker.js')
    if not os.path.exists(path):
        return ['service-worker.js is missing'], []
    rc, out = _run(['node', '--check', 'service-worker.js'])
    fails = [] if rc == 0 else ['service-worker.js syntax error: ' + out[-300:]]
    warns = []
    src = open(path, encoding='utf-8').read()
    m = re.search(r"PREVIOUS_CACHE_VERSION\s*=\s*'([^']+)'", src)
    if m:
        warns.append(f'PREVIOUS_CACHE_VERSION is {m.group(1)}. It must equal the cache that is LIVE now '
                     '(check https://bizora-cm.netlify.app/service-worker.js); never a candidate that was not deployed.')
    return fails, warns


def app_versions():
    info = {}
    try:
        s = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
        for k in ('APP_VERSION', 'BUILD_NUMBER', 'IDB_VERSION'):
            m = re.search(r'const ' + k + r"\s*=\s*'?([^';\n]+)'?", s)
            info[k] = m.group(1) if m else '?'
    except Exception:
        pass
    try:
        s = open(os.path.join(ROOT, 'service-worker.js'), encoding='utf-8').read()
        for k in ('CACHE_VERSION', 'PREVIOUS_CACHE_VERSION'):
            m = re.search(r'const ' + k + r"\s*=\s*'([^']+)'", s)
            info[k] = m.group(1) if m else '?'
    except Exception:
        pass
    return info


if __name__ == '__main__':
    f, w, summary = check_app()
    sf, sw = check_sw()
    print(summary)
    for x in f + sf:
        print('FAIL:', x)
    for x in w + sw:
        print('WARN:', x)
    sys.exit(1 if (f or sf) else 0)
