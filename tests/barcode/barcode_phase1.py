"""Bizora barcode identification, Phase 1 (product field, search, Stock In, POS scanner, CSV, backup).

Real Chromium, real app code, real IndexedDB origin, phone viewport 360x640 (Android user-agent).
Path-independent: serves the repository root on a free port. No outside network.

    python3 tests/barcode/barcode_phase1.py          # all checks, about 1-2 minutes
    python3 tests/barcode/barcode_phase1.py --perf   # also run the 10k / 100k product timings

Exit code 0 = every check passed. Camera scanning (Phase 2) is not covered here.
"""
import os, sys, json, time, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UA = 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36'
PERF = '--perf' in sys.argv

class _H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
class _S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True

RES = []
def chk(area, name, cond, info=''):
    RES.append((area, name, bool(cond)))
    print(('PASS' if cond else 'FAIL'), '|', area, '|', name, '' if cond else '| ' + json.dumps(info, ensure_ascii=False, default=str)[:600])

SETUP = """async(role)=>{
  window.__t=[];const _toast=window.toast;window.toast=(m,k,d)=>{window.__t.push(String(m));try{_toast(m,k,d)}catch(e){}};
  window.__dl=[];window.dl=(c,f,m)=>{window.__dl.push({c:String(c),f})};
  document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  if(typeof FirstRunWizard!=='undefined')FirstRunWizard.skip();
  const P='2026-01-05';
  S.add('products',{id:'pa',sku:'SKU-000001',name:'Coca-Cola 50cl',category:'Drinks',cost:250,price:350,stock:40,unit:'btl',tax:0,status:'active',added:P,barcode:'5449000000996'});
  S.add('products',{id:'pb',sku:'SKU-000002',name:'Rice 5kg',category:'Food',cost:3500,price:4500,stock:10,unit:'bag',tax:0,status:'active',added:P});
  S.add('products',{id:'pc',sku:'SKU-000003',name:'Soap Bar',category:'Hygiene',cost:150,price:250,stock:0,unit:'pcs',tax:0,status:'active',added:P,barcode:'6001234567890'});
  S.add('products',{id:'pd',sku:'SKU-000004',name:'Old Biscuit',category:'Food',cost:100,price:200,stock:5,unit:'pcs',tax:0,status:'discontinued',added:P,barcode:'7770001112223'});
  if(role!=='off'){const salt=genSalt();setAccessControl({enabled:true,pendingSetup:false,ownerPasswordHash:await hashPassword('owner99',salt),ownerPasswordSalt:salt,recoveryCodeHash:'x',recoveryCodeSalt:'x'});
    if(role!=='owner'){const c=await createEmployee({fullName:'Emp '+role,username:'u'+role,password:'1234',role});await Auth.loginEmployee(c.employee.id,'1234');}
    onEmployeeSessionStarted();}
  document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  return true}"""
PROD = """(id)=>{const p=S.get('products').find(x=>x.id===id);return p?{barcode:p.barcode,has:Object.prototype.hasOwnProperty.call(p,'barcode'),name:p.name,stock:p.stock,price:p.price}:null}"""
SAVEFORM = """(f)=>{window.__t=[];resetProdForm();if(f.edit)editProduct(f.edit);else openModal('mAddProd');
  const set=(id,v)=>{if(v!==undefined)document.getElementById(id).value=v};
  set('pName',f.name);set('pCost',f.cost);set('pPrice',f.price);set('pStock',f.stock);set('pBarcode',f.barcode);
  const before=S.get('products').length;saveProduct();
  return {count:S.get('products').length-before,open:document.getElementById('mAddProd').classList.contains('on'),toast:window.__t.slice(-1)[0]||'',err:document.getElementById('pBarcode').classList.contains('err')}}"""
SCAN = """(a)=>{const i=document.getElementById('posProdSearch');i.value=a.code;i.dispatchEvent(new Event('input'));
  const ev=new KeyboardEvent('keydown',{key:a.key||'Enter',bubbles:true,cancelable:true});i.dispatchEvent(ev);
  return {prevented:ev.defaultPrevented,cart:posItems.map(x=>({id:x.productId,qty:x.qty,price:x.price})),toast:window.__t.slice(-1)[0]||'',input:i.value}}"""

def page(br, url, role='off', lang='en', vw=360, vh=640):
    ctx = br.new_context(viewport={'width': vw, 'height': vh}, user_agent=UA, has_touch=True, is_mobile=True, service_workers='block',
                         timezone_id='Africa/Douala', locale='fr-CM' if lang == 'fr' else 'en-US')
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(('http://127.0.0.1', 'data:', 'blob:')) else r.abort())
    p = ctx.new_page(); errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.goto(url); p.wait_for_timeout(1800)
    p.evaluate(SETUP, role)
    if lang == 'fr': p.evaluate("()=>setLang('fr')")
    p.wait_for_timeout(200)
    return p, errs, ctx

def main():
    srv = _S(('127.0.0.1', 0), functools.partial(_H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_address[1]}/index.html'
    with sync_playwright() as pw:
        br = pw.chromium.launch()

        # ===================== PRODUCT FIELD =====================
        A = 'Product'
        p, errs, ctx = page(br, url)
        r = p.evaluate(SAVEFORM, {'name': 'Plain Tea', 'cost': '100', 'price': '150', 'stock': '5', 'barcode': ''})
        np = p.evaluate("()=>S.get('products').find(x=>x.name==='Plain Tea')")
        chk(A, 'Product without a barcode saves, and no barcode field is stored', r['count'] == 1 and np and 'barcode' not in np, {'r': r, 'p': np})
        r = p.evaluate(SAVEFORM, {'name': 'Milk 1L', 'cost': '500', 'price': '700', 'stock': '6', 'barcode': '0123456789012'})
        np = p.evaluate("()=>S.get('products').find(x=>x.name==='Milk 1L')")
        chk(A, 'Valid barcode saved as a string with its leading zero (0123456789012)', r['count'] == 1 and np and np.get('barcode') == '0123456789012', np)
        r = p.evaluate(SAVEFORM, {'name': 'Bread', 'cost': '200', 'price': '300', 'stock': '6', 'barcode': '  5000 1111 2222 3 \n'})
        np = p.evaluate("()=>S.get('products').find(x=>x.name==='Bread')")
        chk(A, 'Barcode normalized: surrounding and inner spaces / line breaks removed', np and np.get('barcode') == '5000111122223', np)
        r = p.evaluate(SAVEFORM, {'name': 'Fake Coke', 'cost': '1', 'price': '2', 'stock': '1', 'barcode': '5449000000996'})
        chk(A, 'Duplicate barcode (belongs to another product) refused; nothing saved; form stays open', r['count'] == 0 and r['open'] and 'Coca-Cola 50cl' in r['toast'] and r['err'], r)
        r = p.evaluate(SAVEFORM, {'name': 'Long Code', 'cost': '1', 'price': '2', 'stock': '1', 'barcode': 'X' * 65})
        r2 = p.evaluate(SAVEFORM, {'name': 'Accent Code', 'cost': '1', 'price': '2', 'stock': '1', 'barcode': 'ÉAN123'})
        chk(A, 'Invalid barcode (over 64 characters, or non-printable/accented) refused', r['count'] == 0 and r2['count'] == 0, [r, r2])
        before = p.evaluate(PROD, 'pa')
        r = p.evaluate(SAVEFORM, {'edit': 'pa', 'barcode': '5449000000996'})
        chk(A, 'Editing a product that keeps its own barcode is allowed', r['count'] == 0 and not r['open'] and p.evaluate(PROD, 'pa')['barcode'] == '5449000000996', r)
        chk(A, 'Edit form shows the existing barcode', p.evaluate("()=>{editProduct('pa');const v=document.getElementById('pBarcode').value;closeModal('mAddProd');return v}") == '5449000000996')
        r = p.evaluate(SAVEFORM, {'edit': 'pa', 'barcode': '5449000000989'})
        after = p.evaluate(PROD, 'pa')
        chk(A, 'Barcode replaced on edit; price, stock and name unchanged', after['barcode'] == '5449000000989' and after['price'] == before['price'] and after['stock'] == before['stock'] and after['name'] == before['name'], {'before': before, 'after': after})
        chk(A, 'Old barcode no longer finds the product after replacement', p.evaluate("()=>lookupBarcode('5449000000996').status") == 'unknown')
        r = p.evaluate(SAVEFORM, {'edit': 'pa', 'barcode': ''})
        after = p.evaluate(PROD, 'pa')
        chk(A, 'Barcode removed on edit: field deleted, product kept', after is not None and not after['has'], after)
        p.evaluate(SAVEFORM, {'edit': 'pa', 'barcode': '5449000000996'})
        chk(A, 'Reset clears the barcode field (Add Product after Edit)', p.evaluate("()=>{editProduct('pa');resetProdForm();return document.getElementById('pBarcode').value}") == '')
        chk(A, 'Product history shows the barcode', '5449000000996' in p.evaluate("()=>{openProductHistory('pa');const t=document.body.innerText;document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));return t}"))
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== SEARCH =====================
        A = 'Search'
        p, errs, ctx = page(br, url)
        p.evaluate("()=>go('pos')")
        res = p.evaluate("(c)=>{const i=document.getElementById('posProdSearch');i.value=c;searchPosProducts();return [...document.querySelectorAll('#posSearchResults .psr-name')].map(e=>e.textContent)}", '5449000000996')
        chk(A, 'POS: exact barcode lists that product first', res and res[0].startswith('Coca-Cola 50cl'), res)
        res = p.evaluate("(c)=>{const i=document.getElementById('posProdSearch');i.value=c;searchPosProducts();return [...document.querySelectorAll('#posSearchResults .psr-name')].map(e=>e.textContent)}", '544900000099')
        chk(A, 'POS: part of a barcode does not match (no fuzzy barcode match)', not any(x.startswith('Coca-Cola') for x in res), res)
        res = [p.evaluate("(c)=>{const i=document.getElementById('posProdSearch');i.value=c;searchPosProducts();return [...document.querySelectorAll('#posSearchResults .psr-name')].map(e=>e.textContent)}", q) for q in ('rice', 'SKU-000002', 'food')]
        chk(A, 'POS: existing name / SKU / category search still works', all(any(x.startswith('Rice 5kg') for x in r) for r in res), res)
        chk(A, 'POS: typing an exact barcode without Enter adds nothing to the cart', p.evaluate("()=>posItems.length") == 0)
        r = p.evaluate("()=>{go('products');const s=document.getElementById('prodSearch');s.value='6001234567890';filterProducts();return document.getElementById('page-products').innerText.includes('Soap Bar')}")
        r2 = p.evaluate("()=>{const s=document.getElementById('prodSearch');s.value='600123456789';filterProducts();return document.getElementById('page-products').innerText.includes('Soap Bar')}")
        chk(A, 'Products page: exact barcode finds the product; a partial barcode does not', r and not r2, [r, r2])
        r = p.evaluate("()=>{go('inventory');const s=document.getElementById('invSearch');s.value='5449000000996';filterInventory();return document.getElementById('page-inventory').innerText.includes('Coca-Cola 50cl')}")
        chk(A, 'Inventory page: exact barcode finds the product', r)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== STOCK IN =====================
        A = 'Stock In'
        p, errs, ctx = page(br, url)
        r = p.evaluate("""()=>{openStockIn();const b=document.getElementById('stockInBarcode');b.value='5449000000996';
          const ev=new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true});b.dispatchEvent(ev);
          return {sel:document.getElementById('stockInProd').value,msg:document.getElementById('stockInBarcodeMsg').textContent,focus:document.activeElement&&document.activeElement.id}}""")
        chk(A, 'Scanning an existing barcode selects the product and moves to Quantity', r['sel'] == 'pa' and 'Coca-Cola' in r['msg'] and r['focus'] == 'stockInQty', r)
        b = p.evaluate("()=>({stock:S.get('products').find(x=>x.id==='pa').stock,price:S.get('products').find(x=>x.id==='pa').price,cost:S.get('products').find(x=>x.id==='pa').cost,mv:S.get('stockMovements').length})")
        p.evaluate("()=>{document.getElementById('stockInQty').value='12';document.getElementById('stockInCost').value='240';saveStockIn()}")
        a = p.evaluate("()=>({stock:S.get('products').find(x=>x.id==='pa').stock,price:S.get('products').find(x=>x.id==='pa').price,cost:S.get('products').find(x=>x.id==='pa').cost,mv:S.get('stockMovements').length,last:S.get('stockMovements').slice(-1)[0]})")
        chk(A, 'Stock added through the existing Stock In save (+12, one stock-in movement)', a['stock'] == b['stock'] + 12 and a['mv'] == b['mv'] + 1 and (a['last'] or {}).get('type') == 'stock-in', {'b': b, 'a': a})
        chk(A, 'Barcode Stock In does not change selling price or product cost', a['price'] == b['price'] and a['cost'] == b['cost'], {'b': b, 'a': a})
        r = p.evaluate("""()=>{openStockIn();const b=document.getElementById('stockInBarcode');b.value='9999999999999';
          b.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
          return {sel:document.getElementById('stockInProd').value,msg:document.getElementById('stockInBarcodeMsg').textContent}}""")
        chk(A, 'Unknown barcode: clear message, no product selected', r['sel'] == '' and 'not found' in r['msg'].lower(), r)
        r = p.evaluate("""()=>{openStockIn();const b=document.getElementById('stockInBarcode');b.value='7770001112223';
          b.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
          return {sel:document.getElementById('stockInProd').value,msg:document.getElementById('stockInBarcodeMsg').textContent}}""")
        chk(A, 'Discontinued product: message, not selected (same rule as the dropdown)', r['sel'] == '' and 'discontinued' in r['msg'].lower(), r)
        r = p.evaluate("()=>{openStockIn();return {v:document.getElementById('stockInBarcode').value,m:document.getElementById('stockInBarcodeMsg').style.display}}")
        chk(A, 'Opening Stock In again clears the previous barcode and message', r['v'] == '' and r['m'] == 'none', r)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== POS / START A SALE =====================
        A = 'Sale'
        p, errs, ctx = page(br, url)
        p.evaluate("()=>{go('pos');resetPosForm()}")
        r = p.evaluate(SCAN, {'code': '5449000000996'})
        chk(A, 'Scan + Enter adds the product: quantity 1 at its saved selling price (350)', r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}] and r['prevented'] and r['input'] == '', r)
        r = p.evaluate(SCAN, {'code': '5449000000996'})
        chk(A, 'Same code again within 1 s is ignored as an accidental double scan', r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}] and 'twice' in r['toast'], r)
        p.wait_for_timeout(1100)
        r = p.evaluate(SCAN, {'code': '5449000000996'})
        chk(A, 'Same code after 1 s increases the quantity through the existing cart logic', r['cart'] == [{'id': 'pa', 'qty': 2, 'price': 350}], r)
        p.evaluate("()=>{resetPosForm();_bcLastScan={code:'',at:0}}")
        r = p.evaluate(SCAN, {'code': '5449000000996', 'key': 'Tab'})
        chk(A, 'Scanner that ends with Tab also adds the product', r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}] and r['prevented'], r)
        r = p.evaluate(SCAN, {'code': '1234567890123'})
        chk(A, 'Unknown barcode adds nothing and shows "Barcode not found"', len(r['cart']) == 1 and 'not found' in r['toast'].lower(), r)
        p.evaluate("()=>{window.__t=[]}")
        r = p.evaluate(SCAN, {'code': 'ABC-XYZ-999'})
        chk(A, 'Unknown letters-and-digits code (e.g. Code 128) adds nothing and shows "Barcode not found"', len(r['cart']) == 1 and 'not found' in r['toast'].lower(), r)
        p.evaluate("()=>{window.__t=[]}")
        r = p.evaluate(SCAN, {'code': '12345'})
        chk(A, 'Unknown short code adds nothing and shows "Barcode not found"', len(r['cart']) == 1 and 'not found' in r['toast'].lower(), r)
        p.evaluate("()=>{window.__t=[]}")
        r = p.evaluate(SCAN, {'code': '6001234567890'})
        chk(A, 'Out-of-stock product is not added (existing stock rule)', len(r['cart']) == 1 and r['toast'] == p.evaluate("()=>t('toast_not_enough_stock')"), r)
        r = p.evaluate(SCAN, {'code': 'rice'})
        chk(A, 'Enter on a normal name search adds nothing and shows no barcode message', len(r['cart']) == 1 and 'barcode' not in r['toast'].lower(), r)
        stock_before = p.evaluate("()=>S.get('products').find(x=>x.id==='pa').stock")
        p.evaluate("""()=>{document.getElementById('posReceived').value='1000';calcPosTotals();document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();}""")
        p.wait_for_timeout(400)
        r = p.evaluate("()=>{const s=S.get('posSales').slice(-1)[0];return {total:s&&s.total,items:s&&s.items.map(i=>i.name+'x'+i.qty),stock:S.get('products').find(x=>x.id==='pa').stock}}")
        chk(A, 'Checkout with a scanned item completes through the existing sale (total 350, stock -1)', r['total'] == 350 and r['items'] == ['Coca-Cola 50cl x1'.replace(' x', 'x')] and r['stock'] == stock_before - 1, r)
        p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));resetPosForm();_bcLastScan={code:'',at:0}}")
        p.evaluate("()=>{const a=S.get('products');a.push({id:'px',sku:'SKU-000099',name:'Clone',category:'X',cost:1,price:2,stock:9,unit:'pcs',tax:0,status:'active',added:'2026-01-05',barcode:'5449000000996'});S.set('products',a)}")
        r = p.evaluate(SCAN, {'code': '5449000000996'})
        chk(A, 'Barcode on two products (e.g. after a restore) is never guessed: nothing added, clear message', r['cart'] == [] and 'more than one' in r['toast'], r)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== ROLES =====================
        A = 'Roles'
        p, errs, ctx = page(br, url, role='cashier')
        p.evaluate("()=>{go('pos');resetPosForm()}")
        r = p.evaluate(SCAN, {'code': '5449000000996'})
        chk(A, 'Cashier can scan a product into a sale', r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}], r)
        r = p.evaluate(SAVEFORM, {'edit': 'pa', 'barcode': '1111111111111'})
        chk(A, 'Cashier cannot change a product barcode (existing editProducts rule)', p.evaluate(PROD, 'pa')['barcode'] == '5449000000996', r)
        r = p.evaluate(SAVEFORM, {'name': 'Cashier Item', 'cost': '1', 'price': '2', 'stock': '1', 'barcode': '2222222222222'})
        chk(A, 'Cashier cannot add a product with a barcode (existing addProducts rule)', r['count'] == 0, r)
        b = p.evaluate("()=>S.get('products').find(x=>x.id==='pa').stock")
        p.evaluate("()=>{openStockIn();const e=document.getElementById('stockInBarcode');e.value='5449000000996';stockInBarcodeResolve();document.getElementById('stockInQty').value='5';saveStockIn()}")
        chk(A, 'Cashier cannot receive stock by scanning (existing manageInventory rule)', p.evaluate("()=>S.get('products').find(x=>x.id==='pa').stock") == b)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== CSV + BACKUP =====================
        A = 'Data'
        p, errs, ctx = page(br, url)
        r = p.evaluate("()=>{window.__dl=[];exportCSV('products');const d=window.__dl.slice(-1)[0];return d?d.c:''}")
        lines = r.split('\n')
        chk(A, 'CSV export has a Barcode column with the value (leading zeros kept as text)', lines[0].endswith(',Barcode') and any('"5449000000996"' in l for l in lines[1:]), lines[:3])
        imp = """(csv)=>{csvImportTypeActive='products';const {headers,rows}=parseCSV(csv);buildCsvPreview('products',headers,rows);
          const prev=csvParsedRows.map(r=>({valid:r.valid,dup:r.dup&&r.dup.kind,bc:r.data.barcode}));const before=S.get('products').length;commitCsvImport();
          return {prev,added:S.get('products').length-before,toasts:window.__t.slice(-2)}}"""
        r = p.evaluate(imp, 'name,cost,price,stock,barcode\nJuice,300,500,10,0099887766554\nWater,100,200,10,5449000000996\nTea Box,100,200,10,0099887766554\nSugar 1kg,600,800,10,\n')
        juice = p.evaluate("()=>S.get('products').find(x=>x.name==='Juice')")
        sugar = p.evaluate("()=>S.get('products').find(x=>x.name==='Sugar 1kg')")
        chk(A, 'CSV import: new barcode imported as text with its leading zeros', juice and juice.get('barcode') == '0099887766554', juice)
        chk(A, 'CSV import: barcode already used by a product is refused', [x['dup'] for x in r['prev']][1] == 'bc_existing' and not p.evaluate("()=>S.get('products').some(x=>x.name==='Water')"), r)
        chk(A, 'CSV import: barcode repeated inside the file is refused', [x['dup'] for x in r['prev']][2] == 'bc_file' and not p.evaluate("()=>S.get('products').some(x=>x.name==='Tea Box')"), r)
        chk(A, 'CSV import: empty barcode cell imports the product with no barcode field', sugar and 'barcode' not in sugar, sugar)
        r = p.evaluate(imp, 'name,cost,price,stock\nOld File Item,100,200,3\n')
        chk(A, 'Old CSV without a barcode column still imports', r['added'] == 1, r)
        chk(A, 'Imported barcode works at once in the POS', p.evaluate("()=>lookupBarcode('0099887766554').status") == 'ok')
        backup = p.evaluate("()=>{window.__dl=[];exportBackup();const d=window.__dl.slice(-1)[0];return d?d.c:''}")
        ctx.close()
        chk(A, 'Backup file contains the barcodes', '"barcode": "5449000000996"' in backup and '"barcode": "0099887766554"' in backup)
        p, errs, ctx = page(br, url)   # second, separate origin profile is NOT guaranteed; restore into this one after wiping products
        p.evaluate("()=>{S.set('products',[]);invalidateBarcodeIndex()}")
        p.evaluate("(json)=>{window.__t=[];handleFile(new File([json],'bizora_backup.json',{type:'application/json'}))}", backup)
        p.wait_for_function("()=>document.getElementById('mConfirm').classList.contains('on')", timeout=5000)
        p.evaluate("()=>document.getElementById('mConfirmBtn').click()"); p.wait_for_timeout(600)
        r = p.evaluate("()=>({coke:(S.get('products').find(x=>x.id==='pa')||{}).barcode,juice:(S.get('products').find(x=>x.name==='Juice')||{}).barcode,look:lookupBarcode('0099887766554').status})")
        chk(A, 'Restore brings the barcodes back exactly, and they scan at once', r == {'coke': '5449000000996', 'juice': '0099887766554', 'look': 'ok'}, r)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== EN / FR, 360 px =====================
        A = 'EN/FR'
        for lang in ('en', 'fr'):
            p, errs, ctx = page(br, url, lang=lang)
            r = p.evaluate("""()=>{resetProdForm();openModal('mAddProd');const lab=document.querySelector('label[data-i18n=bc_lbl_barcode]').textContent;
               const ph=document.getElementById('pBarcode').placeholder;const w=document.getElementById('mAddProd').querySelector('.modal').scrollWidth<=innerWidth;closeModal('mAddProd');
               openStockIn();const ph2=document.getElementById('stockInBarcode').placeholder;const w2=document.documentElement.scrollWidth<=innerWidth;closeModal('mStockIn');
               return {lab,ph,ph2,w,w2,msg:t('bc_not_found')}}""")
            exp = {'en': ('Barcode', 'Barcode not found'), 'fr': ('Code-barres', 'Code-barres introuvable')}[lang]
            chk(A, f'{lang.upper()}: barcode label, placeholders and messages in {lang.upper()}; no overflow at 360 px',
                r['lab'] == exp[0] and r['msg'].startswith(exp[1]) and r['ph'] and r['ph2'] and r['w'] and r['w2'], r)
            chk(A, f'{lang.upper()}: no JS errors', not errs, errs)
            ctx.close()

        # ===================== PERFORMANCE =====================
        if PERF:
            A = 'Perf'
            p, errs, ctx = page(br, url, vw=360)
            for n in (10000, 100000):
                r = p.evaluate("""(n)=>{const a=[];for(let i=0;i<n;i++)a.push({id:'q'+i,sku:'SKU-'+i,name:'Item '+i,category:'C'+(i%40),cost:1,price:2,stock:5,unit:'pcs',tax:0,status:'active',added:'2026-01-05',barcode:i%2?String(1000000000000+i):undefined});
                  MEM.products=a;invalidateBarcodeIndex();
                  let t0=performance.now();lookupBarcode('x');const build=performance.now()-t0;
                  t0=performance.now();let hits=0;for(let k=0;k<1000;k++){if(lookupBarcode(String(1000000000000+((k*97)|1)%n)).status==='ok')hits++;}const look=(performance.now()-t0)/1000;
                  t0=performance.now();for(let k=0;k<1000;k++)lookupBarcode('9'+k);const miss=(performance.now()-t0)/1000;
                  t0=performance.now();barcodeOwner('1000000000001','zz');const owner=performance.now()-t0;
                  const i=document.getElementById('posProdSearch');go('pos');i.value=String(1000000000000+(n-1));t0=performance.now();searchPosProducts();const kw=performance.now()-t0;
                  return {n,build:+build.toFixed(1),lookupHit:+look.toFixed(3),lookupMiss:+miss.toFixed(4),saveCheck:+owner.toFixed(1),posKeystroke:+kw.toFixed(1),hits}}""", n)
                print('PERF', json.dumps(r))
                chk(A, f'{n:,} products: index build < 300 ms, exact lookup < 5 ms, miss < 0.1 ms, save check < 200 ms',
                    r['build'] < 300 and r['lookupHit'] < 5 and r['lookupMiss'] < 0.1 and r['saveCheck'] < 200 and r['hits'] > 0, r)
            ctx.close()

        br.close()
    srv.shutdown()
    p_ = sum(c for _, _, c in RES); t_ = len(RES)
    print(f'\nTOTAL {t_} PASS {p_} FAIL {t_ - p_}')
    sys.exit(0 if p_ == t_ else 1)

if __name__ == '__main__':
    main()
