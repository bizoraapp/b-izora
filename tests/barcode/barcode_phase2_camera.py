"""Bizora barcode Phase 2: phone-camera scanning (native BarcodeDetector), behind FeatureFlags.barcodeScanning.

Real Chromium, real app code, real IndexedDB origin, phone viewport 360x640 (Android user-agent).
Path-independent: serves the repository root on a free port. No outside network.

Desktop/headless Chromium has no BarcodeDetector and no camera, so this suite installs two stand-ins
before the app loads (test only, nothing is added to the app):
  - window.BarcodeDetector: returns whatever the test puts in window.__cam.next, on every frame
    (the same code over and over, like a real camera holding a barcode in view);
  - navigator.mediaDevices.getUserMedia: a real MediaStream from a small canvas, or a refusal /
    no-camera error, so the stop() of every track can be checked.
Real decoding of real barcodes is NOT covered here: that is the Android phone test.

    python3 tests/barcode/barcode_phase2_camera.py

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

MOCK = """
window.__cam={next:null,mode:'ok',formats:null,tracks:[],gum:0,detect:0,constraints:null,asked:null,delay:0,
  devices:null,defaultId:'',opened:[],applied:[],caps:null,failIds:[]};
window.BarcodeDetector=class{
  constructor(o){window.__cam.asked=o&&o.formats;}
  static async getSupportedFormats(){return window.__cam.formats||['aztec','code_128','code_39','data_matrix','ean_13','ean_8','itf','qr_code','upc_a','upc_e'];}
  async detect(src){window.__cam.detect++;const n=window.__cam.next;return n?n.map(x=>({...x})):[];}
};
if(navigator.mediaDevices){navigator.mediaDevices.getUserMedia=async(c)=>{
  const k=window.__cam;k.gum++;k.constraints=c;
  if(k.delay)await new Promise(r=>setTimeout(r,k.delay));
  if(k.mode==='deny')throw new DOMException('Permission denied','NotAllowedError');
  if(k.mode==='nocam')throw new DOMException('Requested device not found','NotFoundError');
  if(k.mode==='busy')throw new DOMException('Could not start video source','NotReadableError');
  const ex=c&&c.video&&c.video.deviceId&&c.video.deviceId.exact;const id=ex||k.defaultId||'';
  if(ex&&k.devices&&!k.devices.some(d=>d.deviceId===ex))throw new DOMException('No such camera','OverconstrainedError');
  if(k.failIds.includes(id))throw new DOMException('Could not start video source','NotReadableError');
  k.opened.push(id);
  const cv=document.createElement('canvas');cv.width=160;cv.height=120;const g=cv.getContext('2d');
  let st;
  if(k.mode==='nopic'){st=cv.captureStream(0);} // never delivers a picture
  else{let i=0;const draw=()=>{g.fillStyle=(i++%2)?'#222':'#ddd';g.fillRect(0,0,160,120);};draw();
    st=cv.captureStream(15);setInterval(draw,60);} // test stand-in only
  const dev=(k.devices||[]).find(d=>d.deviceId===id);
  st.getVideoTracks().forEach(tr=>{tr.getSettings=()=>({deviceId:id});tr.getCapabilities=()=>k.caps||{};
    tr.applyConstraints=async(x)=>{k.applied.push({id,x});};if(dev)Object.defineProperty(tr,'label',{get:()=>dev.label});});
  k.tracks.push(...st.getTracks());return st;};
  navigator.mediaDevices.enumerateDevices=async()=>(window.__cam.devices||[]).map(d=>({kind:'videoinput',groupId:'',...d}));}
"""

SETUP = """async(role)=>{
  window.__t=[];const _toast=window.toast;window.toast=(m,k,d)=>{window.__t.push(String(m));try{_toast(m,k,d)}catch(e){}};
  document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  if(typeof FirstRunWizard!=='undefined')FirstRunWizard.skip();
  const P='2026-01-05';
  S.add('products',{id:'pa',sku:'SKU-000001',name:'Coca-Cola 50cl',category:'Drinks',cost:250,price:350,stock:40,unit:'btl',tax:0,status:'active',added:P,barcode:'5449000000996'});
  S.add('products',{id:'pb',sku:'SKU-000002',name:'Rice 5kg',category:'Food',cost:3500,price:4500,stock:10,unit:'bag',tax:0,status:'active',added:P});
  S.add('products',{id:'pc',sku:'SKU-000003',name:'Soap Bar',category:'Hygiene',cost:150,price:250,stock:0,unit:'pcs',tax:0,status:'active',added:P,barcode:'6001234567890'});
  S.add('products',{id:'pz',sku:'SKU-000004',name:'Zero Gum',category:'Food',cost:50,price:100,stock:9,unit:'pcs',tax:0,status:'active',added:P,barcode:'01234565'});
  if(role!=='off'){const salt=genSalt();setAccessControl({enabled:true,pendingSetup:false,ownerPasswordHash:await hashPassword('owner99',salt),ownerPasswordSalt:salt,recoveryCodeHash:'x',recoveryCodeSalt:'x'});
    if(role!=='owner'){const c=await createEmployee({fullName:'Emp '+role,username:'u'+role,password:'1234',role});await Auth.loginEmployee(c.employee.id,'1234');}
    onEmployeeSessionStarted();}
  document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  return true}"""

STATE = """()=>({open:BarcodeCamera.isOpen(),on:document.getElementById('bcCamOverlay').classList.contains('on'),
  err:document.getElementById('bcCamOverlay').classList.contains('err'),status:document.getElementById('bcCamStatus').textContent,
  live:window.__cam.tracks.filter(t=>t.readyState==='live').length,tracks:window.__cam.tracks.length,gum:window.__cam.gum,detect:window.__cam.detect,
  src:!!document.getElementById('bcCamVideo').srcObject,
  cart:posItems.map(x=>({id:x.productId,qty:x.qty,price:x.price})),toast:window.__t.slice(-1)[0]||'',toasts:window.__t.slice()})"""

BTN = {'pos': 'button[onclick="bcCamToPos()"]', 'form': 'button[onclick="bcCamToProductForm()"]',
       'stock': 'button[onclick="bcCamToStockIn()"]', 'search': 'button[onclick="bcCamToProductSearch()"]'}

def page(br, url, role='off', lang='en', flag=True, mock=True):
    ctx = br.new_context(viewport={'width': 360, 'height': 640}, user_agent=UA, has_touch=True, is_mobile=True, service_workers='block',
                         timezone_id='Africa/Douala', locale='fr-CM' if lang == 'fr' else 'en-US')
    net = []
    def route(r):
        u = r.request.url
        if u.startswith(('data:', 'blob:')): return r.continue_()
        if u.startswith('http://127.0.0.1'):
            net.append(u); return r.continue_()
        net.append(u); return r.abort()
    ctx.route('**/*', route)
    if mock: ctx.add_init_script(MOCK)
    p = ctx.new_page(); errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.goto(url + ('?barcodecam=1' if flag else '')); p.wait_for_timeout(1800)
    p.evaluate(SETUP, role)
    if lang == 'fr': p.evaluate("()=>setLang('fr')")
    p.wait_for_timeout(200)
    return p, errs, ctx, net

def scan(p, btn, code, fmt='ean_13', prep=None, wait_close=True):
    """Tap the camera button with `code` in view; wait until the scanner closes by itself."""
    if prep: p.evaluate(prep)
    p.evaluate("(a)=>{window.__t=[];window.__cam.next=a.code===null?null:[{format:a.fmt,rawValue:a.code}]}", {'code': code, 'fmt': fmt})
    p.click(BTN[btn])
    if wait_close:
        p.wait_for_function("()=>!BarcodeCamera.isOpen()", timeout=8000)
        p.wait_for_timeout(150)
    return p.evaluate(STATE)

def main():
    srv = _S(('127.0.0.1', 0), functools.partial(_H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_address[1]}/index.html'
    with sync_playwright() as pw:
        br = pw.chromium.launch()

        # ===================== FEATURE FLAG =====================
        A = 'Flag'
        p, errs, ctx, net = page(br, url, flag=False)
        r = p.evaluate("""()=>{go('pos');const vis=s=>{const b=document.querySelector(s);return !!(b&&b.offsetParent)};
          return {flag:FeatureFlags.isEnabled('barcodeScanning'),def:FeatureFlags.getAll().barcodeScanning,cls:document.documentElement.classList.contains('bc-cam-on'),
                  pos:vis('button[onclick="bcCamToPos()"]')}}""")
        chk(A, 'Default: FeatureFlags.barcodeScanning is false and the POS camera button is hidden', r['flag'] is False and r['def'] is False and not r['cls'] and not r['pos'], r)
        r = p.evaluate("""()=>{const vis=s=>{const b=document.querySelector(s);return !!(b&&b.offsetParent)};
          go('products');const s1=vis('button[onclick="bcCamToProductSearch()"]');
          resetProdForm();openModal('mAddProd');const s2=vis('button[onclick="bcCamToProductForm()"]');closeModal('mAddProd');
          openStockIn();const s3=vis('button[onclick="bcCamToStockIn()"]');closeModal('mStockIn');return [s1,s2,s3]}""")
        chk(A, 'Default: camera buttons hidden on Products search, product form and Stock In', r == [False, False, False], r)
        p.evaluate("()=>BarcodeCamera.open(()=>{window.__cb=1})"); p.wait_for_timeout(300)
        r = p.evaluate(STATE)
        chk(A, 'Default: BarcodeCamera.open() refuses with the flag off (no camera request, no overlay)', r['gum'] == 0 and not r['on'] and not r['open'], r)
        chk(A, 'Default: no JS errors', not errs, errs)
        ctx.close()

        p, errs, ctx, net = page(br, url, flag=True)
        r = p.evaluate("""()=>{const vis=s=>{const b=document.querySelector(s);return !!(b&&b.offsetParent)};
          go('pos');const a=vis('button[onclick="bcCamToPos()"]');go('products');const b=vis('button[onclick="bcCamToProductSearch()"]');
          resetProdForm();openModal('mAddProd');const c=vis('button[onclick="bcCamToProductForm()"]');closeModal('mAddProd');
          openStockIn();const d=vis('button[onclick="bcCamToStockIn()"]');closeModal('mStockIn');
          return {flag:FeatureFlags.isEnabled('barcodeScanning'),btns:[a,b,c,d]}}""")
        chk(A, '?barcodecam=1 turns the flag on for this device; all 4 camera buttons show', r['flag'] is True and r['btns'] == [True] * 4, r)
        p.goto(url + '?barcodecam=0'); p.wait_for_timeout(1500)
        r = p.evaluate("()=>({flag:FeatureFlags.isEnabled('barcodeScanning'),cls:document.documentElement.classList.contains('bc-cam-on')})")
        chk(A, '?barcodecam=0 turns it off again', r == {'flag': False, 'cls': False}, r)
        chk(A, 'Switch: no JS errors', not errs, errs)
        ctx.close()

        # ===================== SUPPORT / PERMISSION =====================
        A = 'Support'
        p, errs, ctx, net = page(br, url)
        p.evaluate("()=>go('pos')")
        p.evaluate("()=>{window.__BD=window.BarcodeDetector;delete window.BarcodeDetector;window.__t=[]}")
        p.click(BTN['pos']); p.wait_for_timeout(300)
        r = p.evaluate(STATE)
        chk(A, 'No BarcodeDetector: clear message, no camera request, scanner not opened', r['gum'] == 0 and not r['on'] and "isn’t supported" in r['toast'], r)
        p.evaluate("()=>{window.BarcodeDetector=window.__BD;window.__cam.formats=['qr_code','aztec'];window.__t=[]}")
        p.click(BTN['pos']); p.wait_for_timeout(400)
        r = p.evaluate(STATE)
        chk(A, 'Detector without any retail format (QR only): unsupported message in the scanner, no camera request', r['gum'] == 0 and r['on'] and r['err'] and "isn’t supported" in r['status'], r)
        p.click('#bcCamOverlay .modal-ftr button[data-i18n="btn_cancel"]'); p.wait_for_timeout(200)
        p.evaluate("()=>{window.__cam.formats=null;window.__cam.mode='deny'}")
        p.click(BTN['pos']); p.wait_for_timeout(400)
        r = p.evaluate(STATE)
        chk(A, 'Permission refused: message shown in the scanner, video hidden, nothing running', r['on'] and r['err'] and 'refused' in r['status'] and r['live'] == 0 and not r['src'] and r['cart'] == [], r)
        p.click('#bcCamOverlay .modal-close'); p.wait_for_timeout(200)
        r = p.evaluate(STATE)
        chk(A, 'Permission refused: Close hides the scanner', not r['on'] and not r['open'], r)
        p.evaluate("()=>{window.__cam.mode='nocam'}"); p.click(BTN['pos']); p.wait_for_timeout(400)
        r = p.evaluate(STATE)
        chk(A, 'No camera on the device: clear message', r['err'] and 'No camera' in r['status'], r)
        p.evaluate("()=>BarcodeCamera.close()")
        p.evaluate("()=>{window.__cam.mode='busy'}"); p.click(BTN['pos']); p.wait_for_timeout(400)
        r = p.evaluate(STATE)
        chk(A, 'Camera busy / cannot start: clear message', r['err'] and 'could not be started' in r['status'], r)
        p.evaluate("()=>{BarcodeCamera.close();window.__cam.mode='ok'}")
        r = p.evaluate("()=>window.__cam.asked")
        p.click(BTN['pos']); p.wait_for_timeout(500)
        r = p.evaluate("()=>({asked:window.__cam.asked,c:window.__cam.constraints})")
        chk(A, 'Detector asked only for EAN-13, EAN-8, UPC-A, UPC-E, Code 128; rear camera, no audio',
            sorted(r['asked'] or []) == ['code_128', 'ean_13', 'ean_8', 'upc_a', 'upc_e'] and r['c']['audio'] is False and r['c']['video']['facingMode'] == {'ideal': 'environment'}, r)
        r = p.evaluate(STATE)
        chk(A, 'Scanning state: "Point the camera" message, live camera, no error', r['on'] and not r['err'] and 'Point the camera' in r['status'] and r['live'] >= 1, r)
        p.evaluate("()=>{BarcodeCamera._s.started-=9000}"); p.wait_for_timeout(500)
        r = p.evaluate(STATE)
        chk(A, 'Nothing detected after 8 s: helpful hint shown, scanner keeps looking', r['open'] and not r['err'] and 'No barcode detected yet' in r['status'] and r['live'] >= 1, r)
        p.evaluate("()=>BarcodeCamera.close()")
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== POS =====================
        A = 'POS'
        p, errs, ctx, net = page(br, url)
        p.evaluate("()=>go('pos')")
        net0 = len(net)  # requests made by the page load itself are not part of scanning
        r = scan(p, 'pos', '5449000000996')
        chk(A, 'Known barcode: product added once at its saved price (350)', r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}], r)
        chk(A, 'Success: scanner closed, every camera track stopped, video released', not r['on'] and r['live'] == 0 and r['tracks'] >= 1 and not r['src'], r)
        d0 = r['detect']; p.wait_for_timeout(900); r = p.evaluate(STATE)
        chk(A, 'Same barcode held in view on many frames: still added only once; detection loop stopped', r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}] and r['detect'] == d0, {'d0': d0, 'r': r})
        p.evaluate("()=>{_bcLastScan={code:'5449000000996',at:Date.now()}}")  # a scan "just now"
        r = scan(p, 'pos', '5449000000996')
        chk(A, 'Same barcode again within 1 s (Phase 1 guard reused): ignored', r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}] and 'scanned twice' in r['toast'], r)
        p.evaluate("()=>{_bcLastScan={code:'',at:0}}")
        r = scan(p, 'pos', '5449000000996')
        chk(A, 'Same barcode scanned again later: quantity 2 (existing cart rule)', r['cart'] == [{'id': 'pa', 'qty': 2, 'price': 350}], r)
        prods0 = p.evaluate("()=>JSON.stringify(S.get('products'))")
        r = scan(p, 'pos', '9999999999994')
        chk(A, 'Unknown barcode: nothing added, "Barcode not found", products unchanged', r['cart'] == [{'id': 'pa', 'qty': 2, 'price': 350}] and 'Barcode not found' in r['toast'] and p.evaluate("()=>JSON.stringify(S.get('products'))") == prods0, r)
        r = scan(p, 'pos', '544900000099', fmt='upc_a')
        chk(A, 'Part of a known barcode (12 of 13 digits): not found, never matched to that product', r['cart'] == [{'id': 'pa', 'qty': 2, 'price': 350}] and 'Barcode not found' in r['toast'], r)
        r = scan(p, 'pos', '6001234567890')
        chk(A, 'Out-of-stock product: refused with the existing stock message, nothing added', r['cart'] == [{'id': 'pa', 'qty': 2, 'price': 350}] and 'stock' in r['toast'].lower(), r)
        r = scan(p, 'pos', '01234565', fmt='ean_8')
        chk(A, 'Leading zero kept: EAN-8 01234565 finds its product (string, not number)', any(x['id'] == 'pz' for x in r['cart']), r)
        p.evaluate("()=>{const pr=S.get('products');pr.push({id:'pd1',sku:'SKU-9',name:'Dup A',cost:1,price:2,stock:5,status:'active',barcode:'4006381333931'},{id:'pd2',sku:'SKU-10',name:'Dup B',cost:1,price:2,stock:5,status:'active',barcode:'4006381333931'});S.set('products',pr);invalidateBarcodeIndex()}")
        n0 = len(p.evaluate(STATE)['cart'])
        r = scan(p, 'pos', '4006381333931')
        chk(A, 'Barcode on two products: refused as ambiguous, nothing added', len(r['cart']) == n0 and 'more than one product' in r['toast'], r)
        p.evaluate("()=>{window.__t=[];window.__cam.next=[{format:'qr_code',rawValue:'5449000000996'}]}")
        p.click(BTN['pos']); p.wait_for_timeout(700)
        r = p.evaluate(STATE)
        chk(A, 'A QR code is ignored (no QR workflow): scanner keeps looking, nothing added', r['open'] and len(r['cart']) == n0, r)
        p.evaluate("()=>BarcodeCamera.close()")
        r = p.evaluate("()=>{const s=document.getElementById('posProdSearch');return {v:s.value}}")
        chk(A, 'Camera scans do not leave text in the POS search box', r['v'] == '', r)
        chk(A, 'No network request of any kind during camera scanning (frames stay on the phone)', net[net0:] == [], net[net0:])
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== CASHIER: same result as the keyboard scanner =====================
        A = 'Cashier'
        out = {}
        for how in ('camera', 'keyboard'):
            p, errs, ctx, net = page(br, url, role='cashier')
            p.evaluate("()=>go('pos')")
            res = []
            for code in ('5449000000996', '6001234567890', '9999999999994'):
                p.evaluate("()=>{_bcLastScan={code:'',at:0}}")
                if how == 'camera':
                    r = scan(p, 'pos', code)
                else:
                    r = p.evaluate("""(c)=>{window.__t=[];const i=document.getElementById('posProdSearch');i.value=c;i.dispatchEvent(new Event('input'));
                      i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));return {cart:posItems.map(x=>({id:x.productId,qty:x.qty,price:x.price})),toast:window.__t.slice(-1)[0]||''}}""", code)
                res.append({'cart': r['cart'], 'toast': r['toast']})
            out[how] = res
            chk(A, f'Cashier ({how}): no JS errors', not errs, errs)
            ctx.close()
        chk(A, 'Cashier: camera gives exactly the same cart and messages as the scanner gun (known, out of stock, unknown)', out['camera'] == out['keyboard'], out)

        # ===================== PRODUCT FORM / SEARCH / STOCK IN =====================
        A = 'Workflows'
        p, errs, ctx, net = page(br, url)
        p.evaluate("()=>{go('products');resetProdForm();openModal('mAddProd');document.getElementById('pName').value='Milk 1L';document.getElementById('pCost').value='500';document.getElementById('pPrice').value='700';document.getElementById('pStock').value='6'}")
        n0 = p.evaluate("()=>S.get('products').length")
        r = scan(p, 'form', '0123456789012')
        f = p.evaluate("()=>({v:document.getElementById('pBarcode').value,open:document.getElementById('mAddProd').classList.contains('on'),n:S.get('products').length})")
        chk(A, 'Product form: scanned barcode fills the Barcode field exactly (leading zero kept)', f['v'] == '0123456789012', f)
        chk(A, 'Product form: scanning does not save; the form stays open', f['open'] and f['n'] == n0, f)
        chk(A, 'Product form: camera stopped after the scan', r['live'] == 0 and not r['on'], r)
        p.evaluate("()=>saveProduct()")
        np = p.evaluate("()=>S.get('products').find(x=>x.name==='Milk 1L')")
        chk(A, 'Product form: Save stores the scanned barcode through saveProduct()', np and np.get('barcode') == '0123456789012', np)
        p.evaluate("()=>{resetProdForm();openModal('mAddProd');document.getElementById('pName').value='Fake Coke';document.getElementById('pCost').value='1';document.getElementById('pPrice').value='2';document.getElementById('pStock').value='1'}")
        scan(p, 'form', '5449000000996')
        r = p.evaluate("()=>{window.__t=[];const n=S.get('products').length;saveProduct();return {added:S.get('products').length-n,toast:window.__t.slice(-1)[0]||''}}")
        chk(A, 'Product form: a scanned barcode that belongs to another product is refused on Save (existing check)', r['added'] == 0 and 'Coca-Cola 50cl' in r['toast'], r)
        p.evaluate("()=>closeModal('mAddProd')")
        r = scan(p, 'search', '6001234567890', prep="()=>go('products')")
        s = p.evaluate("()=>({v:document.getElementById('prodSearch').value,soap:document.getElementById('page-products').innerText.includes('Soap Bar'),coke:document.getElementById('page-products').innerText.includes('Coca-Cola 50cl')})")
        chk(A, 'Products search: scanned barcode shows exactly that product', s['v'] == '6001234567890' and s['soap'] and not s['coke'], s)
        r = scan(p, 'search', '9999999999994')
        s2 = p.evaluate("()=>document.getElementById('prodSearch').value")
        chk(A, 'Products search: unknown barcode says "not found" and leaves the search unchanged', 'Barcode not found' in r['toast'] and s2 == '6001234567890', {'r': r['toast'], 's': s2})
        stock0 = p.evaluate("()=>S.get('products').find(x=>x.id==='pa').stock")
        r = scan(p, 'stock', '5449000000996', prep="()=>openStockIn()")
        s = p.evaluate("()=>({sel:document.getElementById('stockInProd').value,msg:document.getElementById('stockInBarcodeMsg').textContent,bc:document.getElementById('stockInBarcode').value,open:document.getElementById('mStockIn').classList.contains('on')})")
        chk(A, 'Stock In: scanned barcode selects the product in the existing list', s['sel'] == 'pa' and 'Coca-Cola' in s['msg'] and s['bc'] == '5449000000996' and s['open'], s)
        chk(A, 'Stock In: stock unchanged until the user saves (saveStockIn() not called)', p.evaluate("()=>S.get('products').find(x=>x.id==='pa').stock") == stock0)
        r = scan(p, 'stock', '9999999999994')
        s = p.evaluate("()=>({sel:document.getElementById('stockInProd').value,msg:document.getElementById('stockInBarcodeMsg').textContent})")
        chk(A, 'Stock In: unknown barcode says not found', 'Barcode not found' in s['msg'], s)
        p.evaluate("()=>closeModal('mStockIn')")
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== CLEANUP =====================
        A = 'Cleanup'
        p, errs, ctx, net = page(br, url)
        p.evaluate("()=>go('pos')")
        def opened():
            p.evaluate("()=>{window.__cam.next=null}"); p.click(BTN['pos']); p.wait_for_function("()=>window.__cam.detect>0&&BarcodeCamera.isOpen()", timeout=5000)
            p.evaluate("()=>{window.__cam.detect=0}")
        opened(); p.click('#bcCamOverlay .modal-ftr button[data-i18n="btn_cancel"]'); p.wait_for_timeout(300)
        r = p.evaluate(STATE); p.wait_for_timeout(500); d = p.evaluate("()=>window.__cam.detect")
        chk(A, 'Cancel: scanner closed, every track stopped, detection loop stopped', not r['on'] and r['live'] == 0 and not r['src'] and d == r['detect'], {'r': r, 'd': d})
        opened(); p.click('#bcCamOverlay .modal-close'); p.wait_for_timeout(300)
        r = p.evaluate(STATE)
        chk(A, '✕ close: scanner closed, every track stopped', not r['on'] and r['live'] == 0, r)
        p.evaluate("()=>{go('products');resetProdForm();openModal('mAddProd')}")
        p.evaluate("()=>{window.__cam.next=null}"); p.click(BTN['form']); p.wait_for_function("()=>BarcodeCamera.isOpen()&&window.__cam.detect>0", timeout=5000)
        p.keyboard.press('Escape'); p.wait_for_timeout(300)
        r = p.evaluate(STATE); f = p.evaluate("()=>document.getElementById('mAddProd').classList.contains('on')")
        chk(A, 'Escape: closes the scanner and stops the camera, the product form underneath stays open', not r['on'] and r['live'] == 0 and f, {'r': r, 'form': f})
        p.evaluate("()=>closeModal('mAddProd')")
        p.evaluate("()=>go('pos')")
        opened()
        p.evaluate("()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'hidden'});document.dispatchEvent(new Event('visibilitychange'));delete document.visibilityState}")
        p.wait_for_timeout(300); r = p.evaluate(STATE)
        chk(A, 'App sent to the background (visibility hidden): camera stopped and scanner closed', not r['on'] and r['live'] == 0, r)
        opened()
        p.evaluate("()=>window.dispatchEvent(new Event('pagehide'))"); p.wait_for_timeout(300); r = p.evaluate(STATE)
        chk(A, 'Page closing / navigating away (pagehide): camera stopped', not r['on'] and r['live'] == 0, r)
        opened()
        cov = p.evaluate("""()=>{toast('Barcode not found. Add this product to your inventory first.','warning',5000);
          const rk=document.getElementById('toastRack');rk.dataset.css=rk.style.cssText;rk.style.cssText+=';top:0;bottom:0;right:0;left:0;justify-content:center;align-items:center';
          const e=document.elementFromPoint(innerWidth/2,innerHeight/2);return !!(e&&e.closest('#toastRack'))}""")
        p.wait_for_timeout(600)
        r = p.evaluate(STATE)
        p.evaluate("()=>{const rk=document.getElementById('toastRack');rk.style.cssText=rk.dataset.css}")
        chk(A, 'A toast over the middle of the screen does not close the scanner', cov and r['open'] and r['live'] >= 1, {'toastAtCentre': cov, 'r': r})
        p.evaluate("()=>{document.getElementById('lockScreen').style.display='flex'}"); p.wait_for_timeout(500); r = p.evaluate(STATE)
        p.evaluate("()=>{document.getElementById('lockScreen').style.display='none'}")
        chk(A, 'Another screen covers the scanner (auto-lock screen): camera stopped and scanner closed', not r['on'] and not r['open'] and r['live'] == 0, r)
        t0 = p.evaluate("()=>window.__cam.tracks.length")
        p.evaluate("()=>{window.__cam.delay=400;window.__cam.next=null}"); p.click(BTN['pos']); p.wait_for_timeout(80)
        p.evaluate("()=>BarcodeCamera.close()"); p.wait_for_timeout(700)
        r = p.evaluate(STATE)
        chk(A, 'Closed while the permission prompt is still up: the late camera is stopped at once', r['tracks'] > t0 and r['live'] == 0 and not r['on'] and not r['open'], r)
        p.evaluate("()=>{window.__cam.delay=0}")
        r = p.evaluate("()=>{let n=0;const o=BarcodeCamera.close.bind(BarcodeCamera);BarcodeCamera.close=()=>{n++;o()};document.dispatchEvent(new Event('visibilitychange'));window.dispatchEvent(new Event('pagehide'));BarcodeCamera.close=o;return n}")
        chk(A, 'After closing, its visibility/pagehide listeners are removed (no background listener)', r == 0, r)
        opened(); p.wait_for_timeout(2000); d = p.evaluate("()=>window.__cam.detect"); p.evaluate("()=>BarcodeCamera.close()")
        chk(A, 'While open, detection is throttled (at most about 6 per second, one at a time)', 4 <= d <= 14, d)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== CAMERA CHOICE (several rear lenses, e.g. Samsung A21s) =====================
        A = 'Cameras'
        DEVS = "[{deviceId:'f1',label:'camera2 1, facing front'},{deviceId:'b2',label:'camera2 2, facing back'},{deviceId:'b0',label:'camera2 0, facing back'},{deviceId:'b3',label:'camera2 3, facing back'}]"
        LIVE = "window.__cam.tracks.filter(t=>t.readyState==='live').length"
        p, errs, ctx, net = page(br, url)
        p.evaluate("()=>go('pos')")
        p.evaluate("(d)=>{const k=window.__cam;k.devices=eval(d);k.defaultId='b2';k.caps={focusMode:['manual','continuous']};k.next=null}", DEVS)
        p.click(BTN['pos']); p.wait_for_function("()=>BarcodeCamera.isOpen()&&window.__cam.detect>0", timeout=5000)
        r = p.evaluate("()=>({opened:window.__cam.opened.slice(),cur:BarcodeCamera._currentId(BarcodeCamera._s),live:" + LIVE + ",info:document.getElementById('bcCamInfo').textContent,sw:getComputedStyle(document.getElementById('bcCamSwitch')).display,applied:window.__cam.applied.slice()})")
        chk(A, 'Browser hands over another rear lens (camera2 2): Bizora reopens the main one (camera2 0); only one camera left running',
            r['opened'] == ['b2', 'b0'] and r['cur'] == 'b0' and r['live'] == 1, r)
        chk(A, 'Continuous autofocus requested on the camera in use', any(a['id'] == 'b0' and a['x'] == {'advanced': [{'focusMode': 'continuous'}]} for a in r['applied']), r['applied'])
        chk(A, 'Camera name shown, and Switch camera offered (3 rear lenses; the front camera is not used)', 'camera2 0, facing back' in r['info'] and '(1/3)' in r['info'] and r['sw'] != 'none', r)
        chk(A, 'No camera choice is saved until the user switches', p.evaluate("()=>localStorage.getItem('bizora_bc_camera')") is None)
        p.click('#bcCamSwitch'); p.wait_for_timeout(500)
        r = p.evaluate("()=>({cur:BarcodeCamera._currentId(BarcodeCamera._s),live:" + LIVE + ",info:document.getElementById('bcCamInfo').textContent,pref:localStorage.getItem('bizora_bc_camera'),status:document.getElementById('bcCamStatus').textContent,open:BarcodeCamera.isOpen()})")
        chk(A, 'Switch camera: next rear lens (camera2 2), old camera stopped, choice remembered on this phone',
            r['cur'] == 'b2' and r['live'] == 1 and '(2/3)' in r['info'] and r['pref'] == 'b2' and r['open'] and 'Point the camera' in r['status'], r)
        p.click('#bcCamSwitch'); p.wait_for_timeout(400); p.click('#bcCamSwitch'); p.wait_for_timeout(400)
        r = p.evaluate("()=>({cur:BarcodeCamera._currentId(BarcodeCamera._s),live:" + LIVE + "})")
        chk(A, 'Switch camera goes round all rear lenses (2 -> 3 -> 0)', r['cur'] == 'b0' and r['live'] == 1, r)
        p.click('#bcCamSwitch'); p.wait_for_timeout(400)
        p.evaluate("()=>{BarcodeCamera.close();window.__cam.opened=[]}")
        r = scan(p, 'pos', '5449000000996')
        r2 = p.evaluate("()=>window.__cam.opened.slice()")
        chk(A, 'Next scan opens the remembered lens directly, and the scan works', r2 == ['b2'] and r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}] and r['live'] == 0, {'opened': r2, 'r': r})
        p.evaluate("()=>{localStorage.setItem('bizora_bc_camera','gone');window.__cam.opened=[];window.__cam.next=null}")
        p.click(BTN['pos']); p.wait_for_function("()=>BarcodeCamera.isOpen()&&window.__cam.detect>0", timeout=5000)
        r = p.evaluate("()=>({opened:window.__cam.opened.slice(),pref:localStorage.getItem('bizora_bc_camera'),err:document.getElementById('bcCamOverlay').classList.contains('err')})")
        chk(A, 'Remembered lens no longer exists: forgotten, main lens used, no error', r['opened'] == ['b2', 'b0'] and r['pref'] is None and not r['err'], r)
        p.evaluate("()=>BarcodeCamera.close()")
        p.evaluate("()=>{const k=window.__cam;k.failIds=['b0'];k.opened=[];k.next=null}")
        p.click(BTN['pos']); p.wait_for_function("()=>BarcodeCamera.isOpen()&&window.__cam.detect>0", timeout=5000)
        r = p.evaluate("()=>({opened:window.__cam.opened.slice(),cur:BarcodeCamera._currentId(BarcodeCamera._s),live:" + LIVE + "})")
        chk(A, "Main lens refuses to start: falls back to the browser's choice, scanner still works", r['opened'] == ['b2', 'b2'] and r['cur'] == 'b2' and r['live'] == 1, r)
        p.evaluate("()=>{BarcodeCamera.close();localStorage.removeItem('bizora_bc_camera');window.__cam.failIds=['b3'];window.__cam.next=null}")
        p.click(BTN['pos']); p.wait_for_function("()=>BarcodeCamera.isOpen()&&window.__cam.detect>0", timeout=5000)
        p.click('#bcCamSwitch'); p.wait_for_timeout(400); p.click('#bcCamSwitch'); p.wait_for_timeout(400)
        r = p.evaluate("()=>({err:document.getElementById('bcCamOverlay').classList.contains('err'),status:document.getElementById('bcCamStatus').textContent,live:" + LIVE + ",open:BarcodeCamera.isOpen(),sw:getComputedStyle(document.getElementById('bcCamSwitch')).display})")
        chk(A, 'A lens that will not start: clear message, nothing left running, Switch camera still offered', r['err'] and 'could not be started' in r['status'] and r['live'] == 0 and r['open'] and r['sw'] != 'none', r)
        p.click('#bcCamSwitch'); p.wait_for_timeout(400)
        r = p.evaluate("()=>({err:document.getElementById('bcCamOverlay').classList.contains('err'),cur:BarcodeCamera._currentId(BarcodeCamera._s),live:" + LIVE + "})")
        chk(A, '...and switching again recovers on the next lens', not r['err'] and r['cur'] == 'b0' and r['live'] == 1, r)
        p.evaluate("()=>BarcodeCamera.close()")
        r = p.evaluate("()=>({live:" + LIVE + ",info:document.getElementById('bcCamInfo').textContent,sw:getComputedStyle(document.getElementById('bcCamSwitch')).display})")
        chk(A, 'Close after switching: every camera stopped, name and Switch button cleared', r == {'live': 0, 'info': '', 'sw': 'none'}, r)
        p.evaluate("()=>{const k=window.__cam;k.devices=null;k.defaultId='';k.failIds=[];k.mode='nopic';k.next=null}")
        p.click(BTN['pos']); p.wait_for_timeout(600)
        p.evaluate("()=>{BarcodeCamera._s.picSince-=5000}"); p.wait_for_timeout(500)
        r = p.evaluate("()=>({status:document.getElementById('bcCamStatus').textContent,sw:getComputedStyle(document.getElementById('bcCamSwitch')).display,open:BarcodeCamera.isOpen()})")
        chk(A, 'Camera gives no picture: "No picture from this camera" message, scanner stays open', 'No picture from this camera' in r['status'] and r['open'], r)
        chk(A, 'Single camera (no lens list): Switch camera hidden', r['sw'] == 'none', r)
        p.evaluate("()=>{BarcodeCamera.close();window.__cam.mode='ok'}")
        r = p.evaluate("()=>{BarcodeCamera.open(()=>{});return new Promise(res=>setTimeout(()=>{const v=document.getElementById('bcCamVideo'),f=getComputedStyle(document.querySelector('.bc-cam-view'),'::after');res({fit:getComputedStyle(v).objectFit,frame:f.content!=='none'&&f.borderTopStyle==='solid'});BarcodeCamera.close()},500))}")
        chk(A, 'Whole camera picture visible (not cropped) with a white aiming frame', r == {'fit': 'contain', 'frame': True}, r)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== OFFLINE =====================
        A = 'Offline'
        p, errs, ctx, net = page(br, url)
        p.evaluate("()=>go('pos')")
        ctx.set_offline(True)
        r = scan(p, 'pos', '5449000000996')
        chk(A, 'Phone offline: camera scan still adds the product (no internet needed)', r['cart'] == [{'id': 'pa', 'qty': 1, 'price': 350}] and r['live'] == 0, r)
        ctx.set_offline(False)
        chk(A, 'No JS errors', not errs, errs)
        ctx.close()

        # ===================== EN / FR, 360 px =====================
        for lang in ('en', 'fr'):
            A = 'EN/FR'
            p, errs, ctx, net = page(br, url, lang=lang)
            keys = p.evaluate("""()=>{const en=I18N_DICT.en,fr=I18N_DICT.fr;const k=Object.keys(en).filter(x=>x.startsWith('bc_cam_'));
              return {n:k.length,missing:k.filter(x=>!fr[x]),same:k.filter(x=>fr[x]===en[x])}}""")
            if lang == 'en':
                chk(A, 'All 14 camera strings exist in EN and FR, and FR is translated', keys['n'] == 14 and not keys['missing'] and not keys['same'], keys)
            p.evaluate("()=>go('pos')")
            lbl = p.evaluate("()=>{const b=document.querySelector('button[onclick=\"bcCamToPos()\"]');return {t:b.innerText.trim(),title:b.title}}")
            p.evaluate("()=>{window.__cam.mode='deny'}"); p.click(BTN['pos']); p.wait_for_timeout(400)
            st = p.evaluate("()=>({title:document.getElementById('bcCamTitle').textContent,status:document.getElementById('bcCamStatus').textContent,box:document.querySelector('#bcCamOverlay .modal').getBoundingClientRect().width,sw:document.documentElement.scrollWidth})")
            p.evaluate("()=>{BarcodeCamera.close();window.__cam.mode='ok'}")
            ov = p.evaluate("""()=>{const out=[];const w=()=>document.documentElement.scrollWidth;
              go('pos');out.push(['pos',w(),document.querySelector('button[onclick="bcCamToPos()"]').getBoundingClientRect().right]);
              go('products');out.push(['products',w(),document.querySelector('button[onclick="bcCamToProductSearch()"]').getBoundingClientRect().right]);
              resetProdForm();openModal('mAddProd');out.push(['form',w(),document.querySelector('button[onclick="bcCamToProductForm()"]').getBoundingClientRect().right]);closeModal('mAddProd');
              openStockIn();out.push(['stock',w(),document.querySelector('button[onclick="bcCamToStockIn()"]').getBoundingClientRect().right]);closeModal('mStockIn');return out}""")
            if lang == 'en':
                ok = lbl['t'].endswith('Scan') and 'camera' in lbl['title'] and st['title'] == 'Scan barcode' and 'refused' in st['status']
            else:
                ok = lbl['t'].endswith('Scanner') and 'appareil photo' in lbl['title'] and st['title'] == 'Scanner un code-barres' and 'refusé' in st['status']
            chk(A, f'{lang.upper()}: button, title and messages in {lang.upper()}', ok, {'lbl': lbl, 'st': st})
            chk(A, f'{lang.upper()}: 360 px: scanner fits, camera buttons inside the screen, no sideways scroll', st['box'] <= 360 and st['sw'] <= 360 and all(o[1] <= 360 and o[2] <= 360 for o in ov), {'st': st, 'ov': ov})
            chk(A, f'{lang.upper()}: no JS errors', not errs, errs)
            ctx.close()

        br.close()
    srv.shutdown()
    fails = [r for r in RES if not r[2]]
    print(f'\nTOTAL {len(RES)} PASS {len(RES) - len(fails)} FAIL {len(fails)}')
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
