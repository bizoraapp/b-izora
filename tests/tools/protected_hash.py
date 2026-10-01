"""Protected-function integrity check.

Usage:
  python3 tests/tools/protected_hash.py index.html                      print the hashes (JSON)
  python3 tests/tools/protected_hash.py index.html BASELINE.json        compare; exit 1 if any differ
  python3 tests/tools/protected_hash.py index.html auto                 pick the baseline for the file's APP_VERSION

The approved-change list (tests/approved_protected_changes.txt) names functions that
Ngwe has explicitly approved changing for the current release. They are reported
but do not fail the check. Prints the 16-char SHA-256 of each protected function."""
import re, sys, hashlib, json, os

NAMES = ['computeRealizedProfit', 'buildProfitIndex', 'computeExpenseTotals', 'computeNetProfit',
         'computeProductSalesAggregates', 'collectLossRecords', 'computeShortageChainStatus',
         'filterCollection', 'loadCollection', 'renderCollInsights', 'filterCustomers', 'drawAllCharts',
         'loadDashboard', 'custDebt', 'invBalance', 'invStatus', 'stockStatus', 'openLossRegisterView',
         'filterLossRegister', 'loadProducts', 'renderProdTable', 'saveProduct', 'resetProdForm', 'go',
         'shareReceiptPdfWhatsApp', 'downloadReceipt', 'printReceipt', '_generateReceiptPdfBlob']

TESTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_DIR = os.path.join(TESTS_DIR, 'baselines')
APPROVED_FILE = os.path.join(TESTS_DIR, 'approved_protected_changes.txt')


def extract(src, name):
    m = re.search(r'function\s+' + re.escape(name) + r'\s*\(', src)
    if not m:
        return None
    i = src.index('{', m.end()); d = 0; j = i
    while True:
        c = src[j]
        if c == '{': d += 1
        elif c == '}':
            d -= 1
            if d == 0:
                return src[m.start():j + 1]
        j += 1


def hashes(src):
    out = {}
    for n in NAMES:
        body = extract(src, n)
        out[n] = hashlib.sha256(body.encode()).hexdigest()[:16] if body else None
    return out


def app_version(src):
    m = re.search(r"const APP_VERSION\s*=\s*'([^']+)'", src)
    return m.group(1) if m else None


def _vkey(v):
    return tuple(int(x) for x in re.findall(r'\d+', v))


def pick_baseline(version):
    """Baseline for this version, else the newest baseline older than it."""
    files = {}
    for f in os.listdir(BASELINE_DIR):
        m = re.match(r'protected-([\d.]+)\.json$', f)
        if m:
            files[m.group(1)] = os.path.join(BASELINE_DIR, f)
    if not files:
        return None
    if version and version in files:
        return files[version]
    older = [v for v in files if version and _vkey(v) <= _vkey(version)]
    best = max(older or files, key=_vkey)
    return files[best]


def approved_names():
    if not os.path.exists(APPROVED_FILE):
        return set()
    names = set()
    for line in open(APPROVED_FILE, encoding='utf-8'):
        line = line.split('#', 1)[0].strip()
        if line:
            names.add(line)
    return names


def compare(src, baseline_path):
    """Returns (changed_unapproved, changed_approved)."""
    base = json.load(open(baseline_path))
    cur = hashes(src)
    changed = [n for n in NAMES if base.get(n) != cur[n]]
    ok = approved_names()
    return [n for n in changed if n not in ok], [n for n in changed if n in ok]


def main():
    src = open(sys.argv[1], encoding='utf-8').read()
    if len(sys.argv) < 3:
        print(json.dumps(hashes(src), indent=1))
        return 0
    path = sys.argv[2]
    if path == 'auto':
        path = pick_baseline(app_version(src))
        if not path:
            print('no baseline found in tests/baselines/')
            return 1
    bad, approved = compare(src, path)
    total = len(NAMES)
    msg = f'protected functions unchanged: {total - len(bad) - len(approved)}/{total} (baseline {os.path.basename(path)})'
    if approved:
        msg += f'  APPROVED CHANGES: {approved}'
    if bad:
        msg += f'  CHANGED WITHOUT APPROVAL: {bad}'
    print(msg)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
