"""Bizora 4.3.8 — payment-method integrity suite (real UI clicks + direct-call security). Usage: python3 t438.py [dir]"""
import sys,json
BASE=open('/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/t437.py').read().split("with sync_playwright() as pw:")[0].replace("8811","8820")
exec(BASE)
SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
HELP="""()=>{
 window.__snap=()=>({sales:S.get('sales').length,pays:S.get('payments').length,soap:S.get('products').find(p=>p.id==='sm').stock,exp:__dc().expected,aud:S.get('auditLog').length,cl:S.get('creditLedger').length});
 window.__newAud=n=>S.get('auditLog').slice(n).map(a=>({type:a.type,user:a.user,msg:a.msg}));
 window.__posPrep=(cid,qty)=>{__closeAll();go('pos');resetPosForm();for(let i=0;i<qty;i++)addPosItemFromProduct('sm');document.getElementById('posTypeCredit').checked=true;setPosType('credit');
   const c=document.getElementById('posCustomer');c.value=cid;c.dispatchEvent(new Event('change',{bubbles:true}));document.getElementById('posDueDate').value=todayStr();calcPosTotals();};
 window.__depUI=()=>({wrapShown:document.getElementById('posDepositMethodWrap').style.display!=='none',val:document.getElementById('posDepositMethod').value,opts:[...document.getElementById('posDepositMethod').options].map(o=>o.value)});
 return true}"""
LABEL={'cash':'Cash','mobile-money':'Mobile Money','bank-transfer':'Bank Transfer','card':'Card','other':'Other','cheque':'Cheque'}
def pos_credit(p,cid,qty,deposit,method=None):
    p.evaluate(f"()=>__posPrep('{cid}',{qty})")
    p.fill('#posDeposit',str(deposit)); p.wait_for_timeout(80)
    if method: p.select_option('#posDepositMethod',method)
    b=p.evaluate("()=>{window.__t=[];return __snap()}")
    p.evaluate("()=>{document.getElementById('posCheckoutBtn').disabled=false}")
    p.click('#posCheckoutBtn'); p.wait_for_timeout(350)
    a=p.evaluate("()=>__snap()")
    inv=p.evaluate("()=>{const s=S.get('sales').slice(-1)[0];const pay=S.get('payments').filter(x=>x.invId===s.id);return {id:s.id,amount:s.amount,bal:invBalance(s.id),pays:pay.map(x=>({amount:x.amount,method:x.method,notes:x.notes})),receipt:document.getElementById('mReceipt').classList.contains('on')?document.getElementById('receiptPreview').innerText:'',pdf:(_lastReceiptCtx?_buildReceiptPdfLines(_lastReceiptCtx.sale,_lastReceiptCtx.type).map(l=>l.l?l.l+' '+l.r:'').join('|'):''),wa:(_lastReceiptCtx?_buildReceiptShareText(_lastReceiptCtx.sale,_lastReceiptCtx.type):''),toast:__t.slice(-1)[0]||''}}")
    aud=p.evaluate(f"()=>__newAud({b['aud']})")
    return b,a,inv,aud

with sync_playwright() as pw:
  bro=pw.chromium.launch()
  # =============== 1 + CRITICAL ACCEPTANCE A–D: POS credit deposit, every method (real UI) ===============
  p,errs=page(bro,'owner',390); p.evaluate(HELP)
  st=p.evaluate("()=>{__posPrep('cA',3);return __depUI()}")
  chk('POS: deposit selector hidden while deposit is 0',not st['wrapShown'],st)
  p.fill('#posDeposit','3000'); st=p.evaluate("()=>__depUI()")
  chk('POS: selector appears when a deposit is typed, with NO default and exactly Cash/MoMo/Bank/Card/Other (no Cheque)',st['wrapShown'] and st['val']=='' and st['opts']==['','cash','mobile-money','bank-transfer','card','other'],st)
  for scen,m,dexp in [('A','mobile-money',0),('B','cash',3000),('C','bank-transfer',0),('D','card',0),('E','other',0)]:
      b,a,inv,aud=pos_credit(p,'cA',3,3000,m)
      tag=f'ACCEPTANCE {scen} ({LABEL[m]} deposit)' if scen in 'ABCD' else f'POS deposit ({LABEL[m]})'
      chk(f'{tag}: invoice 6,000, one payment 3,000 with method "{m}", balance 3,000',inv['amount']==6000 and len(inv['pays'])==1 and inv['pays'][0]['amount']==3000 and inv['pays'][0]['method']==m and inv['bal']==3000 and a['sales']-b['sales']==1 and a['pays']-b['pays']==1,{'inv':inv,'b':b,'a':a})
      chk(f'{tag}: Expected Cash +{dexp:,}',a['exp']-b['exp']==dexp,{'before':b['exp'],'after':a['exp']})
      chk(f'{tag}: stock reduced by exactly 3',b['soap']-a['soap']==3,{'b':b['soap'],'a':a['soap']})
      dl=[x for x in aud if x['msg'].startswith('Deposit ')]
      chk(f'{tag}: audit "Deposit FCFA 3,000 ({LABEL[m]}) from Amina on INV-…" by the acting user',len(dl)==1 and f'Deposit FCFA 3,000 ({LABEL[m]}) from Amina on INV-' in dl[0]['msg'] and dl[0]['type']=='payment' and dl[0]['user']=='Business Owner',aud)
      chk(f'{tag}: receipt, PDF and WhatsApp text show the deposit method',f'Deposit paid with' in inv['receipt'] and LABEL[m] in inv['receipt'].split('Deposit paid with')[1][:40] and f'Deposit paid with {LABEL[m]}' in inv['pdf'] and f'Deposit paid with: {LABEL[m]}' in inv['wa'],{'receipt':inv['receipt'][-300:],'pdf':inv['pdf'][-200:]})
  st=p.evaluate("()=>{__closeAll();go('pos');return __depUI()}")
  chk('Stale state: after a completed sale the selector is cleared and hidden',st['val']=='' and not st['wrapShown'],st)
  # =============== 2. zero-deposit credit sale ===============
  b,a,inv,aud=pos_credit(p,'cA',2,0)
  chk('Zero deposit: sale saved, no payment, no method asked, Expected Cash +0, receipt shows no deposit method',a['sales']-b['sales']==1 and a['pays']==b['pays'] and a['exp']==b['exp'] and 'Deposit paid with' not in inv['receipt'] and 'Deposit paid with' not in inv['pdf'],{'inv':inv,'b':b,'a':a})
  # =============== 3. deposit without a method is refused (UI) ===============
  b,a,inv,aud=pos_credit(p,'cA',3,3000,None)
  chk('POS: deposit with no method chosen → refused, nothing saved (no sale, payment, stock)',a==b,{'b':b,'a':a,'toast':p.evaluate("()=>__t")})
  chk('POS: refusal message asks for the deposit method',any('deposit was paid' in x for x in p.evaluate("()=>__t")),p.evaluate("()=>__t"))
  # =============== 5. stale-state protection ===============
  p.evaluate("()=>__posPrep('cA',3)"); p.fill('#posDeposit','3000'); p.select_option('#posDepositMethod','mobile-money')
  p.evaluate("()=>clearPosForm()"); st=p.evaluate("()=>__depUI()")
  chk('Stale: clearing the sale clears the chosen method',st['val']=='' and not st['wrapShown'],st)
  p.evaluate("()=>__posPrep('cA',3)"); p.fill('#posDeposit','3000'); p.select_option('#posDepositMethod','mobile-money'); p.fill('#posDeposit','0'); p.fill('#posDeposit','2000')
  st=p.evaluate("()=>__depUI()")
  chk('Stale: deposit → 0 → new deposit requires choosing again',st['wrapShown'] and st['val']=='',st)
  p.select_option('#posDepositMethod','card'); p.select_option('#posCustomer','cB'); st=p.evaluate("()=>__depUI()")
  chk('Stale: changing the customer clears the method',st['val']=='',st)
  p.evaluate("()=>__posPrep('cA',3)"); p.fill('#posDeposit','3000'); p.select_option('#posDepositMethod','cash'); p.fill('#posDeposit','0')
  b=p.evaluate("()=>__snap()")
  r=p.evaluate("()=>{document.getElementById('posDeposit').value='3000';calcPosTotals();document.getElementById('posDepositMethod').value='cash';const n=S.get('payments').length;window.__t=[];finalizeCreditSale('cA',todayStr(),calcPosTotalsRaw().grand,3000,todayStr(),'');__closeAll();return {d:S.get('payments').length-n,hidden:document.getElementById('posDepositMethodWrap').style.display==='none'}}")
  a=p.evaluate("()=>__snap()")
  chk('Security: a hidden selector (deposit set without the UI) is not trusted → refused, nothing written',r['hidden'] and a['sales']==b['sales'] and a['pays']==b['pays'] and a['soap']==b['soap'],{'r':r,'b':b,'a':a})
  # =============== 4. invalid direct calls ===============
  for lbl,arg in [('missing (no argument, selector unset)',None),('empty string',"''"),('the string "undefined"',"'undefined'"),('"cash2"',"'cash2'"),('"bitcoin"',"'bitcoin'"),('"Cash" (wrong case)',"'Cash'"),('"cheque" (not allowed for deposits)',"'cheque'"),('arbitrary long string',"'x'.repeat(500)"),('malformed object',"{toString(){return 'cash'}}"),('array',"['cash']"),('null',"null"),('number',"1")]:
      p.evaluate("()=>{__posPrep('cA',3);document.getElementById('posDeposit').value='3000';calcPosTotals();syncDepositMethod('pos');}")
      b=p.evaluate("()=>__snap()")
      call=f"finalizeCreditSale('cA',todayStr(),calcPosTotalsRaw().grand,3000,todayStr(),''{','+arg if arg else ''})"
      p.evaluate(f"()=>{{window.__t=[];{call};__closeAll();}}")
      a=p.evaluate("()=>__snap()"); au=p.evaluate(f"()=>__newAud({b['aud']})")
      chk(f'Direct call finalizeCreditSale with deposit method {lbl}: refused, no sale/payment/stock/credit change, audited',a['sales']==b['sales'] and a['pays']==b['pays'] and a['soap']==b['soap'] and a['cl']==b['cl'] and any('deposit payment method' in x['msg'] for x in au),{'b':b,'a':a,'aud':au})
  p.evaluate("()=>{__posPrep('cA',3);}")
  b=p.evaluate("()=>__snap()"); p.evaluate("()=>{finalizeCreditSale('cA',todayStr(),calcPosTotalsRaw().grand,3000,todayStr(),'','card');__closeAll();}"); a=p.evaluate("()=>__snap()")
  chk('Direct call with a valid explicit method ("card") saves exactly one payment with that method',a['pays']-b['pays']==1 and p.evaluate("S.get('payments').slice(-1)[0].method")=='card' and a['exp']==b['exp'],{'b':b,'a':a})
  chk('POS section: no JS errors',errs==[],errs); p.context.close()

  # =============== 6. credit-limit approval unchanged (cashier) ===============
  p,errs=page(bro,'cashier',390); p.evaluate(HELP)
  p.evaluate("()=>S.update('customers',{...S.get('customers').find(c=>c.id==='cA'),limit:4000})")
  p.evaluate("()=>__posPrep('cA',3)"); p.fill('#posDeposit','1000')
  b=p.evaluate("()=>__snap()"); p.evaluate("()=>{window.__t=[];document.getElementById('posCheckoutBtn').disabled=false}"); p.click('#posCheckoutBtn'); p.wait_for_timeout(300)
  st=p.evaluate("()=>({appr:document.getElementById('mPriceApproval').classList.contains('on'),req:__newAud(%d).filter(a=>/Owner approval required/.test(a.msg)).length,t:__t})"%b['aud'])
  chk('Cashier over-limit sale with deposit but no method: asked for the method first, NO approval requested',not st['appr'] and st['req']==0 and any('deposit was paid' in x for x in st['t']),st)
  p.select_option('#posDepositMethod','mobile-money'); p.evaluate("()=>{document.getElementById('posCheckoutBtn').disabled=false}"); p.click('#posCheckoutBtn'); p.wait_for_timeout(300)
  st=p.evaluate("()=>({appr:document.getElementById('mPriceApproval').classList.contains('on'),n:__snap()})")
  chk('Cashier: with a method chosen, the 4.3.6 Owner approval is requested; nothing saved yet',st['appr'] and st['n']['sales']==b['sales'],st)
  approve(p)
  r=p.evaluate("()=>{const s=S.get('sales').slice(-1)[0];return {n:__snap(),pay:S.get('payments').filter(x=>x.invId===s.id).map(x=>x.method),aud:__newAud(%d).map(a=>a.user+': '+a.msg)}}"%b['aud'])
  chk('Cashier: after Owner approval the sale saves with the MoMo deposit; override + deposit audited as the cashier',r['n']['sales']-b['sales']==1 and r['pay']==['mobile-money'] and any('Credit-limit override approved by Business Owner' in x for x in r['aud']) and any(x.startswith('Emp cashier: Deposit FCFA 1,000 (Mobile Money)') for x in r['aud']),r)
  p.evaluate("()=>{__closeAll();__posPrep('cA',1)}"); p.fill('#posDeposit','500'); p.select_option('#posDepositMethod','cash'); p.evaluate("()=>{document.getElementById('posCheckoutBtn').disabled=false}"); p.click('#posCheckoutBtn'); p.wait_for_timeout(300)
  chk('Cashier: approval is still single-use (next over-limit sale asks again)',p.evaluate("document.getElementById('mPriceApproval').classList.contains('on')"),'')
  p.evaluate("()=>cancelPriceApproval()")
  chk('Cashier section: no JS errors',errs==[],errs); p.context.close()

  # =============== 7. invoice-form deposit (real UI) ===============
  p,errs=page(bro,'owner',390); p.evaluate(HELP)
  def inv_form(dep,method=None,ret=True):
      p.evaluate("()=>{__closeAll();openModal('mAddSale');resetSaleForm();const _sc=document.getElementById('sCustomer');if(![..._sc.options].some(o=>o.value==='cB'))_sc.add(new Option('Bello','cB'));_sc.value='cB';document.getElementById('itemsBody').innerHTML='';addItemRow('Service',1,6000);calcInvTotal();}")
      p.fill('#sInitPay',str(dep)); p.wait_for_timeout(60)
      if method: p.select_option('#sDepositMethod',method)
      b=p.evaluate("()=>{window.__t=[];return __snap()}"); p.evaluate("()=>{document.getElementById('saveSaleBtn').disabled=false;saveSale()}"); p.wait_for_timeout(200)
      a=p.evaluate("()=>__snap()"); au=p.evaluate(f"()=>__newAud({b['aud']})")
      last=p.evaluate("()=>{const s=S.get('sales').slice(-1)[0];return {amount:s.amount,date:s.date,pays:S.get('payments').filter(x=>x.invId===s.id).map(x=>({m:x.method,a:x.amount,d:x.date}))}}")
      return b,a,au,last
  st=p.evaluate("()=>{openModal('mAddSale');resetSaleForm();return {shown:document.getElementById('sDepositMethodWrap').style.display!=='none'}}")
  chk('Invoice form: deposit-method selector hidden while deposit is 0',not st['shown'],st)
  for m in ['cash','mobile-money','bank-transfer','card','other']:
      b,a,au,last=inv_form(2500,m)
      chk(f'Invoice deposit ({LABEL[m]}): one payment 2,500 stored as "{m}", Expected Cash +{2500 if m=="cash" else 0:,}',a['sales']-b['sales']==1 and last['pays']==[{'m':m,'a':2500,'d':last['date']}] and a['exp']-b['exp']==(2500 if m=='cash' else 0),{'last':last,'b':b,'a':a})
      chk(f'Invoice deposit ({LABEL[m]}): audit "Deposit FCFA 2,500 ({LABEL[m]}) from Bello on INV-…"',any(x['msg'].startswith(f'Deposit FCFA 2,500 ({LABEL[m]}) from Bello on INV-') for x in au),au)
  b,a,au,last=inv_form(2500,None)
  chk('Invoice deposit with no method: refused, no invoice, no payment',a==b and any('deposit was paid' in x for x in p.evaluate("()=>__t")),{'b':b,'a':a})
  b,a,au,last=inv_form(0,None)
  chk('Invoice with no deposit: saved normally, no payment, no method asked',a['sales']-b['sales']==1 and a['pays']==b['pays'],{'b':b,'a':a})
  p.evaluate("()=>{__closeAll();openModal('mAddSale');resetSaleForm();const _sc=document.getElementById('sCustomer');if(![..._sc.options].some(o=>o.value==='cB'))_sc.add(new Option('Bello','cB'));_sc.value='cB';document.getElementById('itemsBody').innerHTML='';addItemRow('Service',1,6000);calcInvTotal();document.getElementById('sInitPay').value='2500';document.getElementById('sDepositMethod').value='cash';}")
  b=p.evaluate("()=>__snap()"); p.evaluate("()=>{document.getElementById('saveSaleBtn').disabled=false;saveSale()}"); a=p.evaluate("()=>__snap()")
  chk('Invoice deposit: hidden selector (deposit set without the UI) is not trusted → refused',a==b,{'b':b,'a':a})
  p.evaluate("()=>{__closeAll();openModal('mAddSale');resetSaleForm();}"); p.fill('#sInitPay','1000'); p.select_option('#sDepositMethod','card')
  p.evaluate("()=>{__closeAll();openModal('mAddSale');resetSaleForm();}")
  st=p.evaluate("()=>({v:document.getElementById('sDepositMethod').value,shown:document.getElementById('sDepositMethodWrap').style.display!=='none'})")
  chk('Invoice form stale state: reopening a new invoice clears the method',st['v']=='' and not st['shown'],st)

  # =============== 8. Record Payment: every method + invalid ===============
  p.evaluate("()=>S.add('sales',{id:'invR',cid:'cB',amount:900000,date:'2026-01-05',due:'2026-01-05',items:[{name:'x',qty:1,price:900000,subtotal:900000}],status:'pending',docNum:'INV-R'})")
  for m in ['cash','mobile-money','bank-transfer','card','cheque','other']:
      b=p.evaluate("()=>__snap()"); r=p.evaluate(f"()=>__pay('cB','invR',1000,'{m}')"); a=p.evaluate("()=>__snap()")
      last=p.evaluate("()=>S.get('payments').slice(-1)[0].method"); au=p.evaluate(f"()=>__newAud({b['aud']})")
      chk(f'Record Payment ({LABEL[m]}): stored "{m}", Expected Cash +{1000 if m=="cash" else 0:,}, audit shows method + invoice',r['dPays']==1 and last==m and a['exp']-b['exp']==(1000 if m=='cash' else 0) and any(x['msg']==f'Payment FCFA 1,000 ({LABEL[m]}) from Bello on '+p.evaluate("invNum('invR')") for x in au),{'r':r,'last':last,'aud':au})
  for lbl,val in [('"bitcoin" (injected option)','bitcoin'),('"Cash" (wrong case)','Cash'),('empty',''),('"account credit" (not choosable)','account credit')]:
      b=p.evaluate("()=>__snap()")
      r=p.evaluate(f"""()=>{{__closeAll();openModal('mAddPay');resetPayForm();const c=document.getElementById('pCustomer');if(![...c.options].some(o=>o.value==='cB'))c.add(new Option('cB','cB'));c.value='cB';const i=document.getElementById('pInvoice');if(![...i.options].some(o=>o.value==='invR'))i.add(new Option('invR','invR'));i.value='invR';document.getElementById('pAmount').value='1000';const m=document.getElementById('pMethod');if(![...m.options].some(o=>o.value==={json.dumps(val)}))m.add(new Option('x',{json.dumps(val)}));m.value={json.dumps(val)};window.__t=[];savePay();return {{t:__t.slice(-1)[0]||''}}}}""")
      a=p.evaluate("()=>__snap()"); au=p.evaluate(f"()=>__newAud({b['aud']})")
      chk(f'Record Payment with invalid method {lbl}: refused, no payment, no credit, audited',a['pays']==b['pays'] and a['cl']==b['cl'] and any('invalid payment method' in x['msg'] for x in au),{'r':r,'aud':au})
  # overpayment retains method (4.3.7 behaviour)
  b=p.evaluate("()=>__snap()"); p.evaluate("()=>__pay('cA','invPaid',4000,'mobile-money')"); okConfirm(p); a=p.evaluate("()=>__snap()")
  r=p.evaluate("()=>({cl:S.get('creditLedger').slice(-1)[0]})")
  chk('Overpayment (MoMo): excess credit keeps method "mobile-money", Expected Cash +0',a['cl']-b['cl']==1 and r['cl']['method']=='mobile-money' and a['exp']==b['exp'],{'r':r,'b':b,'a':a})
  r=p.evaluate("()=>({ok:refundAccountCredit('cA',1000,'cash2'),c:Math.round(custCreditBalance('cA'))})")
  chk('Refund with "cash2" refused by the canonical list (credit unchanged)',r['ok']==False and r['c']==4000,r)
  b=p.evaluate("()=>__snap()"); p.evaluate("()=>refundAccountCredit('cA',1000,'cash')"); a=p.evaluate("()=>__snap()")
  chk('Cash refund still subtracts from Expected Cash (4.3.7 behaviour)',b['exp']-a['exp']==1000,{'b':b,'a':a})
  # =============== account credit ===============
  p.evaluate("()=>S.add('sales',{id:'invAC',cid:'cA',amount:2000,date:'2026-01-05',due:'2026-01-05',items:[{name:'x',qty:1,price:2000,subtotal:2000}],status:'pending',docNum:'INV-AC'})")
  b=p.evaluate("()=>__snap()"); p.evaluate("()=>{promptApplyCredit('cA');document.getElementById('mConfirmBtn').click();}"); a=p.evaluate("()=>__snap()")
  r=p.evaluate("()=>{const x=S.get('payments').slice(-1)[0];__closeAll();go('payments');document.getElementById('payMethodSel').value='account credit';filterPayments();const rows=[...document.querySelectorAll('#page-payments tbody tr')].map(tr=>tr.innerText);return {m:x.method,opts:[...document.getElementById('payMethodSel').options].map(o=>o.value),rows}}")
  chk('Account credit: stored "account credit", Expected Cash +0',r['m']=='account credit' and a['exp']==b['exp'],{'r':r,'b':b,'a':a})
  chk('Payment filter has Other and Account Credit; filtering by Account Credit shows it labelled "Account Credit"',r['opts'][-2:]==['other','account credit'] and len(r['rows'])>=1 and all('Account Credit' in x for x in r['rows']),r)
  chk('Deposit / payment section: no JS errors',errs==[],errs); p.context.close()

  # =============== 8b. historical unknown / missing methods ===============
  p,errs=page(bro,'owner',1200); p.evaluate(HELP)
  p.evaluate("""()=>{const T=todayStr();const mk=(id,m)=>{const r={id,invId:'invB2',cid:'cB',amount:100,date:T,ref:'',notes:'hist'};if(m!=='__none__')r.method=m;S.add('payments',r)};
   mk('H_none','__none__');mk('H_empty','');mk('H_momo','mobile money');mk('H_bank','bank');mk('H_Cash','Cash');mk('H_btc','bitcoin');
   S.add('posSales',{id:'H_pos',receiptNum:'REC-HPOS',date:T,cid:null,items:[{name:'x',qty:1,price:700,subtotal:700}],subtotal:700,total:700,paid:700,change:0,type:'cash'});
   S.add('expenses',{id:'H_exp',category:'rent',amount:300,date:T,notes:''});S.add('creditLedger',{id:'H_cl',cid:'cB',type:'earned',amount:50,date:T,note:'old',relatedInvId:null,method:'weird'});}""")
  before=p.evaluate("()=>JSON.stringify([S.get('payments').filter(x=>x.id.startsWith('H_')),S.get('posSales').filter(x=>x.id.startsWith('H_')),S.get('expenses').filter(x=>x.id.startsWith('H_')),S.get('creditLedger').filter(x=>x.id.startsWith('H_'))])")
  r=p.evaluate("""()=>{__closeAll();go('payments');document.getElementById('payMethodSel').value='';filterPayments();
    const row=id=>{const tr=[...document.querySelectorAll('#page-payments tbody tr')].find(t=>t.innerText.includes(recNum(id)));return tr?tr.cells[4].innerText.trim():'(none)'};
    const rec=id=>{const m=buildPaymentReceiptDocument(id).match(/Payment Method<\\/span><span>([^<]*)</);return m?m[1]:'?'};
    const ids=['H_none','H_empty','H_momo','H_bank','H_Cash','H_btc'];
    const d=computeDrawerCash(todayStr(),0);renderCashDrawer();
    return {list:Object.fromEntries(ids.map(i=>[i,row(i)])),receipt:Object.fromEntries(ids.map(i=>[i,rec(i)])),dc:{cash:d.cashCollections,sales:d.cashSales,exp:d.cashExpenses,cin:d.cashCreditIn,unrec:d.unrecorded},note:document.getElementById('cdNote').textContent,
      hist:''}}""")
  after=p.evaluate("()=>JSON.stringify([S.get('payments').filter(x=>x.id.startsWith('H_')),S.get('posSales').filter(x=>x.id.startsWith('H_')),S.get('expenses').filter(x=>x.id.startsWith('H_')),S.get('creditLedger').filter(x=>x.id.startsWith('H_'))])")
  exp={'H_none':'Not recorded','H_empty':'Not recorded','H_momo':'Not recorded (mobile money)','H_bank':'Not recorded (bank)','H_Cash':'Not recorded (Cash)','H_btc':'Not recorded (bitcoin)'}
  chk('History: payments list shows "Not recorded" (never Cash) for missing/unknown methods',all(exp[k] in r['list'][k] and r['list'][k].strip() not in ('Cash','cash') for k in exp),r['list'])
  chk('History: payment receipt shows "Not recorded" (never Cash)',all(r['receipt'][k]==exp[k] for k in exp),r['receipt'])
  chk('History: none of them counted as physical cash (incl. posSale without method, expense without method, ledger "weird")',r['dc']['cash']==0 and r['dc']['sales']==0 and r['dc']['exp']==0 and r['dc']['cin']==0,r['dc'])
  chk('History: drawer note reports all 9 excluded records',r['dc']['unrec']==9 and '9 record(s)' in r['note'] and 'missing or not recognised' in r['note'],{'dc':r['dc'],'note':r['note']})
  chk('History: no historical record rewritten',before==after,'')
  sh=p.evaluate("""()=>{__closeAll();go('saleshistory');loadSalesHistory();const tr=[...document.querySelectorAll('#shTbody tr')].find(t=>t.innerText.includes('REC-HPOS'));return tr?tr.innerText:'(row not found)'}""")
  chk('History: Sales History shows the method-less POS sale as "Not recorded", not Cash','Not recorded' in sh and '\tCash' not in sh,sh)
  sr=p.evaluate("""()=>{document.getElementById('gSearchInput').value='100';runGlobalSearch();return document.getElementById('gSearchResults').innerText}""")
  chk('History: global search shows "Not recorded" and never "cash" for missing methods',sr.count('Not recorded')>=6 and ' · cash' not in sr,sr[:600])
  chk('History section: no JS errors',errs==[],errs)
  # =============== FR + 360px ===============
  p.set_viewport_size({'width':360,'height':800})
  r=p.evaluate("()=>{setLang('fr');__posPrep('cA',3);return 1}"); p.fill('#posDeposit','3000'); p.wait_for_timeout(200)
  fr=p.evaluate("()=>({lbl:document.querySelector('#posDepositMethodWrap label').textContent,opt:document.getElementById('posDepositMethod').options[2].textContent,nr:t('pm_not_recorded'),sw:document.documentElement.scrollWidth})")
  chk('FR: deposit selector translated',fr['lbl'].startswith('Acompte payé par') and 'Mobile Money' in fr['opt'] and fr['nr']=='Non enregistré',fr)
  chk('360px: POS credit panel with deposit selector has no horizontal overflow',fr['sw']<=360,fr)
  p.locator('#posDepositMethodWrap').scroll_into_view_if_needed(); p.screenshot(path=SP+'s438_pos_fr_360.png')
  p.evaluate("()=>{setLang('en');__closeAll();openModal('mAddSale');resetSaleForm();}"); p.fill('#sInitPay','1000'); p.wait_for_timeout(700)
  sw=p.evaluate("()=>({sw:document.documentElement.scrollWidth,mw:document.querySelector('#mAddSale .modal').scrollWidth,cw:document.querySelector('#mAddSale .modal').clientWidth})")
  chk('360px: invoice form with deposit selector has no horizontal overflow',sw['sw']<=360 and sw['mw']<=sw['cw']+1,sw)
  p.locator('#sDepositMethodWrap').scroll_into_view_if_needed(); p.screenshot(path=SP+'s438_invoice_en_360.png')
  chk('FR/360 section: no JS errors',errs==[],errs); p.context.close()
  bro.close()
srv.shutdown()
print('\nTOTAL',len(results),'PASS',sum(1 for _,c in results if c),'FAIL',sum(1 for _,c in results if not c))
