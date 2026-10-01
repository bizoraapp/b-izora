import threading,http.server,json,os
from playwright.sync_api import sync_playwright
ROOT={'d':'/home/claude/bz_orig'}
class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self,path):
        p=super().translate_path(path); return os.path.join(ROOT['d'],os.path.relpath(p,os.getcwd()))
    def log_message(self,*a):pass
    def end_headers(self):
        self.send_header('Cache-Control','no-cache'); super().end_headers()
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8871),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:8871/index.html'
DIGEST="""()=>{const st=['sales','payments','customers','products','expenses','posSales','stockMovements','auditLog','employees'];const o={};
  const h=s=>{let x=0;for(let i=0;i<s.length;i++)x=(x*31+s.charCodeAt(i))|0;return x};
  for(const k of st){const v=S.get(k)||[];o[k]={n:v.length,h:h(JSON.stringify(v))}}
  o.debts=Object.fromEntries(S.get('customers').map(c=>[c.name,custDebt(c.id)]));
  o.salesTotal=S.get('sales').reduce((a,s)=>a+(+s.amount||0),0);o.payTotal=S.get('payments').reduce((a,s)=>a+(+s.amount||0),0);
  o.expTotal=S.get('expenses').reduce((a,s)=>a+(+s.amount||0),0);o.stock=Object.fromEntries(S.get('products').map(p=>[p.name+'#'+p.id,p.stock]));
  o.settings=h(JSON.stringify(S.obj('settings')));o.ac=(({enabled,ownerPasswordHash,recoveryCodeHash})=>({enabled,hasPw:!!ownerPasswordHash,hasCode:!!recoveryCodeHash}))(getAccessControl());
  return o}"""
R={}
with sync_playwright() as pw:
  b=pw.chromium.launch(); ctx=b.new_context(); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
  p.goto(URL); p.wait_for_timeout(3000)
  p.evaluate("async()=>{await navigator.serviceWorker.ready}"); p.reload(); p.wait_for_timeout(2500)
  R['prod_version']=p.evaluate("APP_VERSION"); R['prod_caches']=sorted(p.evaluate("caches.keys()"))
  # seed realistic 4.2.7 data through the store
  p.evaluate("""async()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
    const T=todayStr();
    S.set('settings',{...S.obj('settings'),businessName:'Boutique Test',currency:'FCFA',setupDone:true});
    [['p1','Rice 25kg',18000,15000,40],['p2','rice 25KG ',18000,15000,5],['p3','Phone',30000,25000,12],['p4','Soap',500,300,200]].forEach(([id,name,price,cost,stock],i)=>S.add('products',{id,sku:'SKU-00000'+(i+1),name,category:'Gen',cost,price,stock,unit:'pcs',tax:0,status:'active',added:T}));
    [['c1','Amina',5000,'active'],['c2','Bello',0,'active'],['c3','Chidi',100000,'blocked'],['c4','Dora',undefined,'active']].forEach(([id,name,limit,status],i)=>{const c={id,name,phone:'+23767000000'+i,status,added:T};if(limit!==undefined)c.limit=limit;S.add('customers',c)});
    S.add('sales',{id:'s1',cid:'c1',amount:3000,date:T,due:T,items:[{productId:'p4',name:'Soap',qty:6,price:500,subtotal:3000}],status:'pending',docNum:'INV-S1'});
    S.add('sales',{id:'s2',cid:'c2',amount:60000,date:'2026-08-01',due:'2026-08-15',items:[{productId:'p3',name:'Phone',qty:2,price:30000,subtotal:60000}],status:'pending',docNum:'INV-S2'});
    S.add('sales',{id:'s3',cid:'c4',amount:18000,date:'2026-09-01',due:'2026-12-01',items:[{productId:'p1',name:'Rice 25kg',qty:1,price:18000,subtotal:18000}],status:'pending',docNum:'INV-S3'});
    S.set('payments',[{id:'y1',invId:'s2',cid:'c2',amount:25000,date:'2026-08-20',method:'cash'},{id:'y2',invId:'s3',cid:'c4',amount:18000,date:'2026-09-02',method:'mobile'}]);
    S.add('expenses',{id:'e1',category:'rent',amount:50000,date:T,notes:'Sept rent'});S.add('expenses',{id:'e2',category:'transport',amount:3500,date:T,notes:''});
    S.add('posSales',{id:'ps1',receiptNum:'RCP-1',date:T,cid:null,items:[{productId:'p4',name:'Soap',qty:2,price:500,subtotal:1000}],subtotal:1000,total:1000,paid:1000,change:0,method:'cash',type:'cash'});
    const salt=genSalt();setAccessControl({enabled:true,pendingSetup:false,ownerPasswordHash:await hashPassword('owner99',salt),ownerPasswordSalt:salt,recoveryCodeHash:'',recoveryCodeSalt:''});
    await createEmployee({fullName:'Cash Ier',username:'cashier1',password:'1234',role:'cashier'});
    logAuditEvent('add','Legacy 4.2.7 audit line',{});}""")
  p.wait_for_timeout(2000); p.reload(); p.wait_for_timeout(3000)
  R['prod_after_reload_version']=p.evaluate("APP_VERSION")
  before=p.evaluate(DIGEST); R['before']=before
  # ---- deploy merged build to the same origin ----
  ROOT['d']='/home/claude/main'
  p.reload(); p.wait_for_timeout(4000)
  R['still_old_until_user_accepts']=p.evaluate("APP_VERSION")
  R['update_banner_shown']=p.evaluate("!!document.getElementById('pwaUpdateBtn')")
  if R['update_banner_shown']:
      p.evaluate("document.getElementById('pwaUpdateBtn').click()"); p.wait_for_timeout(5000)
  R['new_version']=p.evaluate("APP_VERSION"); R['caches_after']=sorted(p.evaluate("caches.keys()"))
  after=p.evaluate(DIGEST); R['after']=after
  R['data_identical']={k:before[k]==after[k] for k in before}
  R['identify_screen']=p.evaluate("getComputedStyle(document.getElementById('empIdScreen')).display!=='none'")
  R['legacy_audit_kept']=p.evaluate("S.get('auditLog').some(a=>a.msg==='Legacy 4.2.7 audit line')")
  R['preupdate_snapshot']=p.evaluate("(()=>{try{return JSON.stringify(RecoveryManager.listSnapshots().map(x=>x.label)).slice(0,120)}catch(e){return String(e)}})()")
  # owner login (legacy, no recovery code) -> code created
  p.evaluate("showOwnerLoginPanel()"); p.fill('#ownerLoginPassword','owner99'); p.press('#ownerLoginPassword','Enter'); p.wait_for_timeout(1500)
  R['owner_login_code_modal']=p.evaluate("document.getElementById('mRecoveryCode').classList.contains('on')")
  R['ac_after_owner_login']=p.evaluate("(({recoveryCodeHash})=>!!recoveryCodeHash)(getAccessControl())")
  p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));Auth.logout()}"); p.wait_for_timeout(500)
  # cashier on migrated data: over-limit credit sale needs owner
  r=p.evaluate("""async()=>{const e=S.get('employees')[0];await Auth.loginEmployee(e.id,'1234');document.getElementById('empIdScreen').style.display='none';onEmployeeSessionStarted();window.toast=()=>{};
     document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));go('pos');resetPosForm();addPosItemFromProduct('p3');document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value='c1';document.getElementById('posDeposit').value='0';document.getElementById('posDueDate').value=todayStr();calcPosTotals();
     const n=S.get('sales').length;document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();
     return {role:Auth.current().role,ownerPopup:document.getElementById('mPriceApproval').classList.contains('on'),saved:S.get('sales').length-n}}""")
  R['cashier_over_limit_on_migrated_data']=r
  p.evaluate("()=>{cancelPriceApproval();document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}")
  R['unlimited_customers_label']=p.evaluate("()=>{Auth.logout();document.getElementById('empIdScreen').style.display='none';return 1}")
  R['dup_products_untouched']=p.evaluate("S.get('products').filter(x=>/rice/i.test(x.name)).map(x=>x.name)")
  # offline relaunch
  ctx.set_offline(True); p.reload(); p.wait_for_timeout(3500)
  R['offline_version']=p.evaluate("APP_VERSION"); off=p.evaluate(DIGEST)
  R['offline_data_matches_online']=all(off[k]==after[k] for k in ['sales','payments','customers','products','expenses','debts'])
  R['errors']=errs; b.close()
srv.shutdown(); print(json.dumps(R,indent=1,ensure_ascii=False))
