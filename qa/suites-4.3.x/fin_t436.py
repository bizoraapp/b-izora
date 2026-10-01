import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright
DIR=sys.argv[1] if len(sys.argv)>1 else '/home/claude/main'
SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=DIR); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8801),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
results=[]
def chk(n,c,info=''):
    results.append((n,bool(c))); print(('PASS' if c else 'FAIL'),'|',n,'|',json.dumps(info,ensure_ascii=False)[:600] if not c else '')
SEED="""async(role)=>{
  window.__t=[];window.toast=(m)=>{window.__t.push(String(m))};
  S.add('products',{id:'phone',sku:'SKU-000001',name:'Phone',category:'Phones',cost:25000,price:30000,stock:50,unit:'pcs',tax:0,status:'active',added:todayStr()});
  S.add('products',{id:'case',sku:'SKU-000002',name:'Phone Case',category:'Acc',cost:500,price:1000,stock:50,unit:'pcs',tax:0,status:'active',added:todayStr()});
  S.add('products',{id:'item',sku:'SKU-000003',name:'Item2000',category:'Acc',cost:1,price:2000,stock:50,unit:'pcs',tax:0,status:'active',added:todayStr()});
  S.add('customers',{id:'cA',name:'Amina',phone:'+237670000001',limit:5000,status:'active',added:todayStr()});
  S.add('sales',{id:'old1',cid:'cA',amount:3000,date:todayStr(),due:todayStr(),items:[{name:'Old debt',qty:1,price:3000,subtotal:3000}],status:'pending',docNum:'INV-OLD1'});
  S.add('customers',{id:'cB',name:'Bello',phone:'+237670000002',limit:100000,status:'blocked',added:todayStr()});
  S.add('customers',{id:'cC',name:'Chidi',phone:'+237670000003',limit:5000,status:'active',added:todayStr()});
  S.add('customers',{id:'cZ',name:'Zara',phone:'+237670000004',limit:0,status:'active',added:todayStr()});
  if(role!=='off'){const salt=genSalt();setAccessControl({enabled:true,pendingSetup:false,ownerPasswordHash:await hashPassword('owner99',salt),ownerPasswordSalt:salt,recoveryCodeHash:'x',recoveryCodeSalt:'y'});}
  if(!['off','owner'].includes(role)){const c=await createEmployee({fullName:'Emp '+role,username:'u'+role,password:'1234',role});await Auth.loginEmployee(c.employee.id,'1234');window.__emp=c.employee.id;}
  onEmployeeSessionStarted();
  window.__close=()=>document.querySelectorAll('.modal-bg.on').forEach(m=>{if(m.id!=='mPriceApproval')m.classList.remove('on')});
  window.__closeAll=()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  window.__cart=(cid,items,deposit)=>{document.querySelectorAll('.modal-bg.on').forEach(m=>{if(m.id==='mReceipt')m.classList.remove('on')});go('pos');resetPosForm();items.forEach(pid=>addPosItemFromProduct(pid));document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value=cid;document.getElementById('posDeposit').value=String(deposit||0);document.getElementById('posDueDate').value=todayStr();calcPosTotals();};
  window.__n=()=>S.get('sales').length;
  window.__state=()=>({appr:document.getElementById('mPriceApproval').classList.contains('on'),confirm:document.getElementById('mConfirm').classList.contains('on'),paChange:document.getElementById('paChange').textContent,paReg:document.getElementById('paRegular').textContent,confirmMsg:document.getElementById('mConfirmMsg').textContent,okLbl:document.getElementById('mConfirmBtn').textContent});
  window.__checkout=()=>{window.__t=[];document.getElementById('posCheckoutBtn').disabled=false;const n=__n();checkoutPos();return {saved:__n()-n,...__state(),toast:window.__t.slice(-1)[0]||''}};
  window.__aud=re=>S.get('auditLog').filter(a=>re.test(a.msg)).map(a=>({type:a.type,user:a.user,role:a.role,msg:a.msg,prev:a.prevValue,next:a.newValue,date:a.date,time:a.time}));
  window.__direct=(cid,grand,deposit)=>{window.__t=[];const n=__n();finalizeCreditSale(cid,todayStr(),grand,deposit||0,todayStr(),'');__closeAll();return {saved:__n()-n,toast:window.__t.slice(-1)[0]||''}};
  return true}"""
def page(b,role,vw=1200):
    p=b.new_context(service_workers='block',viewport={'width':vw,'height':900}).new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://127.0.0.1:8801/index.html'); p.wait_for_timeout(2200); p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
    p.evaluate(SEED,role); return p,errs
def approve(p,pw='owner99'):
    p.fill('#paPassword',pw); p.click('#paApproveBtn'); p.wait_for_timeout(450)
with sync_playwright() as pw:
  b=pw.chromium.launch()
  # ================= KNOWN ISSUE as CASHIER (real clicks) =================
  p,errs=page(b,'cashier',390)
  p.evaluate("()=>__cart('cA',['phone'],0)")
  banner=p.evaluate("()=>document.getElementById('creditLimitWarnTxt').textContent")
  p.click('#posCheckoutBtn'); p.wait_for_timeout(300)
  st=p.evaluate("()=>({...__state(),saved:__n()})")
  chk('Known issue: cashier gets Owner password pop-up (not a one-tap Confirm); nothing saved yet',st['appr'] and not st['confirm'] and st['saved']==1 and '33,000' in st['paChange'] and '3,000 / FCFA 5,000' in st['paReg'],{'state':st,'banner':banner})
  chk('Banner text updated (Owner approval required)','Owner approval is required' in banner,banner)
  a=p.evaluate("()=>__aud(/Credit limit exceeded — Owner approval required/)")
  chk('Audit A: over-limit attempt logged with customer, debt, limit, sale, deposit, resulting; actor = cashier',len(a)==1 and a[0]['type']=='security' and a[0]['user']=='Emp cashier' and 'Amina' in a[0]['msg'] and 'debt FCFA 3,000, limit FCFA 5,000, sale FCFA 30,000, deposit FCFA 0, resulting FCFA 33,000' in a[0]['msg'],a)
  approve(p,'wrong')
  r=p.evaluate("()=>({saved:__n(),err:document.getElementById('paError').textContent,c:__aud(/Failed Owner approval attempt for credit-limit override/)})")
  chk('Wrong password: no sale; Audit C logged (login_failed, cashier)',r['saved']==1 and 'Incorrect' in r['err'] and len(r['c'])==1 and r['c'][0]['type']=='login_failed' and r['c'][0]['user']=='Emp cashier',r)
  approve(p)
  r=p.evaluate("()=>({saved:__n(),debt:custDebt('cA'),b:__aud(/Credit-limit override approved by/),d:__aud(/Credit sale over limit/),gen:__aud(/^Credit sale INV/),sess:Auth.current().fullName})")
  chk('Correct password: sale saved at 30,000, debt 33,000',r['saved']==2 and r['debt']==33000,r)
  chk('Audit B: approval logged (approver Business Owner, requesting cashier, prev/new debt)',len(r['b'])==1 and 'approved by Business Owner' in r['b'][0]['msg'] and r['b'][0]['user']=='Emp cashier' and r['b'][0]['prev']=='3000' and r['b'][0]['next']=='33000',r['b'])
  chk('Audit D: over-limit sale logged with invoice, debt → resulting, limit, sale, deposit, approver',len(r['d'])==1 and 'debt FCFA 3,000 → FCFA 33,000, limit FCFA 5,000, sale FCFA 30,000, deposit FCFA 0, approved by Business Owner' in r['d'][0]['msg'] and r['d'][0]['user']=='Emp cashier',r['d'])
  chk('Existing "Credit sale INV…" line still written; session not switched to Owner',len(r['gen'])==1 and r['sess']=='Emp cashier',r)
  r=p.evaluate("()=>{__closeAll();__cart('cA',['case'],0);return __checkout()}")
  chk('Approval is single-use: next over-limit sale asks again',r['appr'] and r['saved']==0,r)
  p.evaluate("()=>cancelPriceApproval()")
  chk('Cashier known-issue: no JS errors',errs==[],errs); p.context.close()

  # ================= BOUNDARIES (Cashier: approval vs none) =================
  p,errs=page(b,'cashier')
  res=p.evaluate("""()=>{
    const setDebt=(cid,amt)=>{S.set('sales',S.get('sales').filter(s=>s.cid!==cid));S.set('payments',S.get('payments').filter(x=>x.cid!==cid));if(amt>0)S.add('sales',{id:'d_'+cid+amt,cid,amount:amt,date:todayStr(),due:todayStr(),items:[{name:'x',qty:1,price:amt,subtotal:amt}],status:'pending'});};
    const setLimit=(cid,lim)=>{const c=S.get('customers').find(x=>x.id===cid);const n={...c};if(lim===undefined)delete n.limit;else n.limit=lim;S.update('customers',n);};
    const probe=(cid,price)=>{S.update('products',{...S.get('products').find(p=>p.id==='phone'),price});__cart(cid,['phone'],0);const r=__checkout();cancelPriceApproval();__closeAll();if(r.saved){const inv=S.get('sales').slice(-1)[0];S.set('sales',S.get('sales').filter(s=>s.id!==inv.id));}return r.appr?'APPROVAL':(r.saved?'saved':'refused');};
    const R={};setLimit('cA',5000);setDebt('cA',3000);
    R.exact=probe('cA',2000);R.plus1=probe('cA',2001);
    setDebt('cA',5000);R.atLimit=probe('cA',1);setDebt('cA',8000);R.overLimit=probe('cA',1);
    setDebt('cA',0);R.noDebtAtLimit=probe('cA',5000);R.noDebtPlus1=probe('cA',5001);
    setLimit('cA',0);setDebt('cA',3000);R.zero=probe('cA',1000000);setLimit('cA',undefined);R.missing=probe('cA',1000000);setLimit('cA',-5000);R.negative=probe('cA',1000000);
    setLimit('cA',5000);setDebt('cA',3000);S.add('payments',{id:'pp',invId:'d_cA3000',cid:'cA',amount:1000,date:todayStr(),method:'cash'});
    R.partialRepayAtLimit=probe('cA',3000);R.partialRepayPlus1=probe('cA',3001);
    return R}""")
  exp={'exact':'saved','plus1':'APPROVAL','atLimit':'APPROVAL','overLimit':'APPROVAL','noDebtAtLimit':'saved','noDebtPlus1':'APPROVAL','zero':'saved','missing':'saved','negative':'saved','partialRepayAtLimit':'saved','partialRepayPlus1':'APPROVAL'}
  for k,v in exp.items(): chk(f'Boundary (cashier): {k} -> {v}',res[k]==v,res)
  chk('Boundaries: no JS errors',errs==[],errs); p.context.close()

  # ================= AUTHORIZATION / STALE / REUSE (cashier) =================
  p,errs=page(b,'cashier')
  def open_over(): return p.evaluate("()=>{__closeAll();__cart('cA',['phone'],0);return __checkout()}")
  # different amount: approve, then cart changes before checkout re-runs (simulate by changing cart while modal open, then approve)
  open_over(); p.fill('#paPassword','owner99')
  p.evaluate("()=>{addPosItemFromProduct('phone');addPosItemFromProduct('phone')}")  # 30,000 -> 90,000 while pop-up open
  p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("()=>({saved:__n(),reasked:__state().appr,paChange:__state().paChange})")
  chk('Cart changed 30,000→90,000 while pop-up open: 30,000 approval NOT used for 90,000; new approval asked for 93,000',r['saved']==1 and r['reasked'] and '93,000' in r['paChange'],r)
  p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
  r=open_over()
  chk('Stale approval discarded: after the cart changed, a fresh 30,000 sale (cart reset) asks for approval again — nothing saved',r['appr'] and r['saved']==0 and p.evaluate("()=>__n()")==1,r)
  p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
  # approval then customer change -> direct finalize for different customer
  open_over(); approve(p)
  p.evaluate("()=>__closeAll()")
  n0=p.evaluate("()=>__n()")
  # after approval the sale was already saved; now test stale: approve, but change customer before the re-run consumes
  p.evaluate("()=>{__cart('cA',['phone'],0);__checkout();}"); p.fill('#paPassword','owner99')
  p.evaluate("()=>{document.getElementById('posCustomer').value='cC'}")
  p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("()=>({savedForC:S.get('sales').filter(s=>s.cid==='cC').length,savedForA:S.get('sales').filter(s=>s.cid==='cA').length,reasked:__state().appr,paRegular:__state().paReg})")
  chk('Customer changed after approval: approval for Amina not used for Chidi (Chidi asks for its own approval)',r['savedForC']==0 and r['reasked'],r)
  p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
  # approval after debt changes: grant token via approval, but debt changes before finalize consumes -> use direct finalize path
  r=p.evaluate("""async()=>{__cart('cC',['phone'],0);const o=__checkout();return o.appr}""")
  p.fill('#paPassword','owner99')
  p.evaluate("()=>{S.add('sales',{id:'extra',cid:'cC',amount:500,date:todayStr(),due:todayStr(),items:[],status:'pending'})}")  # debt changes while pop-up open
  p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("()=>({savedC:S.get('sales').filter(s=>s.cid==='cC'&&s.id!=='extra').length,reasked:__state().appr,paReg:__state().paReg})")
  chk('Debt changed while approving: stale approval not used; asks again with new debt',r['savedC']==0 and r['reasked'] and '500' in r['paReg'],r)
  p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
  # approval after limit changes
  p.evaluate("()=>{__cart('cC',['phone'],0);__checkout()}"); p.fill('#paPassword','owner99')
  p.evaluate("()=>{const c=S.get('customers').find(x=>x.id==='cC');S.update('customers',{...c,limit:6000})}")
  p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("()=>({savedC:S.get('sales').filter(s=>s.cid==='cC'&&s.id!=='extra').length,reasked:__state().appr,paReg:__state().paReg})")
  chk('Limit changed while approving: stale approval not used; asks again with new limit',r['savedC']==0 and r['reasked'] and '6,000' in r['paReg'],r)
  p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
  # direct finalize without approval (non-owner)
  r=p.evaluate("()=>{__cart('cA',['phone'],0);return __direct('cA',30000,0)}")
  a=p.evaluate("()=>__aud(/over credit limit without Owner approval/).slice(-1)")
  chk('Direct finalizeCreditSale() over limit without approval: refused + audited',r['saved']==0 and 'needs the Business Owner' in r['toast'] and len(a)==1,{'r':r,'a':a})
  # stale grand argument (the old 30,000 vs 90,000 bug)
  r=p.evaluate("()=>{__cart('cZ',['phone','phone','phone'],0);return __direct('cZ',30000,0)}")
  chk('Direct finalizeCreditSale() with a total that differs from the cart (30,000 vs 90,000 cart): refused',r['saved']==0 and 'changed' in r['toast'],r)
  # deposit > total via direct
  r=p.evaluate("()=>{__cart('cZ',['case'],0);return __direct('cZ',1000,5000)}")
  chk('Direct finalizeCreditSale() with deposit > total: refused',r['saved']==0,r)
  # blocked direct
  r=p.evaluate("()=>{__cart('cB',['case'],0);return __direct('cB',1000,0)}")
  e=p.evaluate("()=>__aud(/customer is blocked/).slice(-1)")
  chk('Blocked customer via direct finalizeCreditSale(): refused + Audit E',r['saved']==0 and len(e)==1 and e[0]['type']=='security',{'r':r,'e':e})
  r=p.evaluate("()=>{__cart('cB',['case'],0);return __checkout()}")
  chk('Blocked customer via UI: refused, no approval offered',r['saved']==0 and not r['appr'] and 'blocked' in r['toast'].lower(),r)
  # reuse: approve for 30,000 then try to reuse token via a second direct call after it has been consumed
  open_over(); approve(p); p.evaluate("()=>__closeAll()")
  r=p.evaluate("()=>{__cart('cA',['phone'],0);return __direct('cA',30000,0)}")
  chk('Approval reuse: second direct sale with identical values refused (token already consumed)',r['saved']==0,r)
  # logout between approval grant and use
  p.evaluate("()=>{__cart('cC',['phone'],0);__checkout()}")
  r=p.evaluate("""async()=>{const spec=_creditSpec('cC',creditCheck('cC',30000,0),30000,0);return 1}""")
  # grant via real approval but intercept: approve, then (token consumed immediately by re-run). To test logout, approve while re-run is blocked by a price issue:
  p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
  r=p.evaluate("""async()=>{__cart('cC',['phone'],0);__checkout();return 1}""")
  p.fill('#paPassword','owner99')
  p.evaluate("()=>{posItems[0].discount=50}")   # makes the re-run stop at the price check -> token remains unused
  p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("""async()=>{const unusedTokenExists=peekApproval(_creditSpec('cC',creditCheck('cC',15000,0),15000,0))||peekApproval(_creditSpec('cC',creditCheck('cC',30000,0),30000,0));
    Auth.logout();document.getElementById('empIdScreen').style.display='none';await Auth.loginEmployee(window.__emp,'1234');onEmployeeSessionStarted();
    __cart('cC',['phone'],0);const d=__direct('cC',30000,0);return {tokenBeforeLogout:unusedTokenExists,afterRelogin:d}}""")
  chk('Logout/switch before approval use: approval gone, direct sale refused',r['afterRelogin']['saved']==0,r)
  # session change: approval granted to user X can't be used by user Y
  chk('Authorization tests: no JS errors',errs==[],errs); p.context.close()

  # ================= ROLES =================
  for role in ['owner','supervisor','sales_rep','cashier','storekeeper','off']:
    p,errs=page(b,role)
    R={}
    R['within']=p.evaluate("()=>{__cart('cA',['case'],0);return __checkout()}"); p.evaluate("()=>__closeAll()")
    R['over']=p.evaluate("()=>{__cart('cA',['phone'],0);return __checkout()}")
    if R['over']['confirm']:
        R['confirmMsg']=R['over']['confirmMsg']; p.evaluate("()=>document.getElementById('mConfirmBtn').click()"); p.wait_for_timeout(200)
    R['afterOver']=p.evaluate("()=>({debt:custDebt('cA'),d:__aud(/Credit sale over limit/).slice(-1)})")
    p.evaluate("()=>{cancelPriceApproval&&cancelPriceApproval();__closeAll()}")
    R['direct']=p.evaluate("()=>{__cart('cA',['phone'],0);return __direct('cA',30000,0)}")
    R['directBlocked']=p.evaluate("()=>{__cart('cB',['case'],0);return __direct('cB',1000,0)}")
    R['F']=p.evaluate("()=>__aud(/Unauthorized credit-sale attempt/)")
    R['errs']=errs; p.context.close()
    if role in ('supervisor','sales_rep','cashier'):
        chk(f'{role}: within limit saved; over limit -> Owner password pop-up; direct over-limit refused; direct blocked refused',R['within']['saved']==1 and R['over']['appr'] and not R['over']['confirm'] and R['over']['saved']==0 and R['direct']['saved']==0 and R['directBlocked']['saved']==0,R)
    elif role=='storekeeper':
        chk('storekeeper: UI refused; direct finalizeCreditSale() refused (no Record Sales) + Audit F',R['within']['saved']==0 and R['over']['saved']==0 and R['direct']['saved']==0 and R['directBlocked']['saved']==0 and len(R['F'])>=2 and R['F'][0]['type']=='security' and R['F'][0]['user']=='Emp storekeeper',R)
    elif role=='owner':
        d=R['afterOver']['d']
        chk('owner: within saved; over limit -> simple confirm (no password), saved; Audit D says own override',R['within']['saved']==1 and R['over']['confirm'] and not R['over']['appr'] and R['afterOver']['debt']==34000 and d and 'Business Owner (own override)' in d[0]['msg'] and d[0]['user']=='Business Owner' and 'Override the credit limit as Business Owner' in R['confirmMsg'],R)
        chk('owner: direct finalizeCreditSale() over limit allowed (owner) and logged; blocked still refused',R['direct']['saved']==1 and R['directBlocked']['saved']==0,R)
    else:
        d=R['afterOver']['d']
        chk('Access Control OFF: behaviour preserved (simple confirm, saved) but actor NOT "Business Owner" in new audit entries',R['within']['saved']==1 and R['over']['confirm'] and R['afterOver']['debt']==34000 and d and d[0]['user']=='Unidentified user (Access Control off)' and 'no sign-in (Access Control off)' in d[0]['msg'],R)
        chk('Access Control OFF: blocked customer still refused on direct call',R['directBlocked']['saved']==0,R)
    chk(f'{role}: no JS errors',R['errs']==[],R['errs'])

  # ================= Owner confirm re-check (stale owner confirm) =================
  p,errs=page(b,'owner')
  r=p.evaluate("()=>{__cart('cA',['phone'],0);__checkout();addPosItemFromProduct('phone');const n=__n();document.getElementById('mConfirmBtn').click();__closeAll();return {saved:__n()-n,toast:window.__t.slice(-1)[0]||''}}")
  chk('Owner confirm: cart changed after the confirm opened -> refused, must check out again',r['saved']==0 and 'changed' in r['toast'],r)
  p.context.close()

  # ================= CUSTOMER LIMIT / STATUS =================
  for role in ['sales_rep','supervisor']:
    p,errs=page(b,role)
    def edit(js): return p.evaluate(f"""()=>{{go('customers');editCust('cA');{js};window.__t=[];saveCust();return {{appr:__state().appr,limit:S.get('customers').find(c=>c.id==='cA').limit,status:S.get('customers').find(c=>c.id==='cA').status,toast:window.__t.slice(-1)[0]||''}}}}""")
    r=edit("document.getElementById('cLimit').value='50000'")
    chk(f'{role}: raising limit 5,000→50,000 needs Owner approval (not saved yet)',r['appr'] and r['limit']==5000,r)
    approve(p,'bad')
    r2=p.evaluate("()=>({limit:S.get('customers').find(c=>c.id==='cA').limit,c:__aud(/Failed Owner approval attempt for customer change/)})")
    chk(f'{role}: wrong password -> not saved, Audit C (customer change)',r2['limit']==5000 and len(r2['c'])==1,r2)
    approve(p)
    r3=p.evaluate("()=>({limit:S.get('customers').find(c=>c.id==='cA').limit,g:__aud(/Customer credit limit changed/).slice(-1)})")
    chk(f'{role}: correct password -> saved; Audit G old→new, approver, requesting employee',r3['limit']==50000 and r3['g'] and 'FCFA 5,000 → FCFA 50,000' in r3['g'][0]['msg'] and 'approved by Business Owner' in r3['g'][0]['msg'] and r3['g'][0]['user']==f'Emp {role}' and r3['g'][0]['prev']=='FCFA 5,000',r3)
    p.evaluate("()=>__closeAll()")
    r=edit("document.getElementById('cLimit').value='0'")
    chk(f'{role}: removing the limit (→ Unlimited) needs approval',r['appr'] and r['limit']==50000,r)
    p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
    r=edit("document.getElementById('cLimit').value='1000'")
    g=p.evaluate("()=>__aud(/Customer credit limit changed/).slice(-1)")
    chk(f'{role}: lowering the limit saves without approval, audited old→new',(not r['appr']) and r['limit']==1000 and 'FCFA 50,000 → FCFA 1,000' in g[0]['msg'] and 'approved' not in g[0]['msg'],{'r':r,'g':g})
    p.evaluate("()=>__closeAll()")
    r=edit("document.getElementById('cStatus').value='blocked'")
    h=p.evaluate("()=>__aud(/Customer status changed/).slice(-1)")
    chk(f'{role}: blocking saves without approval, Audit H active→blocked',(not r['appr']) and r['status']=='blocked' and 'active → blocked' in h[0]['msg'],{'r':r,'h':h})
    p.evaluate("()=>__closeAll()")
    r=edit("document.getElementById('cStatus').value='active'")
    chk(f'{role}: unblocking needs Owner approval',r['appr'] and r['status']=='blocked',r)
    p.fill('#paPassword','owner99')
    p.evaluate("()=>{document.getElementById('cLimit').value='999999'}")   # form value changed after approval requested
    p.click('#paApproveBtn'); p.wait_for_timeout(450)
    r=p.evaluate("()=>({status:S.get('customers').find(c=>c.id==='cA').status,limit:S.get('customers').find(c=>c.id==='cA').limit,reasked:__state().appr})")
    chk(f'{role}: approval for unblock not usable after form values change (asks again, nothing saved)',r['status']=='blocked' and r['limit']==1000 and r['reasked'],r)
    p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
    r=edit("document.getElementById('cStatus').value='active'"); approve(p)
    h=p.evaluate("()=>({s:S.get('customers').find(c=>c.id==='cA').status,h:__aud(/Customer status changed/).slice(-1)})")
    chk(f'{role}: unblock approved -> saved, Audit H blocked→active with approver',h['s']=='active' and 'blocked → active' in h['h'][0]['msg'] and 'approved by Business Owner' in h['h'][0]['msg'],h)
    p.evaluate("()=>__closeAll()")
    # reuse
    r=p.evaluate("""()=>{go('customers');editCust('cA');document.getElementById('cStatus').value='blocked';saveCust();__closeAll();editCust('cA');document.getElementById('cStatus').value='active';window.__t=[];saveCust();return {appr:__state().appr,status:S.get('customers').find(c=>c.id==='cA').status}}""")
    chk(f'{role}: earlier approval cannot be reused for a later unblock',r['appr'] and r['status']=='blocked',r)
    p.evaluate("()=>{cancelPriceApproval();__closeAll()}")
    # new customer: no approval regardless of limit
    r=p.evaluate("""()=>{go('customers');openModal('mAddCust');resetCustForm();document.getElementById('cName').value='New Guy';document.getElementById('cPhone').value='+237670009999';document.getElementById('cLimit').value='';window.__t=[];const n=S.get('customers').length;saveCust();__closeAll();
      openModal('mAddCust');resetCustForm();document.getElementById('cName').value='Big Limit';document.getElementById('cPhone').value='+237670009998';document.getElementById('cLimit').value='9000000';saveCust();__closeAll();return {created:S.get('customers').length-n,appr:__state().appr}}""")
    chk(f'{role}: new customer creation needs no approval (unlimited or any limit)',r['created']==2 and not r['appr'],r)
    chk(f'{role} customer edits: no JS errors',errs==[],errs); p.context.close()
  # cashier (no manageCustomers) unchanged
  p,errs=page(b,'cashier')
  r=p.evaluate("()=>{go('customers');editCust&&editCust('cA');document.getElementById('cLimit').value='50000';window.__t=[];saveCust();return {limit:S.get('customers').find(c=>c.id==='cA').limit,toast:window.__t.slice(-1)[0]||''}}")
  chk('cashier: manageCustomers permission still required first (unchanged)',r['limit']==5000 and 'permission' in r['toast'],r)
  p.context.close()
  # owner / AC off customer edits: direct, audited, actor label
  for role in ['owner','off']:
    p,errs=page(b,role)
    r=p.evaluate("""()=>{go('customers');editCust('cB');document.getElementById('cStatus').value='active';document.getElementById('cLimit').value='0';saveCust();__closeAll();const c=S.get('customers').find(x=>x.id==='cB');const a=__aud(/Customer (status|credit limit) changed/);return {status:c.status,limit:c.limit,a}}""")
    who='Business Owner' if role=='owner' else 'Unidentified user (Access Control off)'
    chk(f'{role}: customer unblock + limit removal save directly; audited with actor "{who}"',r['status']=='active' and r['limit']==0 and len(r['a'])==2 and all(x['user']==who for x in r['a']) and any('FCFA 100,000 → Unlimited' in x['msg'] for x in r['a']),r)
    p.context.close()

  # ================= UI: Unlimited labels + EN/FR + 360 =================
  p,errs=page(b,'owner',360)
  r=p.evaluate("""()=>{go('customers');const row=[...document.querySelectorAll('#page-customers tbody tr')].find(tr=>/Zara/.test(tr.innerText));const rowTxt=row?row.innerText.replace(/\\s+/g,' '):'';
    openModal('mAddCust');resetCustForm();const hint=document.querySelector('[data-i18n=cust_limit_hint]').textContent;__closeAll();
    viewCust('cZ');const ov=document.getElementById('mViewCust').innerText;__closeAll();
    setLang('fr');go('customers');const rowFr=([...document.querySelectorAll('#page-customers tbody tr')].find(tr=>/Zara/.test(tr.innerText))||{innerText:''}).innerText.replace(/\\s+/g,' ');
    openModal('mAddCust');const hintFr=document.querySelector('[data-i18n=cust_limit_hint]').textContent;__closeAll();
    __cart('cA',['phone'],0);window.__t=[];document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();const cm=document.getElementById('mConfirmMsg').textContent,ok=document.getElementById('mConfirmBtn').textContent,banner=document.getElementById('creditLimitWarnTxt').textContent;__closeAll();
    setLang('en');return {rowTxt,hint,ovHas:/Credit limit: Unlimited/.test(ov),rowFr,hintFr,cm,ok,banner,fits:document.documentElement.scrollWidth<=innerWidth}}""")
  chk('UI: customer list shows "Unlimited"; form hint "0 or empty = Unlimited credit"; overview badge',('Unlimited' in r['rowTxt']) and r['hint']=='0 or empty = Unlimited credit' and r['ovHas'],r)
  chk('FR: "Illimitée", hint, Owner confirm and banner translated',('Illimitée' in r['rowFr']) and r['hintFr']=='0 ou vide = crédit illimité' and 'Dépasser la limite' in r['cm'] and r['ok']=='Dépasser la limite' and 'Limite de crédit dépassée' in r['banner'],r)
  chk('360px: no horizontal overflow',r['fits'],r)
  p.context.close()
  p,errs=page(b,'cashier',360); p.evaluate("()=>setLang('fr')")
  p.evaluate("()=>{__cart('cA',['phone'],0);__checkout()}"); p.wait_for_timeout(400)
  r=p.evaluate("()=>({intro:paIntro.textContent,l2:paL2.textContent,l3:paL3.textContent,l4:paL4.textContent,fits:(()=>{const m=document.querySelector('#mPriceApproval .modal').getBoundingClientRect();return m.left>=0&&m.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth})()})")
  p.screenshot(path=SP+'credit_appr_fr_360.png')
  chk('FR/360: credit-override approval pop-up translated and fits',('limite de crédit' in r['intro']) and r['l2']=='Dette actuelle / limite' and r['l3']=='Vente (acompte)' and r['l4']=='Dette après la vente' and r['fits'],r)
  chk('FR/360: no JS errors',errs==[],errs); p.context.close()
  b.close()
srv.shutdown()
f=[x for x in results if not x[1]]
print('\nTOTAL',len(results),'FAIL',len(f)); [print('  FAILED:',x[0]) for x in f]
