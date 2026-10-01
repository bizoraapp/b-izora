"""Bizora 4.3.7 money-controls focused suite (G1-G4 + role/security matrix).
Real browser, real app code, real IndexedDB origin. Usage: python3 t437.py [dir]"""
import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright
DIR=sys.argv[1] if len(sys.argv)>1 else '/home/claude/main'
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=DIR); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8811),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
results=[]
def chk(n,c,info=''):
    results.append((n,bool(c))); print(('PASS' if c else 'FAIL'),'|',n,'|' if c else '| '+json.dumps(info,ensure_ascii=False,default=str)[:700])
PAST='2026-01-05'
SEED="""async(role)=>{
  window.__t=[];window.toast=(m)=>{window.__t.push(String(m))};
  const P='%s';
  S.add('products',{id:'big',sku:'SKU-000001',name:'Fridge',category:'X',cost:50000,price:70000,stock:50,unit:'pcs',tax:0,status:'active',added:P});
  S.add('products',{id:'mid',sku:'SKU-000002',name:'TV',category:'X',cost:20000,price:30000,stock:50,unit:'pcs',tax:0,status:'active',added:P});
  S.add('products',{id:'sm',sku:'SKU-000003',name:'Soap',category:'X',cost:300,price:2000,stock:500,unit:'pcs',tax:0,status:'active',added:P});
  S.add('customers',{id:'cA',name:'Amina',phone:'+237670000001',limit:0,status:'active',added:P});
  S.add('customers',{id:'cB',name:'Bello',phone:'+237670000002',limit:0,status:'active',added:P});
  S.add('sales',{id:'inv1',cid:'cA',amount:10000,date:P,due:P,items:[{name:'x',qty:1,price:10000,subtotal:10000}],status:'pending',docNum:'INV-1'});
  S.add('sales',{id:'invPaid',cid:'cA',amount:1000,date:P,due:P,items:[{name:'x',qty:1,price:1000,subtotal:1000}],status:'paid',docNum:'INV-P'});
  S.add('payments',{id:'yP',invId:'invPaid',cid:'cA',amount:1000,date:P,method:'cash'});
  S.add('sales',{id:'invB',cid:'cB',amount:20000,date:P,due:P,items:[{name:'x',qty:1,price:20000,subtotal:20000}],status:'pending',docNum:'INV-B'});
  S.add('sales',{id:'invB2',cid:'cB',amount:50000,date:P,due:P,items:[{name:'x',qty:1,price:50000,subtotal:50000}],status:'pending',docNum:'INV-B2'});
  S.add('sales',{id:'invX',cid:'cA',amount:2000,date:P,due:P,items:[{name:'x',qty:1,price:2000,subtotal:2000}],status:'cancelled',docNum:'INV-X'});
  S.add('creditLedger',{id:'cl0',cid:'cB',type:'earned',amount:10000,date:P,note:'seed',relatedInvId:null,method:'mobile-money'});
  if(role!=='off'){const salt=genSalt();setAccessControl({enabled:true,pendingSetup:false,ownerPasswordHash:await hashPassword('owner99',salt),ownerPasswordSalt:salt,recoveryCodeHash:'x',recoveryCodeSalt:'y'});}
  if(!['off','owner'].includes(role)){const c=await createEmployee({fullName:'Emp '+role,username:'u'+role,password:'1234',role});await Auth.loginEmployee(c.employee.id,'1234');}
  onEmployeeSessionStarted();
  window.__closeAll=()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  window.__st=()=>({appr:document.getElementById('mPriceApproval').classList.contains('on'),confirm:document.getElementById('mConfirm').classList.contains('on'),confirmMsg:document.getElementById('mConfirmMsg').textContent,paIntro:document.getElementById('paIntro').textContent,paReg:document.getElementById('paRegular').textContent,paProp:document.getElementById('paProposed').textContent,paChange:document.getElementById('paChange').textContent});
  window.__cnt=()=>({pays:S.get('payments').length,credits:S.get('creditLedger').length,sales:S.get('sales').length,exps:S.get('expenses').length});
  window.__pay=(cid,invId,amount,method)=>{__closeAll();openModal('mAddPay');resetPayForm();
    const c=document.getElementById('pCustomer');if(![...c.options].some(o=>o.value===cid))c.add(new Option(cid,cid));c.value=cid;
    const i=document.getElementById('pInvoice');if(![...i.options].some(o=>o.value===invId))i.add(new Option(invId,invId));i.value=invId;
    document.getElementById('pAmount').value=String(amount);document.getElementById('pMethod').value=method||'cash';document.getElementById('pDate').value=todayStr();
    window.__t=[];const b=__cnt();savePay();const a=__cnt();return {dPays:a.pays-b.pays,dCredits:a.credits-b.credits,...__st(),toast:__t.slice(-1)[0]||''}};
  window.__aud=re=>S.get('auditLog').filter(a=>re.test(a.msg)).map(a=>({type:a.type,user:a.user,role:a.role,msg:a.msg,prev:a.prevValue,next:a.newValue,date:a.date,time:a.time,rt:a.recordType}));
  window.__credit=cid=>Math.round(custCreditBalance(cid)*100)/100;
  window.__dc=()=>{const d=S.obj('cashDrawer',{})[todayStr()]||{opening:0};return computeDrawerCash(todayStr(),d.opening)};
  return true}"""%PAST
def page(b,role,vw=1200,throttle=None):
    ctx=b.new_context(service_workers='block',viewport={'width':vw,'height':900}); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://127.0.0.1:8811/index.html'); p.wait_for_timeout(2200); p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
    p.evaluate(SEED,role); return p,errs
def approve(p,pw='owner99'):
    p.fill('#paPassword',pw); p.click('#paApproveBtn'); p.wait_for_timeout(500)
def okConfirm(p):
    p.wait_for_function("()=>document.getElementById('mConfirm').classList.contains('on')",timeout=2000)
    p.evaluate("()=>document.getElementById('mConfirmBtn').click()"); p.wait_for_timeout(250)

with sync_playwright() as pw:
  b=pw.chromium.launch()
  # ======================= G1 — OWNER =======================
  p,errs=page(b,'owner')
  r=p.evaluate("()=>__pay('cA','inv1',4000,'cash')")
  chk('G1 owner: partial payment saved directly (no confirm, no credit)',r['dPays']==1 and r['dCredits']==0 and not r['confirm'] and not r['appr'],r)
  r=p.evaluate("()=>__pay('cA','inv1',6000,'cash')")
  chk('G1 owner: exact payment saved, invoice paid',r['dPays']==1 and r['dCredits']==0 and p.evaluate("S.get('sales').find(s=>s.id==='inv1').status")=='paid',r)
  r=p.evaluate("()=>__pay('cA','inv2x',1,'cash')")
  chk('G1: unknown invoice refused',r['dPays']==0 and 'open invoice' in r['toast'],r)
  for amt,lbl in [(0,'zero'),(-500,'negative'),('abc','non-numeric')]:
      r=p.evaluate(f"()=>__pay('cA','inv1',{json.dumps(amt)},'cash')")
      chk(f'G1: {lbl} amount refused, nothing saved',r['dPays']==0 and r['dCredits']==0,r)
  r=p.evaluate("()=>__pay('cA','inv1','Infinity','cash')")
  chk('G1: Infinity amount refused (was accepted in 4.3.6)',r['dPays']==0 and r['dCredits']==0 and not r['confirm'],r)
  r=p.evaluate("()=>__pay('cA','invX',500,'cash')")
  chk('G1: cancelled invoice refused',r['dPays']==0 and r['dCredits']==0,r)
  r=p.evaluate("()=>__pay('cA','invB',500,'cash')")
  chk('G1: invoice of another customer refused',r['dPays']==0 and r['dCredits']==0,r)
  # overpayment on already-paid invoice
  r=p.evaluate("()=>__pay('cA','invPaid',3000,'cash')")
  chk('G1 owner: overpayment asks for confirmation first; nothing saved yet',r['confirm'] and r['dPays']==0 and r['dCredits']==0 and '3,000' in r['confirmMsg'] and 'Amina' in r['confirmMsg'],r)
  okConfirm(p)
  r=p.evaluate("()=>({credit:__credit('cA'),led:S.get('creditLedger').filter(e=>e.cid==='cA'),a:__aud(/^Overpayment FCFA/)})")
  chk('G1 owner: after confirm, excess banked as credit with method',r['credit']==3000 and r['led'][-1]['method']=='cash' and r['led'][-1]['type']=='earned',r)
  chk('G1 owner: overpayment audited (amount, applied, excess, method, credit before→after)',len(r['a'])==1 and r['a'][0]['type']=='payment' and 'FCFA 0 applied, FCFA 3,000 kept as account credit' in r['a'][0]['msg'] and '(Cash)' in r['a'][0]['msg'] and r['a'][0]['prev']=='0' and r['a'][0]['next']=='3000' and r['a'][0]['user']=='Business Owner' and r['a'][0]['time'],r['a'])
  # overpay on open invoice
  r=p.evaluate("()=>__pay('cB','invB',25000,'mobile-money')"); okConfirm(p)
  r=p.evaluate("()=>({pay:S.get('payments').filter(x=>x.invId==='invB'),credit:__credit('cB'),st:S.get('sales').find(s=>s.id==='invB').status})")
  chk('G1 owner: overpay on open invoice -> 20,000 applied (mobile money), 5,000 credit, invoice paid',len(r['pay'])==1 and r['pay'][0]['amount']==20000 and r['pay'][0]['method']=='mobile-money' and r['credit']==15000 and r['st']=='paid',r)
  # double tap
  r=p.evaluate("()=>{__closeAll();openModal('mAddPay');resetPayForm();const c=document.getElementById('pCustomer');if(![...c.options].some(o=>o.value==='cB'))c.add(new Option('cB','cB'));c.value='cB';const i=document.getElementById('pInvoice');if(![...i.options].some(o=>o.value==='invB2'))i.add(new Option('invB2','invB2'));i.value='invB2';document.getElementById('pAmount').value='1000';const n=S.get('payments').length;savePay();savePay();savePay();return S.get('payments').length-n}")
  chk('G1: rapid repeated taps record the payment once',r==1,r)
  chk('G1 owner: no JS errors',errs==[],errs); p.context.close()

  # ======================= G1 — ACCESS CONTROL OFF =======================
  p,errs=page(b,'off')
  r=p.evaluate("()=>__pay('cA','invPaid',2000,'cash')")
  chk('G1 AC off: overpayment asks for confirmation',r['confirm'] and not r['appr'] and r['dCredits']==0,r)
  p.evaluate("()=>{__closeAll()}")
  r=p.evaluate("()=>({credit:__credit('cA')})")
  chk('G1 AC off: cancelling the confirm saves nothing',r['credit']==0,r)
  r=p.evaluate("()=>__pay('cA','invPaid',2000,'cash')"); okConfirm(p)
  a=p.evaluate("()=>__aud(/^Overpayment FCFA/)")
  chk('G1 AC off: audit names actor honestly (Unidentified user)',len(a)==1 and 'Unidentified user' in a[0]['user'],a)
  chk('G1 AC off: no JS errors',errs==[],errs); p.context.close()

  # ======================= G1 — CASHIER (Owner approval) =======================
  p,errs=page(b,'cashier',390)
  r=p.evaluate("()=>__pay('cA','inv1',3000,'cash')")
  chk('G1 cashier: partial payment unchanged (no approval)',r['dPays']==1 and not r['appr'],r)
  r=p.evaluate("()=>__pay('cA','inv1',12000,'cash')")
  chk('G1 cashier: overpayment -> Owner password pop-up, nothing saved',r['appr'] and not r['confirm'] and r['dPays']==0 and r['dCredits']==0 and '5,000' in r['paChange'] and '7,000' in r['paReg'],r)
  a=p.evaluate("()=>__aud(/^Overpayment — Owner approval required/)")
  chk('G1 cashier: approval request audited (security, cashier)',len(a)==1 and a[0]['type']=='security' and a[0]['user']=='Emp cashier',a)
  approve(p,'wrong')
  r=p.evaluate("()=>({c:__cnt(),f:__aud(/Failed Owner approval attempt for overpayment/),credit:__credit('cA')})")
  chk('G1 cashier: wrong password -> nothing saved, login_failed audited',r['credit']==0 and len(r['f'])==1 and r['f'][0]['type']=='login_failed',r)
  approve(p)
  r=p.evaluate("()=>({credit:__credit('cA'),bal:invBalance('inv1'),a:__aud(/^Overpayment FCFA/),sess:Auth.current().fullName})")
  chk('G1 cashier: correct password -> 7,000 applied, 5,000 credit, session stays cashier',r['credit']==5000 and r['bal']==0 and r['sess']=='Emp cashier',r)
  chk('G1 cashier: overpayment audit shows cashier + approved by Business Owner',len(r['a'])==1 and r['a'][0]['user']=='Emp cashier' and 'approved by Business Owner' in r['a'][0]['msg'],r['a'])
  r=p.evaluate("()=>__pay('cA','invPaid',1000,'cash')")
  chk('G1 cashier: approval is single-use (next overpayment asks again)',r['appr'] and r['dCredits']==0,r)
  p.evaluate("()=>cancelPriceApproval()")
  # stale approval cannot be reused for a different amount
  r=p.evaluate("()=>__pay('cB','invB',25000,'cash')")
  p.evaluate("()=>{cancelPriceApproval()}")
  r=p.evaluate("()=>{const r1=__pay('cB','invB',90000,'cash');return {...r1,credit:__credit('cB')}}")
  chk('G1 cashier: cancelled approval for 25,000 never covers a 90,000 overpayment',r['appr'] and r['dPays']==0 and r['credit']==10000,r)
  approve(p)  # approve 90,000 then verify it only applied to the 90,000 request
  r=p.evaluate("()=>({credit:__credit('cB')})")
  chk('G1 cashier: approved 90,000 applied exactly (70,000 credit added)',r['credit']==80000,r)
  chk('G1 cashier: no JS errors',errs==[],errs); p.context.close()

  # ======================= G2 — refunds =======================
  p,errs=page(b,'owner')
  p.evaluate("()=>{__closeAll();promptRefundCredit('cB')}")
  st=p.evaluate("()=>({on:document.getElementById('mRefundCredit').classList.contains('on'),amt:document.getElementById('rcAmount').textContent,cust:document.getElementById('rcCust').textContent,m:document.getElementById('rcMethod').value})")
  chk('G2 owner: refund screen shows customer, full credit, no method preselected',st['on'] and '10,000' in st['amt'] and st['cust']=='Bello' and st['m']=='',st)
  p.evaluate("()=>confirmRefundCredit()")
  r=p.evaluate("()=>({on:document.getElementById('mRefundCredit').classList.contains('on'),err:document.getElementById('rcError').textContent,credit:__credit('cB')})")
  chk('G2: refund without a method refused; credit unchanged',r['on'] and 'Choose' in r['err'] and r['credit']==10000,r)
  p.select_option('#rcMethod','cash'); p.evaluate("()=>confirmRefundCredit()"); p.wait_for_timeout(200)
  r=p.evaluate("()=>({credit:__credit('cB'),led:S.get('creditLedger').filter(e=>e.cid==='cB').slice(-1)[0],a:__aud(/^Account credit refunded/)})")
  chk('G2 owner: cash refund recorded with method, credit 0',r['credit']==0 and r['led']['type']=='refunded' and r['led']['method']=='cash' and r['led']['amount']==10000,r)
  chk('G2 owner: refund audited (customer, amount, method, user, before→after, time)',len(r['a'])==1 and r['a'][0]['type']=='payment' and 'Bello' in r['a'][0]['msg'] and '(Cash)' in r['a'][0]['msg'] and 'FCFA 10,000 → FCFA 0' in r['a'][0]['msg'] and r['a'][0]['prev']=='10000' and r['a'][0]['next']=='0' and r['a'][0]['user']=='Business Owner' and r['a'][0]['time'] and r['a'][0]['rt']=='creditRefund',r['a'])
  p.evaluate("()=>S.add('creditLedger',{id:'cl9',cid:'cA',type:'earned',amount:4000,date:'2026-01-05',note:'seed',relatedInvId:null,method:'cash'})")
  for args,lbl in [("'cA',5000,'cash'",'refund exceeding credit'),("'cA',0,'cash'",'zero refund'),("'cA',-100,'cash'",'negative refund'),("'cA',1000,'bitcoin'",'unknown method'),("'nobody',1000,'cash'",'unknown customer')]:
      r=p.evaluate(f"()=>{{const n=S.get('creditLedger').length;const ok=refundAccountCredit({args});return {{ok,d:S.get('creditLedger').length-n,credit:__credit('cA')}}}}")
      chk(f'G2 direct call: {lbl} refused, credit unchanged',r['ok']==False and r['d']==0 and r['credit']==4000,r)
  a=p.evaluate("()=>__aud(/refund refused — amount exceeds credit/)")
  chk('G2: over-credit refund attempt audited',len(a)==1 and a[0]['type']=='security',a)
  r=p.evaluate("()=>{const ok=refundAccountCredit('cA',4000,'mobile-money');return {ok,credit:__credit('cA'),m:S.get('creditLedger').slice(-1)[0].method}}")
  chk('G2 owner: non-cash (mobile money) refund recorded with its method',r['ok'] and r['credit']==0 and r['m']=='mobile-money',r)
  chk('G2 owner: no JS errors',errs==[],errs); p.context.close()

  # ---- roles ----
  for role,perm in [('cashier',False),('storekeeper',False),('sales_rep',True),('supervisor',True)]:
      p,errs=page(b,role,390)
      r=p.evaluate("()=>{__closeAll();window.__t=[];promptRefundCredit('cB');return {on:document.getElementById('mRefundCredit').classList.contains('on'),t:__t.slice(-1)[0]||''}}")
      r2=p.evaluate("()=>{window.__t=[];const n=S.get('creditLedger').length;const ok=refundAccountCredit('cB',10000,'cash');return {ok,d:S.get('creditLedger').length-n,credit:__credit('cB'),...__st(),a:__aud(/refund refused \\(no Manage Customers/).length,req:__aud(/refund — Owner approval required/).length}}")
      if not perm:
          chk(f'G2 {role}: Refund screen blocked (no Manage Customers permission)',not r['on'] and 'permission' in r['t'],r)
          chk(f'G2 {role}: direct call refused at operation boundary, audited, credit unchanged',r2['ok']==False and r2['d']==0 and r2['credit']==10000 and r2['a']==1 and not r2['appr'],r2)
      else:
          chk(f'G2 {role}: direct call without approval -> Owner password pop-up, nothing written',r2['ok']==False and r2['d']==0 and r2['credit']==10000 and r2['appr'] and r2['req']==1 and '10,000' in r2['paReg'],r2)
          approve(p,'nope')
          r3=p.evaluate("()=>({credit:__credit('cB'),f:__aud(/Failed Owner approval attempt for account-credit refund/).length})")
          chk(f'G2 {role}: wrong Owner password -> no refund, login_failed audited',r3['credit']==10000 and r3['f']==1,r3)
          approve(p)
          r3=p.evaluate("()=>({credit:__credit('cB'),a:__aud(/^Account credit refunded/),m:S.get('creditLedger').slice(-1)[0].method})")
          chk(f'G2 {role}: approved refund recorded once, attributed to employee + approver',r3['credit']==0 and len(r3['a'])==1 and r3['a'][0]['user']==f'Emp {role}' and 'approved by Business Owner' in r3['a'][0]['msg'] and r3['m']=='cash',r3)
          r4=p.evaluate("()=>{S.add('creditLedger',{id:'cl8',cid:'cB',type:'earned',amount:6000,date:'2026-01-05',note:'s',relatedInvId:null,method:'cash'});const n=S.get('creditLedger').length;refundAccountCredit('cB',6000,'cash');const s1=__st();cancelPriceApproval();refundAccountCredit('cB',3000,'cash');return {d:S.get('creditLedger').length-n,appr:document.getElementById('mPriceApproval').classList.contains('on'),s1}}")
          chk(f'G2 {role}: approval not reusable — each refund request asks again, nothing written meanwhile',r4['d']==0 and r4['appr'],r4)
          p.evaluate("()=>cancelPriceApproval()")
      # G1 role boundary
      r5=p.evaluate("()=>__pay('cA','invPaid',500,'cash')")
      if role=='storekeeper':
          chk('G1 storekeeper: payment refused (no Record Sales permission)',r5['dPays']==0 and r5['dCredits']==0 and not r5['appr'] and 'permission' in r5['toast'],r5)
      else:
          chk(f'G1 {role}: overpayment needs Owner approval',r5['appr'] and r5['dCredits']==0,r5)
          p.evaluate("()=>cancelPriceApproval()")
      # G4 role boundary
      r6=p.evaluate("()=>{__closeAll();window.__t=[];go('inventory');const el=document.getElementById('cdOpening');const before=JSON.stringify(S.obj('cashDrawer',{}));el.value='99999';saveCashDrawer();commitCashDrawerEdit();return {changed:JSON.stringify(S.obj('cashDrawer',{}))!==before,t:__t.join('|'),a:__aud(/^Cash drawer opening/).length,page:document.getElementById('page-inventory').classList.contains('active')}}")
      allowed=role in ('storekeeper','supervisor')
      if allowed: chk(f'G4 {role}: drawer edit allowed (Manage Inventory) and audited',r6['changed'] and r6['a']==1,r6)
      else: chk(f'G4 {role}: drawer edit refused at operation boundary, drawer unchanged, no audit',not r6['changed'] and r6['a']==0 and 'permission' in r6['t'],r6)
      chk(f'{role}: no JS errors',errs==[],errs); p.context.close()

  # ======================= G3 — physical cash =======================
  p,errs=page(b,'owner')
  def dc(): return p.evaluate("()=>__dc()")
  p.evaluate("()=>{__closeAll();go('inventory');const el=document.getElementById('cdOpening');el.value='10000';saveCashDrawer();commitCashDrawerEdit();}")
  d0=dc()
  chk('G3: opening cash 10,000 -> expected 10,000',d0['expected']==10000,d0)
  POS="""([pid,method,recv])=>{__closeAll();go('pos');resetPosForm();addPosItemFromProduct(pid);document.getElementById('posTypeCash').checked=true;setPosType('cash');document.getElementById('posMethod').value=method;document.getElementById('posReceived').value=String(recv);calcPosTotals();document.getElementById('posCheckoutBtn').disabled=false;const n=S.get('posSales').length;checkoutPos();__closeAll();const s=S.get('posSales').slice(-1)[0];return {saved:S.get('posSales').length-n,total:s.total,paid:s.paid,change:s.change,method:s.method}}"""
  r=p.evaluate(POS,['big','cash',75000]); d1=dc()
  chk('G3: cash sale 70,000 paid with 75,000 (5,000 change) adds exactly 70,000',r['saved']==1 and r['change']==5000 and d1['expected']-d0['expected']==70000 and d1['cashSales']==70000,{'sale':r,'dc':d1})
  r=p.evaluate(POS,['mid','mobile-money',30000]); d2=dc()
  chk('G3: Mobile Money sale 30,000 adds 0',r['saved']==1 and d2['expected']==d1['expected'],d2)
  r=p.evaluate("()=>__pay('cB','invB',20000,'cash')"); d3=dc()
  chk('G3: cash payment 20,000 on credit adds 20,000',r['dPays']==1 and d3['expected']-d2['expected']==20000,d3)
  r=p.evaluate("()=>{__closeAll();openAddExpense();document.getElementById('expAmount').value='5000';document.getElementById('expPayMethod').value='cash';const n=S.get('expenses').length;saveExpense();return {d:S.get('expenses').length-n,m:S.get('expenses').slice(-1)[0].payMethod,a:__aud(/^Expense logged/).slice(-1)[0]}}"); d4=dc()
  chk('G3: cash expense 5,000 subtracts 5,000 (method saved + in audit)',r['d']==1 and r['m']=='cash' and '(Cash)' in r['a']['msg'] and d3['expected']-d4['expected']==5000,{'r':r,'dc':d4})
  r=p.evaluate("()=>__pay('cA','invPaid',10000,'mobile-money')"); okConfirm(p); d5=dc()
  chk('G3: account credit created by a Mobile Money overpayment adds 0',p.evaluate("__credit('cA')")==10000 and d5['expected']==d4['expected'],d5)
  r=p.evaluate("()=>refundAccountCredit('cA',10000,'cash')"); d6=dc()
  chk('G3: cash refund 10,000 subtracts 10,000',r and d5['expected']-d6['expected']==10000,d6)
  chk('G3 FIXTURE: opening 10,000 + cash sale 70,000 + MoMo sale 30,000 + cash payment 20,000 − cash expense 5,000 − cash refund 10,000 = 85,000',d6['expected']==85000,d6)
  ui=p.evaluate("()=>{__closeAll();go('inventory');return {exp:document.getElementById('cdExpected').textContent,cs:document.getElementById('cdCashSales').textContent,cin:document.getElementById('cdCashIn').textContent,ce:document.getElementById('cdCashExpenses').textContent,cr:document.getElementById('cdCashRefunds').textContent,coll:document.getElementById('cdCollections').textContent,note:document.getElementById('cdNote').textContent}}")
  chk('G3 UI: Expected Cash shows FCFA 85,000 with breakdown lines',ui['exp']=='FCFA 85,000' and ui['cs']=='FCFA 70,000' and ui['cin']=='FCFA 20,000' and ui['ce']=='FCFA 5,000' and ui['cr']=='FCFA 10,000' and 'physical cash only' in ui['note'],ui)
  old=p.evaluate("()=>{const td=todayStr();const o=10000;const cs=S.get('posSales').filter(s=>s.date===td&&s.method==='cash').reduce((a,s)=>a+s.paid,0);const col=S.get('payments').filter(x=>x.date===td).reduce((a,x)=>a+parseFloat(x.amount||0),0);return o+cs+col}")
  chk('G3 (reference): the 4.3.6 formula would have shown 105,000 for the same day',old==105000,old)
  base=dc()['expected']
  for js,lbl in [("__pay('cB','invB2',3000,'bank-transfer')",'bank payment'),("__pay('cB','invB2',2000,'card')",'card payment'),("__pay('cB','invB2',1000,'cheque')",'cheque payment'),
                 ("(()=>{__closeAll();openAddExpense();document.getElementById('expAmount').value='7000';document.getElementById('expPayMethod').value='mobile-money';saveExpense();})()",'non-cash expense'),
                 ("(()=>{S.add('creditLedger',{id:'cl7',cid:'cB',type:'earned',amount:2500,date:'2026-01-05',note:'s',relatedInvId:null,method:'cash'});return refundAccountCredit('cB',2500,'bank-transfer')})()",'non-cash refund'),
                 ("(()=>{__closeAll();go('pos');resetPosForm();addPosItemFromProduct('sm');document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value='cA';document.getElementById('posDeposit').value='0';document.getElementById('posDueDate').value=todayStr();calcPosTotals();document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();__closeAll();})()",'credit sale with no deposit')]:
      p.evaluate("()=>"+js); p.wait_for_timeout(100); v=dc()['expected']
      chk(f'G3: {lbl} does not change physical cash',v==base,{'before':base,'after':v})
  p.evaluate("()=>{__closeAll();go('pos');resetPosForm();addPosItemFromProduct('sm');document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value='cA';document.getElementById('posDeposit').value='1500';document.getElementById('posDueDate').value=todayStr();calcPosTotals();document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();__closeAll();}")
  v=dc()['expected']
  chk('G3: credit sale with a 1,500 cash deposit adds 1,500',v-base==1500,{'before':base,'after':v}); base=v
  p.evaluate("()=>{const t=S.get('sales').find(s=>s.cid==='cA'&&invBalance(s.id)>0&&s.status!=='cancelled');S.add('creditLedger',{id:'cl6',cid:'cA',type:'earned',amount:500,date:'2026-01-05',note:'s',relatedInvId:null,method:'cash'});promptApplyCredit('cA');document.getElementById('mConfirmBtn').click();}")
  v=dc()['expected']
  chk('G3: applying account credit to an invoice does not change physical cash',v==base,{'before':base,'after':v})
  # legacy records (no method) are reported, not guessed
  p.evaluate("()=>{S.add('expenses',{id:'legacyE',category:'rent',amount:4000,date:todayStr(),notes:''});S.add('payments',{id:'legacyP',invId:'invB2',cid:'cB',amount:1000,date:todayStr()});S.add('creditLedger',{id:'legacyC',cid:'cB',type:'earned',amount:700,date:todayStr(),note:'old',relatedInvId:null});renderCashDrawer();}")
  d=dc(); note=p.evaluate("document.getElementById('cdNote').textContent")
  chk('G3: records without a method are left out and reported on screen (not guessed)',d['expected']==base and d['unrecorded']==3 and '3 record(s)' in note,{'d':d,'note':note})
  r=p.evaluate("()=>{editExpense('legacyE');return {v:document.getElementById('expPayMethod').value,unk:!document.getElementById('expPayMethodUnknown').hidden}}")
  chk('G3: editing an older expense shows "Not recorded" (never silently turned into cash)',r['v']=='' and r['unk'],r)
  p.evaluate("()=>{document.getElementById('expAmount').value='4000';saveExpense();}")
  chk('G3: saving an older expense without choosing keeps it method-less (history not rewritten)','payMethod' not in p.evaluate("S.get('expenses').find(e=>e.id==='legacyE')"),'')
  r=p.evaluate("()=>{openAddExpense();return {v:document.getElementById('expPayMethod').value,unkHidden:document.getElementById('expPayMethodUnknown').hidden}}")
  chk('G3: new expense defaults to Cash; "Not recorded" not offered',r['v']=='cash' and r['unkHidden'],r)
  chk('G3: no JS errors',errs==[],errs)

  # ======================= G4 — drawer edits =======================
  p.evaluate("()=>{__closeAll();go('inventory');}")
  n0=p.evaluate("()=>__aud(/^Cash drawer/).length")
  p.click('#cdClosing'); p.keyboard.type('84500'); p.keyboard.press('Tab'); p.wait_for_timeout(200)
  r=p.evaluate("()=>({drawer:S.obj('cashDrawer',{})[todayStr()],a:__aud(/^Cash drawer closing/),v:document.getElementById('cdVariance').textContent})")
  chk('G4: typing a closing count (5 keystrokes) saves it and writes ONE audit entry',r['drawer']['closing']==84500 and len(r['a'])==1,r)
  chk('G4: closing audit has previous (blank) and new value, user, date and time',r['a'][0]['prev']=='' and r['a'][0]['next']=='84500' and '(blank) → FCFA 84,500' in r['a'][0]['msg'] and r['a'][0]['user']=='Business Owner' and r['a'][0]['date'] and r['a'][0]['time'] and r['a'][0]['type']=='edit',r['a'])
  p.fill('#cdOpening','12000'); p.keyboard.press('Tab'); p.wait_for_timeout(200)
  r=p.evaluate("()=>__aud(/^Cash drawer opening/).slice(-1)[0]")
  chk('G4: opening edit audited 10,000 → 12,000',r['prev']=='10000' and r['next']=='12000' and 'FCFA 10,000 → FCFA 12,000' in r['msg'],r)
  p.click('#cdOpening'); p.keyboard.press('Tab'); p.wait_for_timeout(100)
  chk('G4: focusing and leaving without a change writes no audit entry',p.evaluate("()=>__aud(/^Cash drawer/).length")==n0+2,'')
  before=p.evaluate("()=>JSON.stringify(S.obj('cashDrawer',{})[todayStr()])")
  p.fill('#cdOpening','-500'); p.keyboard.press('Tab'); p.wait_for_timeout(200)
  r=p.evaluate("()=>({d:JSON.stringify(S.obj('cashDrawer',{})[todayStr()]),field:document.getElementById('cdOpening').value,t:__t.slice(-1)[0]||''})")
  chk('G4: negative amount refused — drawer not corrupted, field restored, message shown',r['d']==before and r['field']=='12,000' and '0 or more' in r['t'],r)
  p.evaluate("()=>{const el=document.getElementById('cdClosing');el.value='80000';saveCashDrawer();Object.defineProperty(document,'visibilityState',{value:'hidden',configurable:true});document.dispatchEvent(new Event('visibilitychange'));}")
  a=p.evaluate("()=>__aud(/^Cash drawer closing/).slice(-1)[0]")
  chk('G4: edit still open when the app is hidden/closed is still audited',a['prev']=='84500' and a['next']=='80000',a)
  chk('G4: no JS errors',errs==[],errs); p.context.close()

  # ======================= i18n (FR) =======================
  p,errs=page(b,'owner',390)
  r=p.evaluate("()=>{setLang('fr');__closeAll();go('inventory');promptRefundCredit('cB');const rc={t:document.querySelector('#mRefundCredit .modal-title').textContent,lbl:document.querySelector('#mRefundCredit [data-i18n=refund_method_label]').textContent,opt:document.getElementById('rcMethod').options[1].textContent};__closeAll();return {rc,note:document.getElementById('cdNote').textContent,cin:document.querySelector('[data-i18n=cd_lbl_cash_in]').textContent}}")
  chk('i18n FR: refund screen and drawer lines translated',"Rembourser" in r['rc']['t'] and 'rendu' in r['rc']['lbl'] and 'Comptant' in r['rc']['opt'] and 'espèces' in r['note'] and 'espèces' in r['cin'],r)
  r=p.evaluate("()=>{const x=__pay('cA','invPaid',1000,'cash');return x}")
  chk('i18n FR: overpayment confirm message in French',r['confirm'] and 'avoir' in r['confirmMsg'],r)
  p.screenshot(path='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/g1_confirm_fr_390.png')
  p.evaluate("()=>{__closeAll();go('inventory')}"); p.wait_for_timeout(300)
  p.locator('#cdNote').scroll_into_view_if_needed(); p.screenshot(path='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/g3_drawer_fr_390.png')
  chk('i18n FR: no JS errors',errs==[],errs); p.context.close()
  b.close()
srv.shutdown()
print('\nTOTAL',len(results),'PASS',sum(1 for _,c in results if c),'FAIL',sum(1 for _,c in results if not c))
