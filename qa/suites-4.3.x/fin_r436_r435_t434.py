import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright
DIR=sys.argv[1] if len(sys.argv)>1 else '/home/claude/main'
SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=DIR); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8843),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
results=[]
def chk(n,c,info=''):
    results.append((n,bool(c))); print(('PASS' if c else 'FAIL'),'|',n,'|',json.dumps(info,ensure_ascii=False)[:500] if not c else '')
SEED="""async(role)=>{
  window.__t=[];window.toast=(m,ty)=>{window.__t.push(String(m));};
  S.add('products',{id:'p1',sku:'SKU-000001',name:'Rice Bag',category:'Grains',cost:13500,price:16000,stock:10,unit:'pcs',status:'active',added:todayStr()});
  S.add('products',{id:'p2',sku:'SKU-000002',name:'Oil',category:'G',cost:4000,price:5000,stock:4,unit:'pcs',status:'active',added:todayStr()});
  S.add('products',{id:'p3',sku:'SKU-000003',name:'Old Soap',category:'G',cost:100,price:200,stock:0,unit:'pcs',status:'discontinued',added:todayStr()});
  S.add('products',{id:'p4',sku:'SKU-000004',name:'Café',category:'G',cost:100,price:200,stock:3,unit:'pcs',status:'active',added:todayStr()});
  if(role!=='off'){const salt=genSalt();setAccessControl({...getAccessControl(),enabled:true,ownerPasswordSalt:salt,ownerPasswordHash:await hashPassword('ownerpass9',salt)});}
  if(!['off','owner'].includes(role)){const c=await createEmployee({fullName:'Emp '+role,username:'u'+role,password:'1234',role});await Auth.loginEmployee(c.employee.id,'1234');}
  onEmployeeSessionStarted();
  window.__close=()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  window.__n=()=>S.get('products').length;
  window.__add=(name,cat)=>{go('products');openModal('mAddProd');resetProdForm();document.getElementById('pName').value=name;document.getElementById('pCost').value='100';document.getElementById('pPrice').value='200';document.getElementById('pStock').value='1';if(cat)document.getElementById('pCategory').value=cat;window.__t=[];const n0=__n();saveProduct();const r={added:__n()-n0,toast:window.__t.slice(-1)[0]||'',btnFree:!document.getElementById('saveProductBtn').disabled,modalOpen:document.getElementById('mAddProd').classList.contains('on')};__close();return r};
  window.__editName=(id,name,extra)=>{go('products');editProduct(id);document.getElementById('pName').value=name;if(extra)eval(extra);document.getElementById('saveProductBtn').disabled=false;window.__t=[];saveProduct();const r={name:S.get('products').find(p=>p.id===id).name,toast:window.__t.slice(-1)[0]||''};__close();return r};
  return true}"""
def page(b,vw=1200):
    p=b.new_context(service_workers='block',viewport={'width':vw,'height':900}).new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://127.0.0.1:8843/index.html'); p.wait_for_timeout(2200)
    p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}"); return p,errs
with sync_playwright() as pw:
  b=pw.chromium.launch()
  for role in ['owner','storekeeper','supervisor','off']:
    p,errs=page(b); p.evaluate(SEED,role)
    R=lambda js: p.evaluate(js)
    r=R("()=>__add('Rice Bag')")
    chk(f'{role}: exact duplicate on add refused with SKU+stock message',r['added']==0 and "already exists (SKU-000001, stock 10)" in r['toast'] and 'Stock In' in r['toast'] and r['btnFree'],r)
    for label,nm in [('case-only','rice bag'),('upper-case','RICE BAG'),('leading/trailing spaces','   Rice Bag  '),('repeated internal spaces','Rice    Bag'),('tab/nbsp whitespace','Rice\\tBag'),('different category',None)]:
        r=R(f"()=>__add('{nm}')") if nm else R("()=>__add('Rice Bag','Beverages')")
        chk(f'{role}: {label} duplicate refused',r['added']==0 and 'SKU-000001' in r['toast'],r)
    r=R("()=>__add('Rice Bag 25kg')")
    chk(f'{role}: distinct name still saves',r['added']==1 and 'added' in r['toast'].lower(),r)
    r=R("()=>__add('Cafe')")
    chk(f'{role}: accents NOT normalized (Cafe allowed alongside Café)',r['added']==1,r)
    r=R("()=>__add('old soap')")
    chk(f'{role}: matching DISCONTINUED product -> refused with reactivate guidance',r['added']==0 and 'discontinued' in r['toast'] and 'Reactivate' in r['toast'] and 'SKU-000003' in r['toast'],r)
    r=R("()=>__editName('p2','Rice Bag')")
    chk(f'{role}: edit to another existing name refused (name unchanged)',r['name']=='Oil' and 'SKU-000001' in r['toast'],r)
    r=R("()=>__editName('p2',' oil ')")
    chk(f'{role}: edit keeping its own name (case/space variant) allowed',r['toast'].lower().startswith('product updated') or 'updated' in r['toast'].lower(),r)
    r=R("()=>__editName('p1','Rice Bag',\"document.getElementById('pPrice').value='17000'\")")
    chk(f'{role}: edit own product (same name, new price) allowed',S if False else ('updated' in r['toast'].lower() and R("()=>S.get('products').find(p=>p.id==='p1').price")==17000),r)
    r=R("""()=>{window.__t=[];document.getElementById('editProdId').value='';document.getElementById('pName').value='Rice Bag';document.getElementById('pCost').value='1';document.getElementById('pPrice').value='1';document.getElementById('pStock').value='1';document.getElementById('saveProductBtn').disabled=false;const n0=__n();saveProduct();__close();return {added:__n()-n0,toast:window.__t.slice(-1)[0]||''}}""")
    chk(f'{role}: direct saveProduct() call refused',r['added']==0 and 'already exists' in r['toast'],r)
    chk(f'{role}: no JS errors',errs==[],errs); p.context.close()
  # ===== CSV (owner and storekeeper) =====
  for role in ['owner','storekeeper']:
    p,errs=page(b); p.evaluate(SEED,role)
    before=p.evaluate("()=>JSON.stringify(S.get('products'))")
    p.evaluate("()=>{go('backup');document.getElementById('csvImportType').value='products'}")
    p.set_input_files('#csvFileInput',SP+'dup434.csv'); p.wait_for_timeout(800)
    rows=p.evaluate("()=>[...document.querySelectorAll('#csvPreviewBody tr')].map(r=>r.innerText.replace(/\\s+/g,' ').trim())")
    summ=p.evaluate("()=>document.getElementById('csvPreviewSummary').innerText")
    exp={1:'already exists (SKU-000001)',2:'already exists (SKU-000001)',3:'✓ Valid',4:'repeated in this file (row 3)',5:'✓ Valid',6:'repeated in this file (row 3)',7:'Invalid',8:'already exists (SKU-000004)'}
    okrows=all(exp[i+1] in rows[i] for i in range(8))
    chk(f'{role} CSV preview: existing-name and in-file duplicates flagged, invalid/skipped',okrows and '2 valid' in summ,{'rows':rows,'summary':summ})
    # direct commit bypass: mark every row valid, including dupes
    p.evaluate("()=>{csvParsedRows.forEach(r=>{if(r.data&&r.data.name)r.valid=true});window.__t=[];commitCsvImport();}")
    after=p.evaluate("()=>S.get('products').map(p=>p.name)")
    toasts=p.evaluate("()=>window.__t")
    names=[n.strip().lower() for n in after]
    chk(f'{role} CSV direct commitCsvImport() with forced-valid rows: only Sugar + Salt added, no duplicates',sorted(after[4:])==['Salt','Sugar'] and len(names)==len(set(' '.join(n.split()) for n in names)),{'after':after,'toasts':toasts})
    chk(f'{role} CSV: skipped-duplicates warning and correct imported count',any('5 duplicate' in x for x in toasts) and any(x.startswith('2 ') or ' 2 ' in x for x in toasts),toasts)
    orig=p.evaluate("(b)=>{const B=JSON.parse(b);const now=S.get('products');return B.every(o=>{const n=now.find(x=>x.id===o.id);return n&&n.name===o.name&&n.stock===o.stock&&n.price===o.price&&n.status===o.status})}",before)
    chk(f'{role} CSV: existing products untouched (not merged/modified)',orig)
    # all-duplicates commit
    p.evaluate("()=>{csvParsedRows=[{valid:true,data:{name:'rice  bag',cost:1,price:1,stock:1,category:'Imported',unit:'pcs',lowStock:5,tax:0}}];csvImportTypeActive='products';window.__t=[];commitCsvImport()}")
    r=p.evaluate("()=>({n:S.get('products').length,t:window.__t.slice(-1)[0]})")
    chk(f'{role} CSV: all-duplicate commit imports nothing, explains why',r['n']==len(after) and 'Nothing imported' in r['t'],r)
    chk(f'{role} CSV: no JS errors',errs==[],errs); p.context.close()
  # ===== Developer Test Suite validator (existing duplicates, report-only) =====
  p,errs=page(b); p.evaluate(SEED,'off')
  r=p.evaluate("""async()=>{
    // legacy duplicates injected directly (as older versions allowed)
    S.set('products',[...S.get('products'),{id:'d1',sku:'SKU-000009',name:'rice bag ',price:1,stock:2,status:'active'},{id:'d2',sku:'SKU-000010',name:'OIL',price:1,stock:1,status:'active'}]);
    const before=JSON.stringify(S.get('products'));
    await DevSuite.runValidator();
    const html=document.getElementById('devValidatorResults')?document.getElementById('devValidatorResults').innerText:document.body.innerText;
    const after=JSON.stringify(S.get('products'));
    return {unchanged:before===after,count:S.get('products').length,found:/2 duplicate product name\\(s\\) found/.test(html),detail:(html.match(/duplicate product name[^\\n]*/)||[''])[0]}}""")
  chk('Developer validator: reports existing normalized duplicate names (WARNING) with SKUs',r['found'] and 'SKU-000001' in r['detail'] and 'SKU-000009' in r['detail'] and 'SKU-000010' in r['detail'],r)
  chk('Developer validator: report-only (no product modified, merged or removed)',r['unchanged'] and r['count']==6,r)
  chk('Validator: no JS errors',errs==[],errs); p.context.close()
  # ===== FR + 360 =====
  p,errs=page(b,360); p.evaluate(SEED,'owner'); p.evaluate("()=>setLang('fr')")
  r=p.evaluate("()=>[__add('rice bag').toast,__add('old soap').toast]")
  chk('FR: duplicate + discontinued messages translated','existe déjà (SKU-000001, stock 10)' in r[0] and 'entrée de stock' in r[0] and 'arrêté' in r[1] and 'Réactivez' in r[1],r)
  p.evaluate("()=>{go('backup');document.getElementById('csvImportType').value='products'}"); p.set_input_files('#csvFileInput',SP+'dup434.csv'); p.wait_for_timeout(800)
  rows=p.evaluate("()=>[...document.querySelectorAll('#csvPreviewBody tr')].map(r=>r.innerText.replace(/\\s+/g,' ').trim())")
  chk('FR: CSV duplicate labels translated','Doublon — existe déjà (SKU-000001)' in rows[0] and 'répété dans ce fichier (ligne 3)' in rows[3],rows)
  fits=p.evaluate("()=>{const m=document.querySelector('#mCsvPreview .modal').getBoundingClientRect();return m.left>=0&&m.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth}")
  p.wait_for_timeout(400); p.screenshot(path=SP+'csv_dup_fr.png')
  chk('360px: CSV preview with duplicate labels has no page overflow',fits)
  p.evaluate("()=>{closeModal('mCsvPreview');setLang('en');go('products');openModal('mAddProd');resetProdForm();document.getElementById('pName').value='Rice Bag';document.getElementById('pCost').value='1';document.getElementById('pPrice').value='1';document.getElementById('pStock').value='1';}")
  p.evaluate("()=>{window.toast=window.__origToast||window.toast}")
  chk('EN/FR/360: no JS errors',errs==[],errs); p.context.close()
  # ===== not run at checkout / load / render =====
  p,errs=page(b); 
  r=p.evaluate("""async()=>{S.add('products',{id:'p1',sku:'S1',name:'Rice',cost:1,price:2,stock:50,status:'active',added:todayStr()});
    let calls=0;const wrap=n=>{const f=window[n];return f};
    // count helper calls via a Proxy on S.get('products') reads would be invasive; instead instrument by name lookup counters
    return true}""")
  b.close()
srv.shutdown()
f=[x for x in results if not x[1]]
print('\nTOTAL',len(results),'FAIL',len(f)); [print('  FAILED:',x[0]) for x in f]
