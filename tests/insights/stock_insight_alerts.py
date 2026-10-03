"""Dashboard Smart Insights: out-of-stock (red) and low-stock (orange) alerts open Inventory
filtered to the matching products; the low collection-rate alert opens the Collection page.

Real Chromium, real app code, real IndexedDB origin, phone viewport 360x640 (Android user-agent).
Path-independent: serves the repository root on a free port. No outside network.

    python3 tests/insights/stock_insight_alerts.py

Exit code 0 = every check passed.
"""
import os, sys, json, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UA = 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36'

class _H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
class _S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True

RES = []
def chk(area, name, cond, info=''):
    RES.append((area, name, bool(cond)))
    print(('PASS' if cond else 'FAIL'), '|', area, '|', name, '' if cond else '| ' + json.dumps(info, ensure_ascii=False, default=str)[:600])

SETUP = """async(a)=>{
  document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  if(typeof FirstRunWizard!=='undefined')FirstRunWizard.skip();
  const P='2026-01-05';
  for(const x of a.prods)S.add('products',{category:'Food',cost:100,price:200,unit:'pcs',tax:0,status:'active',added:P,lowStock:5,...x});
  if(a.role&&a.role!=='owner'){const salt=genSalt();setAccessControl({enabled:true,pendingSetup:false,ownerPasswordHash:await hashPassword('owner99',salt),ownerPasswordSalt:salt,recoveryCodeHash:'x',recoveryCodeSalt:'x'});
    const c=await createEmployee({fullName:'Emp '+a.role,username:'u'+a.role,password:'1234',role:a.role});await Auth.loginEmployee(c.employee.id,'1234');onEmployeeSessionStarted();}
  if(a.collection){S.add('customers',{id:'c1',name:'Awa',phone:'677000001',status:'active'});
    S.add('sales',{id:'s1',cid:'c1',amount:10000,cost:6000,date:P,due:'2026-02-05',status:'pending',items:[]});
    S.add('payments',{id:'r1',saleId:'s1',cid:'c1',amount:2000,date:P,method:'cash'});}
  document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  go('dashboard');
  return true}"""
CARDS = """()=>[...document.querySelectorAll('#insightsFeed .insight-card')].map(c=>({txt:c.querySelector('.insight-txt').childNodes[0].textContent.trim(),
  sub:(c.querySelector('.insight-sub')||{}).textContent||'',tone:[...c.classList].find(x=>x.startsWith('ins-')&&x!=='ins-link'),link:c.classList.contains('ins-link')}))"""
INV = """()=>({page:document.querySelector('.page.active').id,filter:document.getElementById('invFilterSel').value,
  normal:document.getElementById('invNormalView').style.display!=='none',
  names:[...document.querySelectorAll('#invGrid .inv-card')].map(c=>c.innerText.split('\\n')[0].trim())})"""

PRODS = [{'id': 'p1', 'sku': 'SKU-1', 'name': 'Rice 5kg', 'stock': 0},
         {'id': 'p2', 'sku': 'SKU-2', 'name': 'Sugar 1kg', 'stock': 0},
         {'id': 'p3', 'sku': 'SKU-3', 'name': 'Soap Bar', 'stock': 3},
         {'id': 'p4', 'sku': 'SKU-4', 'name': 'Oil 1L', 'stock': 40}]

def page(br, url, prods, role='owner', lang='en', collection=False):
    ctx = br.new_context(viewport={'width': 360, 'height': 640}, user_agent=UA, has_touch=True, is_mobile=True, service_workers='block',
                         timezone_id='Africa/Douala', locale='fr-CM' if lang == 'fr' else 'en-US')
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(('http://127.0.0.1', 'data:', 'blob:')) else r.abort())
    p = ctx.new_page(); errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.goto(url); p.wait_for_timeout(1800)
    p.evaluate(SETUP, {'prods': prods, 'role': role, 'collection': collection})
    if lang == 'fr': p.evaluate("()=>{setLang('fr');go('dashboard')}")
    p.wait_for_timeout(300)
    return p, errs, ctx

def tap(p, text):
    p.evaluate("(t)=>{const c=[...document.querySelectorAll('#insightsFeed .insight-card')].find(c=>c.innerText.includes(t));c.scrollIntoView();}", text)
    p.locator('#insightsFeed .insight-card', has_text=text).first.click()
    p.wait_for_timeout(300)

def main():
    srv = _S(('127.0.0.1', 0), functools.partial(_H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_address[1]}/index.html'
    with sync_playwright() as pw:
        br = pw.chromium.launch()

        A = 'Stock alerts'
        p, errs, ctx = page(br, url, PRODS, collection=True)
        cards = p.evaluate(CARDS)
        out = [c for c in cards if 'out of stock' in c['txt']]
        low = [c for c in cards if 'low on stock' in c['txt']]
        chk(A, 'Out-of-stock alert is red (danger) and counts 2 products', len(out) == 1 and out[0]['txt'] == '2 products are out of stock' and out[0]['tone'] == 'ins-danger', cards)
        chk(A, 'Low-stock alert is orange (warn) and counts 1 product (singular wording)', len(low) == 1 and low[0]['txt'] == '1 product is low on stock' and low[0]['tone'] == 'ins-warn', cards)
        chk(A, 'Both stock alerts are tappable and explain what to do', out and low and out[0]['link'] and low[0]['link'] and 'restock' in out[0]['sub'] and 'Restock' in low[0]['sub'], cards)
        chk(A, 'The old combined "needs restocking" line is gone', not any('restocking' in c['txt'] for c in cards), cards)
        grp = p.evaluate("()=>{const f=document.getElementById('insightsFeed');const kids=[...f.children];const i=kids.findIndex(k=>k.classList.contains('ins-group')&&kids.indexOf(k)>0);const first=kids.filter(k=>k.classList.contains('insight-card')).slice(0,i>0?i:99).map(k=>k.innerText);return {first:kids[0].textContent,txt:f.innerText}}")
        chk(A, 'Both stock alerts sit under "Requires action"', grp['first'].lower().startswith('requires action') and grp['txt'].index('out of stock') < (grp['txt'].lower().find('review') if 'review' in grp['txt'].lower() else 10**6), grp)
        tap(p, 'out of stock')
        r = p.evaluate(INV)
        chk(A, 'Tap out-of-stock: Inventory opens filtered to Out of Stock, showing exactly Rice and Sugar', r['page'] == 'page-inventory' and r['filter'] == 'out' and sorted(r['names']) == ['Rice 5kg', 'Sugar 1kg'], r)
        p.evaluate("()=>go('dashboard')"); p.wait_for_timeout(300)
        tap(p, 'low on stock')
        r = p.evaluate(INV)
        chk(A, 'Tap low-stock: Inventory opens filtered to Low Stock, showing exactly Soap Bar', r['page'] == 'page-inventory' and r['filter'] == 'low' and r['names'] == ['Soap Bar'], r)
        p.evaluate("()=>{document.getElementById('invSearch').value='zzz';openLossRegisterView();go('dashboard')}"); p.wait_for_timeout(300)
        tap(p, 'out of stock')
        r = p.evaluate(INV)
        chk(A, 'From an open Loss Register view and an old search: back to the normal list, search cleared, filter applied', r['normal'] and r['filter'] == 'out' and sorted(r['names']) == ['Rice 5kg', 'Sugar 1kg'] and p.evaluate("()=>document.getElementById('invSearch').value") == '', r)
        p.evaluate("()=>go('dashboard')"); p.wait_for_timeout(300)
        A = 'Collection rate'
        cards = p.evaluate(CARDS)
        cr = [c for c in cards if 'Collection rate is only' in c['txt']]
        chk(A, 'Low collection-rate alert (20%) is tappable', len(cr) == 1 and cr[0]['link'] and '20%' in cr[0]['txt'], cards)
        tap(p, 'Collection rate is only')
        r = p.evaluate("()=>({page:document.querySelector('.page.active').id,coll:[...document.querySelectorAll('#collInsights .insight-card')].map(c=>c.innerText)})")
        chk(A, 'Tap opens the Collection page', r['page'] == 'page-collection', r)
        chk(A, 'Collection page insights unchanged: collection-rate line shown, no stock alerts there', any('Collection rate is only' in x for x in r['coll']) and not any('stock' in x for x in r['coll']), r)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        A = 'Edge cases'
        p, errs, ctx = page(br, url, [{'id': 'q1', 'sku': 'S1', 'name': 'Tea', 'stock': 50}])
        cards = p.evaluate(CARDS)
        chk(A, 'All products in stock: no stock alert at all', not any('stock' in c['txt'] for c in cards), cards)
        p.evaluate("()=>{S.add('products',{id:'q2',sku:'S2',name:'Milk',stock:0,lowStock:5,cost:1,price:2,status:'active'});go('dashboard')}"); p.wait_for_timeout(300)
        cards = p.evaluate(CARDS)
        chk(A, 'One product out of stock: singular wording, no low-stock alert', any(c['txt'] == '1 product is out of stock' for c in cards) and not any('low on stock' in c['txt'] for c in cards), cards)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        A = 'Permissions'
        p, errs, ctx = page(br, url, PRODS, role='cashier')
        can = p.evaluate("()=>Auth.can('manageInventory')")
        cards = p.evaluate(CARDS)
        out = [c for c in cards if 'out of stock' in c['txt']]
        chk(A, 'Cashier without inventory permission: alert shown but not tappable (same rule as the other alerts)', can is False and len(out) == 1 and not out[0]['link'], {'can': can, 'cards': cards})
        p.evaluate("()=>openInsight('stockout')"); p.wait_for_timeout(200)
        chk(A, 'Cashier: forcing the link does not open Inventory', p.evaluate("()=>document.querySelector('.page.active').id") != 'page-inventory')
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        A = 'EN/FR'
        p, errs, ctx = page(br, url, PRODS, lang='fr')
        cards = p.evaluate(CARDS)
        chk(A, 'FR: out-of-stock and low-stock alerts in French', any(c['txt'] == '2 produits en rupture de stock' for c in cards) and any(c['txt'] == '1 produit en stock faible' for c in cards), cards)
        keys = p.evaluate("()=>{const k=Object.keys(I18N_DICT.en).filter(x=>x.startsWith('ins_stock_'));return {n:k.length,missing:k.filter(x=>!I18N_DICT.fr[x]),same:k.filter(x=>I18N_DICT.fr[x]===I18N_DICT.en[x])}}")
        chk(A, 'All 6 new strings exist in EN and FR, FR translated', keys['n'] == 6 and not keys['missing'] and not keys['same'], keys)
        chk(A, '360 px: no sideways scroll on the dashboard', p.evaluate("()=>document.documentElement.scrollWidth") <= 360)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        br.close()
    srv.shutdown()
    fails = [r for r in RES if not r[2]]
    print(f'\nTOTAL {len(RES)} PASS {len(RES) - len(fails)} FAIL {len(fails)}')
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
