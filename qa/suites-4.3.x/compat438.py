import threading,http.server,functools,json
from playwright.sync_api import sync_playwright
SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
res=[]
def chk(n,c,i=''): res.append((n,bool(c)));print(('PASS' if c else 'FAIL'),'|',n,'' if c else '| '+json.dumps(i,ensure_ascii=False,default=str)[:500])
def serve(d,port):
  h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=d);h.log_message=lambda *a:None
  s=http.server.ThreadingHTTPServer(('127.0.0.1',port),h);threading.Thread(target=s.serve_forever,daemon=True).start();return s
SEED="""async()=>{window.toast=()=>{};const T=todayStr(),P='2026-05-02';
 S.add('products',{id:'o1',sku:'SKU-000001',name:'Rice',category:'G',cost:15000,price:18000,stock:30,unit:'pcs',tax:0,status:'active',added:P});
 S.add('customers',{id:'oc1',name:'Old Customer',phone:'+237 670 111 222',limit:0,status:'active',added:P});
 S.add('customers',{id:'oc2',name:'Second One',phone:'',status:'active',added:P});
 S.add('sales',{id:'os1',cid:'oc1',amount:50000,date:P,due:P,items:[{productId:'o1',name:'Rice',qty:2,price:18000,subtotal:36000},{name:'Other',qty:1,price:14000,subtotal:14000}],status:'partial',docNum:'INV-OS1'});
 S.add('payments',{id:'op1',invId:'os1',cid:'oc1',amount:10000,date:P,method:'cash',ref:'',notes:'Deposit at time of sale'});
 S.add('payments',{id:'op2',invId:'os1',cid:'oc1',amount:5000,date:P,method:'mobile-money',ref:'MM1',collector:'Ali',notes:''});
 S.add('payments',{id:'op3',invId:'os1',cid:'oc1',amount:2000,date:P,ref:'',notes:'very old, no method'});
 S.add('posSales',{id:'ops1',receiptNum:'REC-000001',date:P,cid:null,items:[{productId:'o1',name:'Rice',qty:1,price:18000,subtotal:18000}],subtotal:18000,total:18000,paid:20000,change:2000,method:'cash',type:'cash'});
 S.add('expenses',{id:'oe1',category:'rent',amount:40000,date:P,notes:'May rent'});
 S.add('creditLedger',{id:'ocl1',cid:'oc2',type:'earned',amount:3000,date:P,note:'Overpayment on INV-X',relatedInvId:null});
 S.setObj('cashDrawer',{[P]:{opening:10000,closing:25000}});
 await new Promise(r=>setTimeout(r,300));let blob=null;const o=URL.createObjectURL;URL.createObjectURL=b=>{blob=b;return o.call(URL,b)};exportBackup();URL.createObjectURL=o;await new Promise(r=>setTimeout(r,400));return {v:APP_VERSION,txt:await blob.text()}}"""
DIG="""()=>{const strip=a=>JSON.stringify(a.map(r=>{const{updated_at,created_at,sync_status,version,deleted,...x}=r;return x}).sort((a,b)=>String(a.id).localeCompare(String(b.id))));const o={};
 for(const k of ['customers','sales','payments','products','posSales','creditLedger','expenses'])o[k]=strip(S.get(k)||[]);o.cd=JSON.stringify(S.obj('cashDrawer',{}));
 o.debt=custDebt('oc1');o.credit=Math.round(custCreditBalance('oc2'));o.pm=S.get('payments').map(p=>p.id+':'+(p.method===undefined?'(none)':p.method)).sort();return o}"""
RESTORE="""async(txt)=>{const T=[];window.toast=(m,ty)=>T.push((ty||'')+':'+m);handleFile(new File([txt],'b.json',{type:'application/json'}));await new Promise(r=>setTimeout(r,900));
 const c=document.getElementById('mConfirm').classList.contains('on');if(c)document.getElementById('mConfirmBtn').click();await new Promise(r=>setTimeout(r,1200));return {c,T}}"""
with sync_playwright() as pw:
  b=pw.chromium.launch()
  for label,d,port in [('4.2.7 (production)','/home/claude/bz_orig',8861),('4.3.7 candidate',SP+'v437',8862)]:
    s1=serve(d,port);ctx=b.new_context(service_workers='block');p=ctx.new_page();p.goto(f'http://127.0.0.1:{port}/index.html');p.wait_for_timeout(2500)
    p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
    r=p.evaluate(SEED);src=p.evaluate(DIG);ctx.close();s1.shutdown()
    s2=serve('/home/claude/main',port+10);ctx=b.new_context(service_workers='block');p=ctx.new_page();errs=[];p.on('pageerror',lambda e:errs.append(str(e)[:200]))
    p.goto(f'http://127.0.0.1:{port+10}/index.html');p.wait_for_timeout(2500);p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
    rr=p.evaluate(RESTORE,r['txt']);dst=p.evaluate(DIG);v=p.evaluate("APP_VERSION")
    chk(f'Backup from {label} (v{r["v"]}) restores into {v}: confirm + success, no JS error',rr['c'] and any(t.startswith('success:') for t in rr['T']) and errs==[],{'T':rr['T'],'errs':errs})
    diff=[k for k in src if src[k]!=dst[k]]
    chk(f'Backup from {label}: every store, debt, credit, drawer and payment method identical after restore (incl. method-less payment kept method-less)',diff==[] and '(none)' in ' '.join(dst['pm']),{'diff':diff,'pm':dst['pm']})
    ctx.close();s2.shutdown()
  b.close()
print('TOTAL',len(res),'PASS',sum(c for _,c in res),'FAIL',sum(1 for _,c in res if not c))
