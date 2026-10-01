"""Protected-function integrity check.
Usage: python3 qa/tools/protected_hash.py index.html [baseline.json]
Prints the 16-char SHA-256 of each protected function; with a baseline, reports changes and exits 1 if any differ."""
import re,sys,hashlib,json
NAMES=['computeRealizedProfit','buildProfitIndex','computeExpenseTotals','computeNetProfit','computeProductSalesAggregates','collectLossRecords','computeShortageChainStatus','filterCollection','loadCollection','renderCollInsights','filterCustomers','drawAllCharts','loadDashboard','custDebt','invBalance','invStatus','stockStatus','openLossRegisterView','filterLossRegister','loadProducts','renderProdTable','saveProduct','resetProdForm','go','shareReceiptPdfWhatsApp','downloadReceipt','printReceipt','_generateReceiptPdfBlob']
def extract(src,name):
    m=re.search(r'function\s+'+re.escape(name)+r'\s*\(',src)
    if not m: return None
    i=src.index('{',m.end()); d=0; j=i
    while True:
        c=src[j]
        if c=='{':d+=1
        elif c=='}':
            d-=1
            if d==0: return src[m.start():j+1]
        j+=1
src=open(sys.argv[1],encoding='utf-8').read()
cur={n:(hashlib.sha256(extract(src,n).encode()).hexdigest()[:16] if extract(src,n) else None) for n in NAMES}
if len(sys.argv)>2:
    base=json.load(open(sys.argv[2]))
    changed=[n for n in NAMES if base.get(n)!=cur[n]]
    print(f'protected functions unchanged: {len(NAMES)-len(changed)}/{len(NAMES)}'+(f'  CHANGED: {changed}' if changed else ''))
    sys.exit(1 if changed else 0)
print(json.dumps(cur,indent=1))
