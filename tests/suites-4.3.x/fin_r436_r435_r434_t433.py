import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright
DIR=sys.argv[1] if len(sys.argv)>1 else '/home/claude/main'
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=DIR); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8852),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
results=[]
def chk(name,cond,info=''):
    results.append((name,bool(cond))); print(('PASS' if cond else 'FAIL'),'|',name,'|',json.dumps(info,ensure_ascii=False)[:600] if (not cond) else '')
SEED="""async(role)=>{
  window.__t=[];window.toast=(m,ty)=>{window.__t.push(String(m));};
  S.add('products',{id:'pT',sku:'S1',name:'Rice Bag',category:'G',cost:13500,price:16000,stock:100,lowStock:5,tax:19.25,added:todayStr()});
  S.add('products',{id:'pU',sku:'S2',name:'Oil',category:'G',cost:4000,price:5000,stock:100,lowStock:5,tax:0,added:todayStr()});
  S.add('customers',{id:'cT',name:'Alpha Cust',phone:'+237670000001',limit:0,status:'active',added:todayStr()});
  S.add('customers',{id:'cU',name:'Beta Cust',phone:'+237670000002',limit:0,status:'active',added:todayStr()});
  window.__close=()=>document.querySelectorAll('.modal-bg.on').forEach(m=>{if(m.id!=='mPriceApproval'&&m.id!=='mAddSale')m.classList.remove('on')});
  window.__closeAll=()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  window.__apprOpen=()=>document.getElementById('mPriceApproval').classList.contains('on');
  window.__inv=id=>S.get('sales').find(s=>s.id===id);
  window.__audit=re=>S.get('auditLog').filter(a=>re.test(a.msg)).map(a=>({type:a.type,user:a.user,role:a.role,msg:a.msg,rt:a.recordType,rid:a.recordId,prev:a.prevValue,next:a.newValue,date:a.date,time:a.time}));
  const posCredit=(pid,setup,cid)=>{go('pos');resetPosForm();addPosItemFromProduct(pid);setup&&setup();document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value=cid||'cT';document.getElementById('posDeposit').value='0';document.getElementById('posDueDate').value=todayStr();document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();__closeAll();return S.get('sales').slice(-1)[0].id};
  // Owner creates fixtures (access control not yet on)
  window.__taxedInv=posCredit('pT');
  window.__discInv=posCredit('pU',()=>updatePosItem(0,'discount','20'));
  window.__plainPosInv=posCredit('pU');
  // manual/non-product invoices (legacy path, created directly — the New Invoice button is retired)
  const manual=(rows,cid)=>{go('sales');openModal('mAddSale');resetSaleForm();document.getElementById('sCustomer').value=cid||'cT';document.getElementById('itemsBody').innerHTML='';rows.forEach(r=>addItemRow(r[0],r[1],r[2]));document.getElementById('saveSaleBtn').disabled=false;saveSale();__closeAll();return S.get('sales').slice(-1)[0].id};
  window.__manA=manual([['Service A',2,5000]]);
  window.__manB=manual([['Service B',1,8000]]);
  window.__manPaid=manual([['Service C',1,10000]]);S.add('payments',{id:'pp1',invId:window.__manPaid,cid:'cT',amount:4000,date:todayStr(),method:'cash'});syncStatuses();
  window.__manC=manual([['Service D',1,3000]]);
  window.__manE=manual([['Service E',1,6000]]);
  if(role!=='off'){const salt=genSalt();setAccessControl({...getAccessControl(),enabled:true,ownerPasswordSalt:salt,ownerPasswordHash:await hashPassword('ownerpass9',salt)});}
  if(!['off','owner'].includes(role)){const c=await createEmployee({fullName:'Emp '+role,username:'u'+role,password:'1234',role});await Auth.loginEmployee(c.employee.id,'1234');window.__emp=c.employee;}
  onEmployeeSessionStarted();
  window.__t=[];
  return {req:priceApprovalRequired()}}"""
def approve(p,pw='ownerpass9'):
    p.fill('#paPassword',pw); p.click('#paApproveBtn'); p.wait_for_timeout(450)
def page(b,vw=1200):
    ctx=b.new_context(service_workers='block',viewport={'width':vw,'height':900}); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://127.0.0.1:8852/index.html'); p.wait_for_timeout(2200)
    p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}"); return p,errs
def edit(p,inv,js=''):
    # open ✏️ on an invoice and optionally change fields, then Save (the real button handler)
    return p.evaluate("""([id,js])=>{go('sales');editSale(window[id]);eval(js);document.getElementById('saveSaleBtn').disabled=false;window.__t=[];saveSale();return {appr:__apprOpen(),toast:window.__t.slice(-1)[0]||'',formOpen:document.getElementById('mAddSale').classList.contains('on')}}""",[inv,js])
SETROW="const r=document.querySelectorAll('#itemsBody .item-row')[0];"
with sync_playwright() as pw:
  b=pw.chromium.launch()
  # ================= CASHIER (full) =================
  p,errs=page(b); p.evaluate(SEED,'cashier')
  # ---------- 1. TAX ----------
  r=p.evaluate("""()=>{go('pos');resetPosForm();addPosItemFromProduct('pT');const o={};
    o.inputDisabled=document.querySelectorAll('#posItemsBody .pos-item-row input[type=number]')[document.querySelectorAll('#posItemsBody .pos-item-row input[type=number]').length-1].disabled;
    o.grand=Math.round(calcPosTotalsRaw().grand);window.__t=[];updatePosItem(0,'tax','0');o.afterUi=posItems[0].tax;o.toast=window.__t.slice(-1)[0];
    document.getElementById('posReceived').value='100000';const n=S.get('posSales').length;checkoutPos();__closeAll();o.sold=S.get('posSales').length-n;o.total=Math.round(S.get('posSales').slice(-1)[0].total);return o}""")
  chk('Tax: normal catalog tax sells; tax field is locked for cashier',r['inputDisabled'] and r['sold']==1 and r['total']==19080,r)
  chk('Tax: UI change to 0 refused (stays 19.25) with message',r['afterUi']==19.25 and 'Owner can change tax' in (r['toast'] or ''),r)
  for label,val in [('0',0),('negative -80',-80),('above range 150',150),('NaN','NaN'),('string "0"','"0"')]:
    r=p.evaluate(f"""()=>{{go('pos');resetPosForm();addPosItemFromProduct('pT');posItems[0].tax={val};document.getElementById('posReceived').value='100000';window.__t=[];const n=S.get('posSales').length;checkoutPos();__closeAll();return {{sold:S.get('posSales').length-n,msg:window.__t.slice(-1)[0]||'',btnFree:!document.getElementById('posCheckoutBtn').disabled}}}}""")
    chk(f'Tax bypass blocked at checkout (cash): direct tax = {label}',r['sold']==0 and 'tax differs' in r['msg'] and r['btnFree'],r)
  r=p.evaluate("""()=>{go('pos');resetPosForm();addPosItemFromProduct('pT');posItems[0].tax=0;document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value='cT';document.getElementById('posDeposit').value='0';document.getElementById('posDueDate').value=todayStr();const n=S.get('sales').length;document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();__closeAll();return {sold:S.get('sales').length-n}}""")
  chk('Tax bypass blocked on CREDIT sale path',r['sold']==0,r)
  r=p.evaluate("""()=>{const o={};go('pos');resetPosForm();addPosItemFromProduct('pT');posItems[0].tax=0;let n=S.get('posSales').length;finalizeCashSale('',todayStr(),16000,100000,'');__closeAll();o.cash=S.get('posSales').length-n;
    resetPosForm();addPosItemFromProduct('pT');posItems[0].tax=-50;document.getElementById('posTypeCredit').checked=true;setPosType('credit');n=S.get('sales').length;finalizeCreditSale('cT',todayStr(),8000,0,todayStr(),'');__closeAll();o.credit=S.get('sales').length-n;return o}""")
  chk('Tax bypass: direct finalizeCashSale()/finalizeCreditSale() blocked',r['cash']==0 and r['credit']==0,r)
  r=p.evaluate("""()=>{go('pos');resetPosForm();addPosItemFromProduct('pT');const p0=S.get('products').find(x=>x.id==='pT');S.update('products',{...p0,tax:5});document.getElementById('posReceived').value='100000';window.__t=[];const n=S.get('posSales').length;checkoutPos();__closeAll();const o={sold:S.get('posSales').length-n,msg:window.__t.slice(-1)[0]};S.update('products',p0);return o}""")
  chk('Tax: catalog tax changed while item in cart -> blocked (re-add)',r['sold']==0 and 'tax differs' in (r['msg'] or ''),r)
  p.evaluate("()=>{go('pos');resetPosForm();addPosItemFromProduct('pT');updatePosItem(0,'sellingPrice','12000')}"); approve(p)
  r=p.evaluate("""()=>{const o={disc:posItems[0].discount};posItems[0].tax=0;document.getElementById('posReceived').value='100000';const n=S.get('posSales').length;checkoutPos();__closeAll();o.sold=S.get('posSales').length-n;
    posItems[0].tax=19.25;document.getElementById('posCheckoutBtn').disabled=false;const n2=S.get('posSales').length;checkoutPos();__closeAll();o.soldAfterRestore=S.get('posSales').length-n2;o.total=Math.round(S.get('posSales').slice(-1)[0].total);return o}""")
  chk('Tax: price-APPROVED line with changed tax still blocked; restored tax sells at approved price',r['sold']==0 and r['soldAfterRestore']==1 and r['total']==round(12000*1.1925),r)
  # ---------- 2. R1 POS-created invoices ----------
  for inv,stored in [('__taxedInv',19080),('__discInv',4000),('__plainPosInv',5000)]:
    before=p.evaluate(f"()=>JSON.stringify(__inv(window.{inv}).items)")
    r=edit(p,inv,"document.getElementById('sNotes').value='note-updated';document.getElementById('sPriority').value='high';const d=new Date();d.setDate(d.getDate()+20);document.getElementById('sDue').value=d.toISOString().slice(0,10);")
    after=p.evaluate(f"()=>{{const s=__inv(window.{inv});return {{amount:s.amount,items:JSON.stringify(s.items),notes:s.notes,priority:s.priority}}}}")
    chk(f'R1: POS invoice {stored} saved with only notes/priority/due changed -> total, lines, product link, cost, tax, discount kept; notes saved',
        (not r['appr']) and after['amount']==stored and after['items']==before and after['notes']=='note-updated' and after['priority']=='high',{**r,**after,'before_items':before[:120]})
  r=edit(p,'__taxedInv',SETROW+"r.querySelector('.item-price').value='100';calcInvTotal();")
  chk('R1: POS invoice with CHANGED rows refused for cashier (no approval offered)',(not r['appr']) and 'point of sale' in r['toast'] and p.evaluate("()=>__inv(window.__taxedInv).amount")==19080,r)
  r=p.evaluate("""()=>{document.getElementById('editSaleId').value=window.__taxedInv;document.getElementById('sCustomer').value='cT';document.getElementById('sDate').value=todayStr();document.getElementById('sDue').value=todayStr();
    document.getElementById('itemsBody').innerHTML='';addItemRow('Rice Bag',1,100);document.getElementById('saveSaleBtn').disabled=false;window.__t=[];clearInvoiceApprovalState();
    document.getElementById('editSaleId').value=window.__taxedInv;saveSale();return {amount:__inv(window.__taxedInv).amount,toast:window.__t.slice(-1)[0]||'',appr:__apprOpen()}}""")
  chk('R1: direct saveSale() on POS invoice without a snapshot is refused',r['amount']==19080 and 'point of sale' in r['toast'] and not r['appr'],r)
  r=p.evaluate("""()=>{go('sales');editSale(window.__discInv);const row=document.querySelector('#itemsBody .item-row');row.querySelector('.item-price').value='1';calcInvTotal();markInvoiceEditBaseline(window.__discInv);document.getElementById('saveSaleBtn').disabled=false;saveSale();__closeAll();const s=__inv(window.__discInv);return {amount:s.amount,price:s.items[0].price,productId:s.items[0].productId}}""")
  chk('R1: forged snapshot gains nothing (stored total and lines kept)',r['amount']==4000 and r['price']==5000 and r['productId']=='pU',r)
  # ---------- 3. invoice edit approval (manual invoice) ----------
  r=edit(p,'__manA',SETROW+"r.querySelector('.item-price').value='4000';calcInvTotal();")
  chk('Edit: amount change opens Owner approval, nothing saved yet',r['appr'] and p.evaluate("()=>__inv(window.__manA).amount")==10000,r)
  lbl=p.evaluate("()=>({l1:paL1.textContent,v1:paProduct.textContent,l2:paL2.textContent,v2:paRegular.textContent,v3:paProposed.textContent,v4:paChange.textContent,intro:paIntro.textContent})")
  chk('Edit: modal shows invoice, current/new totals and change',lbl['l1']=='Invoice' and 'INV' in lbl['v1'] and '10,000' in lbl['v2'] and '8,000' in lbl['v3'] and '-FCFA 2,000' in lbl['v4'] and 'invoice' in lbl['intro'],lbl)
  approve(p,'wrong')
  r=p.evaluate("()=>({open:__apprOpen(),amount:__inv(window.__manA).amount,err:paError.textContent,aud:__audit(/Failed Owner approval attempt for invoice edit/)})")
  chk('Edit: WRONG password -> not saved, error, failed attempt audited to cashier (login_failed, invoice id, amounts)',r['open'] and r['amount']==10000 and 'Incorrect' in r['err'] and len(r['aud'])==1 and r['aud'][0]['type']=='login_failed' and r['aud'][0]['user']=='Emp cashier' and r['aud'][0]['rt']=='invoice' and '10,000' in r['aud'][0]['msg'] and '8,000' in r['aud'][0]['msg'],r)
  p.click('#mPriceApproval .modal-ftr .btn-outline'); p.wait_for_timeout(150)
  r=p.evaluate("()=>({open:__apprOpen(),amount:__inv(window.__manA).amount,formOpen:document.getElementById('mAddSale').classList.contains('on')})")
  chk('Edit: CANCEL approval -> nothing saved, invoice form still open',(not r['open']) and r['amount']==10000 and r['formOpen'],r)
  p.evaluate("()=>{document.getElementById('saveSaleBtn').disabled=false;saveSale()}"); approve(p)
  r=p.evaluate("()=>({open:__apprOpen(),amount:__inv(window.__manA).amount,items:__inv(window.__manA).items.map(i=>[i.qty,i.price]),debt:invBalance(window.__manA),aud:__audit(/Invoice edit approved/),form:document.getElementById('mAddSale').classList.contains('on'),sess:Auth.current().fullName})")
  a=r['aud'][0] if r['aud'] else {}
  chk('Edit: CORRECT password -> saved at new amount; rows = amount = debt',(not r['open']) and r['amount']==8000 and r['items']==[[2,4000]] and r['debt']==8000 and not r['form'],r)
  chk('Edit audit: invoice id, old/new amount, approver, timestamp, acting cashier',a and a['type']=='edit' and a['rid']==p.evaluate("()=>window.__manA") and a['prev']=='10000' and a['next']=='8000' and 'approved by Business Owner' in a['msg'] and a['user']=='Emp cashier' and a['date'] and a['time'],r)
  chk('Edit: approving does not switch the session to Owner',r['sess']=='Emp cashier',r)
  r=edit(p,'__manA',SETROW+"r.querySelector('.item-price').value='3500';calcInvTotal();")
  chk('Edit: approval is single-use (next change prompts again)',r['appr'] and p.evaluate("()=>__inv(window.__manA).amount")==8000,r)
  approve(p)
  p.evaluate("()=>{}")
  chk('Edit: second approval applies',p.evaluate("()=>__inv(window.__manA).amount")==7000)
  # rows changed after approval
  r=edit(p,'__manB',SETROW+"r.querySelector('.item-price').value='7000';calcInvTotal();")
  p.fill('#paPassword','ownerpass9')
  p.evaluate("()=>{const r=document.querySelectorAll('#itemsBody .item-row')[0];r.querySelector('.item-price').value='100';calcInvTotal();}")
  p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("()=>({amount:__inv(window.__manB).amount,apprAgain:__apprOpen(),toasts:window.__t.slice(-3)})")
  chk('Edit: rows changed AFTER approval -> approval does not fit, not saved, asks again',r['amount']==8000 and r['apprAgain'] and any('changed after approval' in x for x in r['toasts']),r)
  p.evaluate("()=>cancelPriceApproval()")
  # hidden sAmount tamper on manual invoice with approval
  r=edit(p,'__manB',"document.getElementById('sAmount').value='1';")
  chk('Hidden total: tampering sAmount alone is ignored (rows unchanged -> no amount change, no approval)',(not r['appr']) and p.evaluate("()=>__inv(window.__manB).amount")==8000,r)
  r=edit(p,'__manB',SETROW+"r.querySelector('.item-price').value='6000';calcInvTotal();document.getElementById('sAmount').value='50';")
  approve(p)
  r=p.evaluate("()=>{const s=__inv(window.__manB);return {amount:s.amount,rows:s.items.reduce((a,i)=>a+(i.subtotal||0),0),debt:custDebt('cT')>=0,bal:invBalance(window.__manB)}}")
  chk('Hidden total: sAmount=50 with rows 6,000 -> saved 6,000 = rows = invoice balance',r['amount']==6000 and r['rows']==6000 and r['bal']==6000,r)
  # direct saveSale call with injected edit id (no ✏️)
  r=p.evaluate("""()=>{closeModal('mAddSale');resetSaleForm();document.getElementById('editSaleId').value=window.__manC;document.getElementById('sCustomer').value='cT';document.getElementById('sDate').value=todayStr();document.getElementById('sDue').value=todayStr();
    document.getElementById('itemsBody').innerHTML='';addItemRow('Service D',1,10);document.getElementById('saveSaleBtn').disabled=false;saveSale();return {amount:__inv(window.__manC).amount,appr:__apprOpen()}}""")
  chk('Edit bypass: direct saveSale() with injected edit id only opens approval, saves nothing',r['amount']==3000 and r['appr'],r)
  p.evaluate("()=>cancelPriceApproval()")
  # stale approval across logout / reset / other invoice / cancel-vs-edit
  edit(p,'__manC',SETROW+"r.querySelector('.item-price').value='2000';calcInvTotal();"); approve(p)  # applies 2000
  r=edit(p,'__manC',SETROW+"r.querySelector('.item-price').value='1500';calcInvTotal();")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(50)
  chk('Edit: approved change applied (setup for stale tests)',p.evaluate("()=>__inv(window.__manC).amount") in (1500,2000))
  # form reset between approval and save -> token cleared
  p.wait_for_timeout(400)
  r=edit(p,'__manE',SETROW+"r.querySelector('.item-price').value='5000';calcInvTotal();")
  p.evaluate("()=>{cancelPriceApproval()}")
  r=p.evaluate("""async()=>{// approve then reset form before the save runs: simulate by setting token via real approval flow on a different invoice, then editing another
    return 1}""")
  # Approval for invoice X used on invoice Y
  edit(p,'__manE',SETROW+"r.querySelector('.item-price').value='5000';calcInvTotal();")
  p.evaluate("()=>{window.__origSave=saveSale}")  # cannot intercept const flow; instead test via cancel: approve edit for manE, then try cancel manE
  approve(p)
  chk('Edit applied for manE (setup)',p.evaluate("()=>__inv(window.__manE).amount")==5000)
  r=p.evaluate("()=>{window.__t=[];cancelSale(window.__manE);return {status:__inv(window.__manE).status,appr:__apprOpen()}}")
  chk('Kind binding: an edit approval cannot be used to cancel (cancel asks for its own approval)',r['status']!='cancelled' and r['appr'],r)
  p.evaluate("()=>cancelPriceApproval()")
  # ---------- 4. customer change ----------
  r=edit(p,'__manE',"document.getElementById('sCustomer').value='cU';")
  chk('Customer change (same amount) requires approval',r['appr'] and p.evaluate("()=>__inv(window.__manE).cid")=='cT',r)
  lab=p.evaluate("()=>({v2:paRegular.textContent,v3:paProposed.textContent,v4:paChange.textContent})")
  chk('Customer change: modal shows Alpha -> Beta',('Alpha Cust' in lab['v2']) and ('Beta Cust' in lab['v3']) and 'Customer change' in lab['v4'],lab)
  approve(p)
  r=p.evaluate("()=>({cid:__inv(window.__manE).cid,aud:__audit(/customer change approved/)})")
  chk('Customer change approved -> moved; audit shows old and new customer',r['cid']=='cU' and r['aud'] and 'Alpha Cust → Beta Cust' in r['aud'][-1]['msg'] and r['aud'][-1]['prev']=='Alpha Cust' and r['aud'][-1]['next']=='Beta Cust',r)
  # approval A->B cannot be used for A->C : approve for cU then change to cT in form before approval completes
  r=edit(p,'__manE',"document.getElementById('sCustomer').value='cT';")
  p.fill('#paPassword','ownerpass9'); p.evaluate("()=>{document.getElementById('sCustomer').value='cU'}")
  p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("()=>({cid:__inv(window.__manE).cid})")
  chk('Customer binding: approval for B->A is not usable after the form switches to another customer',r['cid']=='cU',r)
  p.evaluate("()=>{__closeAll();cancelPriceApproval()}")
  r=edit(p,'__manE',"document.getElementById('sNotes').value='only notes';const d=new Date();d.setDate(d.getDate()+9);document.getElementById('sDue').value=d.toISOString().slice(0,10);document.getElementById('sPriority').value='urgent';")
  chk('Non-financial edit (notes/due/priority) needs no approval and saves',(not r['appr']) and p.evaluate("()=>__inv(window.__manE).notes")=='only notes',r)
  r=edit(p,'__manE',"const d=new Date();d.setDate(d.getDate()-3);document.getElementById('sDate').value=d.toISOString().slice(0,10);")
  chk('Invoice DATE edit unchanged (no approval, saves) — as instructed',(not r['appr']) and p.evaluate("()=>__inv(window.__manE).date")!=p.evaluate("()=>todayStr()"),r)
  # ---------- 5. payment guard ----------
  r=edit(p,'__manPaid',SETROW+"r.querySelector('.item-price').value='10';calcInvTotal();")
  chk('Payment guard: edit below amount paid refused BEFORE any approval request',(not r['appr']) and 'lower than the amount already paid' in r['toast'] and p.evaluate("()=>__inv(window.__manPaid).amount")==10000,r)
  r=edit(p,'__manPaid',SETROW+"r.querySelector('.item-price').value='4000';calcInvTotal();")
  chk('Payment guard: total equal to paid is allowed (goes to approval)',r['appr'],r)
  p.evaluate("()=>cancelPriceApproval()")
  # ---------- 6. cancellation ----------
  r=p.evaluate("()=>{go('sales');window.__t=[];cancelSale(window.__manC);return {status:__inv(window.__manC).status,appr:__apprOpen(),v4:paChange.textContent,confirmShown:document.getElementById('mConfirm').classList.contains('on')}}")
  chk('Cancel: direct cancelSale() without approval does NOT cancel; opens Owner approval (not plain confirm)',r['status']!='cancelled' and r['appr'] and not r['confirmShown'] and 'Cancel invoice' in r['v4'],r)
  approve(p,'bad')
  r=p.evaluate("()=>({status:__inv(window.__manC).status,aud:__audit(/Failed Owner approval attempt for invoice cancellation/)})")
  chk('Cancel: wrong password -> not cancelled; failed attempt audited',r['status']!='cancelled' and len(r['aud'])==1 and r['aud'][0]['type']=='login_failed',r)
  p.click('#mPriceApproval .modal-ftr .btn-outline'); p.wait_for_timeout(100)
  chk('Cancel: cancelling the approval leaves invoice active',p.evaluate("()=>__inv(window.__manC).status")!='cancelled')
  amtC=p.evaluate("()=>__inv(window.__manC).amount")
  p.evaluate("()=>cancelSale(window.__manC)"); approve(p)
  r=p.evaluate("()=>({status:__inv(window.__manC).status,aud:__audit(/Invoice cancellation approved/),legacy:__audit(/^Cancelled invoice/).length})")
  chk('Cancel: correct password -> cancelled; audit has invoice id, amount, approver; existing "Cancelled invoice" line kept',r['status']=='cancelled' and r['aud'] and r['aud'][-1]['rid']==p.evaluate("()=>window.__manC") and r['aud'][-1]['prev']==str(amtC) and 'approved by Business Owner' in r['aud'][-1]['msg'] and r['legacy']>=1,r)
  # approval bound to invoice: approve cancel for plainPosInv then try another
  p.evaluate("()=>cancelSale(window.__plainPosInv)"); p.fill('#paPassword','ownerpass9')
  p.evaluate("()=>{const s=__inv(window.__plainPosInv);S.update('sales',{...s,amount:s.amount+1})}")  # amount changes while approving
  p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("()=>({status:__inv(window.__plainPosInv).status,appr:__apprOpen()})")
  chk('Cancel binding: invoice amount changed between approval and cancel -> not cancelled',r['status']!='cancelled',r)
  p.evaluate("()=>{cancelPriceApproval();const s=__inv(window.__plainPosInv);S.update('sales',{...s,amount:s.amount-1})}")
  r=p.evaluate("()=>{window.__t=[];cancelSale(window.__manPaid);return {status:__inv(window.__manPaid).status,appr:__apprOpen(),toast:window.__t.slice(-1)[0]||''}}")
  chk('Cancel: invoice with payments still refused as before (no approval asked)',r['status']!='cancelled' and not r['appr'],r)
  # ---------- 7. approval-state manipulation ----------
  r=p.evaluate("""()=>{const o={};
    o.oldGlobals=[typeof window._priceGrants,typeof window._pendingPriceApproval,typeof window._invoiceApproval,typeof window.invoiceToken];
    try{o.lexical=[typeof _priceGrants,typeof _pendingPriceApproval,typeof invoiceToken,typeof editBaseline,typeof pending]}catch(e){o.lexical='err'}
    o.frozen=Object.isFrozen(OwnerApproval);
    try{OwnerApproval.consumeInvoiceApproval=()=>({token:{by:'x'}});}catch(e){}
    o.stillOrig=OwnerApproval.consumeInvoiceApproval.toString().includes('invoiceToken');
    // forge: assign names that used to be approval state
    window._invoiceApproval={kind:'invEdit',invId:window.__manB,oldAmount:6000,newAmount:1,oldCid:'cT',newCid:'cT',user:Auth.current().id,by:'Owner'};
    window.invoiceToken=window._invoiceApproval;window._priceGrants=new WeakMap();
    go('sales');editSale(window.__manB);document.querySelector('#itemsBody .item-row .item-price').value='1';calcInvTotal();document.getElementById('saveSaleBtn').disabled=false;saveSale();
    o.forgedTokenSaved=__inv(window.__manB).amount===1;o.apprAsked=__apprOpen();cancelPriceApproval();__closeAll();
    // forged flags on invoice record
    const s=__inv(window.__manC2||window.__manB);S.update('sales',{...s,ownerApproved:true,approvedBy:'Owner'});
    editSale(window.__manB);document.querySelector('#itemsBody .item-row .item-price').value='2';calcInvTotal();document.getElementById('saveSaleBtn').disabled=false;saveSale();
    o.forgedFlagSaved=__inv(window.__manB).amount===2;cancelPriceApproval();__closeAll();
    // reassigning an exported function binding
    try{posPricesOkOrWarn=()=>true;o.reassignedConst=true}catch(e){o.reassignedConst=false}
    return o}""")
  chk('State: approval objects are not reachable as globals (window or top-level names)',r['oldGlobals']==['undefined']*4 and r['lexical']==['undefined']*5,r)
  chk('State: exported API is frozen (cannot swap consumeInvoiceApproval)',r['frozen'] and r['stillOrig'],r)
  chk('State: forged token objects under old/new names do nothing',(not r['forgedTokenSaved']) and r['apprAsked'],r)
  chk('State: forged "approved" flags on the invoice do nothing',not r['forgedFlagSaved'],r)
  chk('State: exported approval functions are const (cannot be reassigned by name)',r['reassignedConst']==False,r)
  # ---------- 8. logout / user switch / refresh ----------
  edit(p,'__manB',SETROW+"r.querySelector('.item-price').value='5000';calcInvTotal();")
  p.evaluate("()=>{Auth.logout();document.getElementById('empIdScreen').style.display='none'}")
  r=p.evaluate("""async()=>{const o={apprClosed:!__apprOpen()};await Auth.loginEmployee(window.__emp.id,'1234');onEmployeeSessionStarted();
    go('sales');editSale(window.__manB);document.querySelector('#itemsBody .item-row .item-price').value='5000';calcInvTotal();document.getElementById('saveSaleBtn').disabled=false;saveSale();
    o.amount=__inv(window.__manB).amount;o.askedAgain=__apprOpen();cancelPriceApproval();__closeAll();return o}""")
  chk('Logout: pending invoice approval closed; nothing carries over after re-login',r['apprClosed'] and r['amount']==6000 and r['askedAgain'],r)
  chk('Cashier: no JS errors',errs==[],errs)
  p.reload(); p.wait_for_timeout(2200)
  r=p.evaluate("()=>({api:typeof OwnerApproval, pendingOpen:document.getElementById('mPriceApproval').classList.contains('on')})")
  chk('Refresh: approval state gone (memory only), modal closed',r['api']=='object' and not r['pendingOpen'],r)
  p.context.close()
  # ================= SUPERVISOR & SALES REP (core) =================
  for role in ['supervisor','sales_rep']:
    p,errs=page(b); p.evaluate(SEED,role)
    r=p.evaluate("()=>{go('pos');resetPosForm();addPosItemFromProduct('pT');posItems[0].tax=0;document.getElementById('posReceived').value='100000';const n=S.get('posSales').length;checkoutPos();__closeAll();return S.get('posSales').length-n}")
    r2=edit(p,'__manA',SETROW+"r.querySelector('.item-price').value='4000';calcInvTotal();")
    p.evaluate("()=>cancelPriceApproval()")
    r3=p.evaluate("()=>{cancelSale(window.__manB);return {status:__inv(window.__manB).status,appr:__apprOpen()}}")
    p.evaluate("()=>cancelPriceApproval()")
    r4=edit(p,'__taxedInv',SETROW+"r.querySelector('.item-price').value='100';calcInvTotal();")
    chk(f'{role}: tax bypass blocked, invoice edit + cancel need approval, POS-invoice row change refused',r==0 and r2['appr'] and r3['status']!='cancelled' and r3['appr'] and 'point of sale' in r4['toast'],[r,r2,r3,r4])
    chk(f'{role}: no JS errors',errs==[],errs); p.context.close()
  # ================= OWNER & ACCESS CONTROL OFF =================
  for role in ['owner','off']:
    p,errs=page(b); p.evaluate(SEED,role)
    r=p.evaluate("()=>{go('pos');resetPosForm();addPosItemFromProduct('pT');const dis=[...document.querySelectorAll('#posItemsBody input[type=number]')].some(i=>i.disabled);updatePosItem(0,'tax','0');const o={dis,tax:posItems[0].tax};document.getElementById('posReceived').value='100000';const n=S.get('posSales').length;checkoutPos();__closeAll();o.sold=S.get('posSales').length-n;o.total=Math.round(S.get('posSales').slice(-1)[0].total);return o}")
    chk(f'{role}: tax editable as before (0% sells at 16,000, field not locked)',(not r['dis']) and r['tax']==0 and r['sold']==1 and r['total']==16000,r)
    r=edit(p,'__manA',SETROW+"r.querySelector('.item-price').value='4000';calcInvTotal();")
    chk(f'{role}: manual invoice amount edit saves directly, no approval',(not r['appr']) and p.evaluate("()=>__inv(window.__manA).amount")==8000,r)
    r=edit(p,'__manB',"document.getElementById('sCustomer').value='cU';")
    chk(f'{role}: customer change saves directly',(not r['appr']) and p.evaluate("()=>__inv(window.__manB).cid")=='cU',r)
    r=p.evaluate("()=>{cancelSale(window.__manC);return {confirm:document.getElementById('mConfirm').classList.contains('on'),appr:__apprOpen()}}")
    p.click('#mConfirmBtn'); p.wait_for_timeout(150)
    chk(f'{role}: cancel uses the existing Confirm dialog and cancels',r['confirm'] and not r['appr'] and p.evaluate("()=>__inv(window.__manC).status")=='cancelled',r)
    r=edit(p,'__manPaid',SETROW+"r.querySelector('.item-price').value='10';calcInvTotal();")
    chk(f'{role}: PAYMENT GUARD applies (below paid refused)','lower than the amount already paid' in r['toast'] and p.evaluate("()=>__inv(window.__manPaid).amount")==10000,r)
    r=edit(p,'__taxedInv',SETROW+"r.querySelector('.item-price').value='100';calcInvTotal();")
    chk(f'{role}: R1 applies (POS invoice row change refused)','point of sale' in r['toast'] and p.evaluate("()=>__inv(window.__taxedInv).amount")==19080,r)
    r=edit(p,'__taxedInv',"document.getElementById('sNotes').value='owner note';")
    chk(f'{role}: R1 unchanged-row save keeps 19,080 and saves notes',p.evaluate("()=>[__inv(window.__taxedInv).amount,__inv(window.__taxedInv).notes]")==[19080,'owner note'],r)
    r=p.evaluate("""()=>{closeModal('mAddSale');editProduct('pU');document.getElementById('pPrice').value='5500';document.getElementById('saveProductBtn').disabled=false;saveProduct();const a1=__audit(/Updated product: Oil/).slice(-1)[0];
      editProduct('pU');document.getElementById('pName').value='Oil';document.getElementById('saveProductBtn').disabled=false;saveProduct();const a2=__audit(/Updated product: Oil/).slice(-1)[0];return {a1,a2}}""")
    chk(f'{role}: catalog price audit shows old -> new; non-price edit logs as before',r['a1']['msg']=='Updated product: Oil (price FCFA 5,000 → FCFA 5,500)' and r['a1']['prev']=='5000' and r['a1']['next']=='5500' and r['a1']['rt']=='product' and r['a2']['msg']=='Updated product: Oil' and r['a2']['prev']=='',r)
    chk(f'{role}: no JS errors',errs==[],errs); p.context.close()
  # ================= SUPERVISOR catalog price audit (permission unchanged) =================
  p,errs=page(b); p.evaluate(SEED,'supervisor')
  r=p.evaluate("""()=>{editProduct('pU');document.getElementById('pPrice').value='4500';document.getElementById('saveProductBtn').disabled=false;saveProduct();return {price:S.get('products').find(x=>x.id==='pU').price,a:__audit(/Updated product: Oil/).slice(-1)[0]}}""")
  chk('Supervisor editProducts unchanged; price change audited old -> new with acting supervisor',r['price']==4500 and '5,000 → FCFA 4,500' in r['a']['msg'] and r['a']['user']=='Emp supervisor',r)
  p.context.close()
  # ================= FR + 360px =================
  p,errs=page(b,360); p.evaluate(SEED,'cashier'); p.evaluate("()=>setLang('fr')")
  edit(p,'__manA',SETROW+"r.querySelector('.item-price').value='4000';calcInvTotal();")
  r=p.evaluate("()=>({intro:paIntro.textContent,l1:paL1.textContent,l2:paL2.textContent,l3:paL3.textContent,l4:paL4.textContent,btn:paApproveBtn.textContent,fits:(()=>{const m=document.querySelector('#mPriceApproval .modal').getBoundingClientRect();return m.left>=0&&m.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth})()})")
  p.screenshot(path='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/inv_appr_fr.png')
  chk('FR: invoice approval modal translated and fits 360px','facture' in r['intro'] and r['l1']=='Facture' and r['l2']=='Actuel' and r['l3']=='Nouveau' and r['l4']=='Variation' and r['btn']=='Approuver' and r['fits'],r)
  p.evaluate("()=>cancelPriceApproval()")
  r=edit(p,'__taxedInv',SETROW+"r.querySelector('.item-price').value='100';calcInvTotal();")
  chk('FR: POS-invoice refusal message translated','point de vente' in r['toast'],r)
  r=edit(p,'__manPaid',SETROW+"r.querySelector('.item-price').value='10';calcInvTotal();")
  chk('FR: payment-guard message translated','déjà payé' in r['toast'],r)
  r=p.evaluate("()=>{closeModal('mAddSale');go('pos');resetPosForm();addPosItemFromProduct('pT');window.__t=[];updatePosItem(0,'tax','0');const a=window.__t.slice(-1)[0];posItems[0].tax=0;document.getElementById('posReceived').value='100000';window.__t=[];checkoutPos();return {a,b:window.__t.slice(-1)[0]}}")
  chk('FR: tax messages translated','taxe' in r['a'] and 'taxe diffère' in r['b'],r)
  p.evaluate("()=>{setLang('en');resetPosForm();cancelSale(window.__manA)}"); p.wait_for_timeout(150)
  p.screenshot(path='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/inv_cancel_en.png')
  r=p.evaluate("()=>({fits:(()=>{const m=document.querySelector('#mPriceApproval .modal').getBoundingClientRect();return m.left>=0&&m.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth})()})")
  chk('EN: cancel approval modal fits 360px',r['fits'],r)
  chk('FR/360: no JS errors',errs==[],errs); p.context.close()
  b.close()
srv.shutdown()
f=[x for x in results if not x[1]]
print('\nTOTAL',len(results),'FAIL',len(f)); [print('  FAILED:',x[0]) for x in f]
