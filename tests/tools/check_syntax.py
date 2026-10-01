"""node --check every inline <script> block of index.html.
Usage: python3 tests/tools/check_syntax.py index.html
Block 0 is a known false positive (a literal <script> tag inside an HTML comment); it fails identically in every version.
Errors are reported with the matching index.html line number."""
import re, sys, subprocess, tempfile, os

s = open(sys.argv[1], encoding='utf-8').read()
bad = []
for i, m in enumerate(re.finditer(r'<script>(.*?)</script>', s, re.S)):
    b = m.group(1)
    start_line = s.count('\n', 0, m.start(1))  # lines before the block body
    f = tempfile.NamedTemporaryFile('w', suffix='.js', delete=False); f.write(b); f.close()
    r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True); os.unlink(f.name)
    ok = r.returncode == 0
    if ok:
        print(f'block {i}: OK'); continue
    if i == 0:
        print(f'block {i}: ERR  (known false positive)'); continue
    err = r.stderr
    lm = re.search(re.escape(f.name) + r':(\d+)', err)
    where = f'index.html line {start_line + int(lm.group(1))}' if lm else 'unknown line'
    msg = next((l.strip() for l in err.splitlines() if 'Error' in l), err.strip().splitlines()[0] if err.strip() else '?')
    print(f'block {i}: ERR  {msg[:160]} at {where}')
    bad.append(i)
sys.exit(1 if bad else 0)
