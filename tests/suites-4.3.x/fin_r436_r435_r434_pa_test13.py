import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory='/home/claude/main'); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8851),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
results=[];
def chk(name,cond,info=''):
    results.append((name,bool(cond),info)); print(('PASS' if cond else 'FAIL'),'|',name,'|',info if not cond or info else '')
def page(b,vw=390):
    p=b.new_context(service_workers='block',viewport={'width':vw,'height':860}).new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://127.0.0.1:8851/index.html'); p.wait_for_timeout(2200)
    p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}"); return p,errs
SEED="""async(mode)=>{
  window.__t=[];const ot=window.toast;window.toast=(m,ty)=>{window.__t.push(m);};
  S.add('products',{id:'pT',sku:'S1',name:'Rice Bag',category:'G',cost:13500,price:16000,stock:100,lowStock:5,tax:0,added:todayStr()});
  S.add('products',{id:'pU',sku:'S2',name:'Oil',category:'G',cost:4200,price:5500,stock:100,lowStock:5,tax:0,added:todayStr()});
  S.add('customers',{id:'cT',name:'Test Cust',phone:'+237670000001',limit:10000,status:'active',added:todayStr()});
  window.__ok=async()=>{};
  if(mode!=='off'){
    // real owner password so verifyPassword() is exercised for real
    const salt=genSalt();setAccessControl({...getAccessControl(),enabled:true,ownerPasswordSalt:salt,ownerPasswordHash:await hashPassword('ownerpass9',salt),pendingSetup:false});
  }
  if(mode==='cashier'||mode==='supervisor'){const c=await createEmployee({fullName:'Cash Ier',username:'cash',password:'1234',role:mode});await Auth.loginEmployee(c.employee.id,'1234');window.__emp=c.employee.id;}
  onEmployeeSessionStarted();go('pos');
  window.__close=()=>document.querySelectorAll('.modal-bg.on').forEach(m=>{if(m.id!=='mPriceApproval')m.classList.remove('on')});
  window.__last=()=>S.get('posSales').slice(-1)[0];
  window.__modalOn=()=>document.getElementById('mPriceApproval').classList.contains('on');
  window.__newCart=(ids)=>{resetPosForm();(ids||['pT']).forEach(i=>addPosItemFromProduct(i));};
  window.__pay=(v)=>{document.getElementById('posReceived').value=v};
  window.__audit=()=>S.get('auditLog').filter(a=>/price adjustment/i.test(a.msg)).map(a=>({type:a.type,user:a.user,role:a.role,msg:a.msg,rt:a.recordType,prev:a.prevValue,next:a.newValue}));
  return true}"""
with sync_playwright() as pw:
  b=pw.chromium.launch()
  # ===== OWNER (access control ON, owner session) =====
  p,errs=page(b); p.evaluate(SEED,'owner')
  r=p.evaluate("""()=>{__newCart();updatePosItem(0,'sellingPrice','10000');const o={modal:__modalOn(),disc:posItems[0].discount,grand:Math.round(calcPosTotalsRaw().grand)};__pay('100000');checkoutPos();__close();const s=__last();o.saved=Math.round(s.total);o.itemMeta=s.items[0].priceApprovedBy||null;
    __newCart();updatePosItem(0,'discount','10');o.pctModal=__modalOn();o.pct=posItems[0].discount;
    __newCart();updatePosItem(0,'sellingPrice','20000');o.markModal=__modalOn();o.markDisc=posItems[0].discount;o.audit=__audit().length;return o}""")
  chk('Owner: selling-price change applies with NO prompt',not r['modal'] and abs(r['disc']-37.5)<1e-9 and r['grand']==10000,r)
  chk('Owner: sale saves at adjusted price, no approval metadata',r['saved']==10000 and r['itemMeta'] is None,r)
  chk('Owner: discount % and markup also prompt-free; nothing added to audit',not r['pctModal'] and r['pct']==10 and not r['markModal'] and r['markDisc']==-25 and r['audit']==0,r)
  chk('Owner: no JS errors',errs==[],errs); p.context.close()
  # ===== ACCESS CONTROL OFF =====
  p,errs=page(b); p.evaluate(SEED,'off')
  r=p.evaluate("""()=>{__newCart();updatePosItem(0,'sellingPrice','10000');const o={modal:__modalOn(),disc:posItems[0].discount,req:priceApprovalRequired()};posItems[0].discount=50;__pay('100000');checkoutPos();__close();o.saved=Math.round(__last().total);return o}""")
  chk('Access Control OFF: no approval required, direct edits sell as before',(not r['modal']) and r['req']==False and r['saved']==8000,r)
  chk('Access Control OFF: no JS errors',errs==[],errs); p.context.close()
  # ===== CASHIER =====
  p,errs=page(b); p.evaluate(SEED,'cashier')
  r=p.evaluate("""()=>{const o={req:priceApprovalRequired(),isOwner:Auth.isOwner()};
    __newCart();updatePosItem(0,'sellingPrice','10000');
    o.modalOpens=__modalOn();o.discStillZero=posItems[0].discount;o.fieldReverted=document.querySelector('#posItemsBody input.num-fmt:nth-of-type(1)')!==null;
    o.shownProduct=document.getElementById('paProduct').textContent;o.shownRegular=document.getElementById('paRegular').textContent;o.shownNew=document.getElementById('paProposed').textContent;o.shownChange=document.getElementById('paChange').textContent;
    return o}""")
  chk('Cashier: changing price opens Owner Approval modal and does NOT apply the price',r['req'] and r['modalOpens'] and r['discStillZero']==0,r)
  chk('Cashier: modal shows product, regular, new price and change',r['shownProduct']=='Rice Bag' and '16,000' in r['shownRegular'] and '10,000' in r['shownNew'] and 'Discount' in r['shownChange'] and '37.5' in r['shownChange'],r)
  # wrong password
  p.fill('#paPassword','wrong'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  r=p.evaluate("()=>({modal:__modalOn(),disc:posItems[0].discount,err:document.getElementById('paError').textContent,audit:__audit()})")
  chk('Cashier: WRONG password -> price not applied, modal stays, error shown',r['modal'] and r['disc']==0 and 'Incorrect' in r['err'],r)
  chk('Cashier: failed attempt audited (login_failed, attributed to the cashier)',len(r['audit'])==1 and r['audit'][0]['type']=='login_failed' and r['audit'][0]['user']=='Cash Ier' and r['audit'][0]['role']=='Cashier',r['audit'])
  p.fill('#paPassword',''); p.click('#paApproveBtn'); p.wait_for_timeout(200)
  chk('Cashier: empty password rejected without a verification',p.evaluate("()=>document.getElementById('paError').textContent")!='' and p.evaluate("()=>posItems[0].discount")==0)
  # cancel
  p.click('#mPriceApproval .modal-ftr .btn-outline'); p.wait_for_timeout(150)
  r=p.evaluate("()=>({modal:__modalOn(),disc:posItems[0].discount,pending:(typeof _pendingPriceApproval)})")
  chk('Cashier: CANCEL -> price unchanged, modal closed, nothing pending',(not r['modal']) and r['disc']==0 and r['pending']=='undefined',r)
  # checkout attempt with nothing approved (catalog price) still works
  r=p.evaluate("()=>{__pay('100000');checkoutPos();__close();const s=__last();return {total:Math.round(s.total),meta:s.items[0].priceApprovedBy||null}}")
  chk('Cashier: sale at the catalog price completes with no approval needed',r['total']==16000 and r['meta'] is None,r)
  # correct password
  p.evaluate("()=>{__newCart();updatePosItem(0,'sellingPrice','10000')}")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(500)
  r=p.evaluate("()=>({modal:__modalOn(),disc:posItems[0].discount,grand:Math.round(calcPosTotalsRaw().grand),audit:__audit(),sess:Auth.current()&&Auth.current().fullName,isOwner:Auth.isOwner()})")
  chk('Cashier: CORRECT Owner password -> price applied to that line',(not r['modal']) and abs(r['disc']-37.5)<1e-9 and r['grand']==10000,r)
  chk('Cashier: session NOT switched to Owner by approving',r['sess']=='Cash Ier' and not r['isOwner'],r)
  a=[x for x in r['audit'] if x['type']=='edit']
  chk('Audit: approval recorded (type edit, acting employee = cashier, prev/new price, recordType)',len(a)==1 and a[0]['user']=='Cash Ier' and a[0]['role']=='Cashier' and a[0]['rt']=='priceAdjustment' and a[0]['prev']=='16000' and a[0]['next']=='10000' and 'approved by' in a[0]['msg'],a)
  # quantity change after approval keeps approval
  r=p.evaluate("""()=>{const d0=posItems[0].discount;updatePosItem(0,'qty','3');const o={modal:__modalOn(),sameDisc:posItems[0].discount===d0,grand:Math.round(calcPosTotalsRaw().grand)};__pay('100000');checkoutPos();__close();const s=__last();o.saved=Math.round(s.total);o.meta=s.items[0].priceApprovedBy;o.at=!!s.items[0].priceApprovedAt;o.sp=Math.round(s.items[0].sellingPrice);return o}""")
  chk('Quantity change after approval: NO new prompt, unit price stays approved, sale completes',(not r['modal']) and r['sameDisc'] and r['grand']==30000 and r['saved']==30000 and r['sp']==10000,r)
  chk('Saved sale line carries nullable approval metadata (approver name + time)',r['meta']=='Business Owner' and r['at'],r)
  # changing to a different price needs approval again
  r=p.evaluate("""()=>{__newCart();updatePosItem(0,'sellingPrice','10000');return 1}""")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  r=p.evaluate("()=>{updatePosItem(0,'sellingPrice','9000');const o={modal:__modalOn(),disc:posItems[0].discount};return o}")
  chk('A DIFFERENT price on an approved line needs a new approval (not applied meanwhile)',r['modal'] and abs(r['disc']-37.5)<1e-9,r)
  p.click('#mPriceApproval .modal-ftr .btn-outline'); p.wait_for_timeout(100)
  r=p.evaluate("()=>{updatePosItem(0,'sellingPrice','16000');return {modal:__modalOn(),disc:posItems[0].discount}}")
  chk('Returning a line to the catalog price needs no approval',(not r['modal']) and abs(r['disc'])<1e-9,r)
  # percent mode
  r=p.evaluate("()=>{__newCart();setPosDiscountMode('percentage');updatePosItem(0,'discount','5');return {modal:__modalOn(),disc:posItems[0].discount}}")
  chk('Discount (percentage mode): small 5% change also prompts, not applied',r['modal'] and r['disc']==0,r)
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  chk('Discount 5% applies after approval',p.evaluate("()=>posItems[0].discount")==5)
  # markup
  r=p.evaluate("()=>{__newCart();setPosDiscountMode('sellingPrice');updatePosItem(0,'sellingPrice','20000');return {modal:__modalOn(),disc:posItems[0].discount,chg:document.getElementById('paChange').textContent}}")
  chk('MARKUP above catalog price prompts too, not applied; modal labels it Markup',r['modal'] and r['disc']==0 and 'Markup' in r['chg'] and '+25' in r['chg'],r)
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  r=p.evaluate("()=>{__pay('100000');checkoutPos();__close();const s=__last();return {disc:posItems.length,total:Math.round(s.total),d:s.items[0].discount}}")
  chk('Markup approved -> sale saves at the marked-up price',r['total']==20000 and r['d']==-25,r)
  # ===== BYPASS ATTEMPTS =====
  r=p.evaluate("""()=>{const o={};const n0=S.get('posSales').length;window.__t=[];
    __newCart();posItems[0].discount=99;__pay('100000');checkoutPos();__close();o.directDiscount={sold:S.get('posSales').length-n0,msg:window.__t.slice(-1)[0]};
    const n1=S.get('posSales').length;__newCart();posItems[0].price=100;__pay('100000');checkoutPos();__close();o.directPrice={sold:S.get('posSales').length-n1};
    const n2=S.get('posSales').length;__newCart();updatePosItem(0,'price','50');__pay('100000');checkoutPos();__close();o.updatePosItemPrice={sold:S.get('posSales').length-n2};
    const n3=S.get('posSales').length;__newCart();posItems=[{productId:'pT',name:'Rice Bag',sku:'S1',unit:'',category:'G',notes:'',maxStock:100,qty:1,price:16000,cost:13500,discount:80,tax:0}];__pay('100000');checkoutPos();__close();o.replacedObject={sold:S.get('posSales').length-n3};
    const n4=S.get('posSales').length;__newCart();posItems[0].discount=NaN;__pay('100000');checkoutPos();__close();o.nan={sold:S.get('posSales').length-n4};
    const n5=S.get('posSales').length;__newCart();posItems[0].discount=60;__pay('100000');const b=document.getElementById('posCheckoutBtn');b.disabled=false;
      // calling the save functions directly, skipping checkoutPos entirely
      finalizeCashSale('', todayStr(), 6400, 100000, '');o.directFinalizeCash={sold:S.get('posSales').length-n5};
    const s0=S.get('sales').length;__newCart();posItems[0].discount=60;document.getElementById('posTypeCredit').checked=true;setPosType('credit');finalizeCreditSale('cT',todayStr(),6400,0,todayStr(),'');o.directFinalizeCredit={sold:S.get('sales').length-s0};
    o.checkoutButtonEnabled=!document.getElementById('posCheckoutBtn').disabled;return o}""")
  chk('Bypass: setting posItems[0].discount directly is BLOCKED at checkout',r['directDiscount']['sold']==0 and 'not approved' in (r['directDiscount']['msg'] or ''),r['directDiscount'])
  chk('Bypass: lowering posItems[0].price directly is BLOCKED (catalog price check)',r['directPrice']['sold']==0,r['directPrice'])
  chk('Bypass: updatePosItem(idx,"price") direct call is BLOCKED at checkout',r['updatePosItemPrice']['sold']==0,r['updatePosItemPrice'])
  chk('Bypass: replacing posItems with forged line objects is BLOCKED',r['replacedObject']['sold']==0,r['replacedObject'])
  chk('Bypass: NaN discount is BLOCKED',r['nan']['sold']==0,r['nan'])
  chk('Bypass: calling finalizeCashSale() directly is BLOCKED',r['directFinalizeCash']['sold']==0,r['directFinalizeCash'])
  chk('Bypass: calling finalizeCreditSale() directly is BLOCKED',r['directFinalizeCredit']['sold']==0,r['directFinalizeCredit'])
  chk('Blocked attempts never leave Complete Sale stuck disabled',r['checkoutButtonEnabled'],r)
  # forged grant can't be created from outside (closure-private)
  r=p.evaluate("""()=>{const o={};o.globalsLeak=[typeof window._priceGrants,typeof window.priceGrants];
    try{o.grantsVisible=typeof _priceGrants!=='undefined'}catch(e){o.grantsVisible='err'}
    const n=S.get('posSales').length;__newCart();posItems[0].discount=70;posItems[0].approved=true;posItems[0].priceApprovedBy='Owner';posItems[0].priceApprovedAt=new Date().toISOString();__pay('100000');checkoutPos();__close();o.fakeFlags={sold:S.get('posSales').length-n};return o}""")
  chk('Bypass: adding fake "approved" flags to a line does nothing',r['fakeFlags']['sold']==0,r)
  # line removed / re-added
  r=p.evaluate("""()=>{__newCart();updatePosItem(0,'sellingPrice','10000');return 1}""")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  r=p.evaluate("""()=>{const o={};o.approved=posItems[0].discount;removePosItem(0);addPosItemFromProduct('pT');o.afterReAdd=posItems[0].discount;
    const n=S.get('posSales').length;posItems[0].discount=37.5;__pay('100000');checkoutPos();__close();o.soldWithCopiedDiscount=S.get('posSales').length-n;return o}""")
  chk('Line REMOVED then re-added: approval gone, re-typing the same discount is blocked',abs(r['approved']-37.5)<1e-9 and r['afterReAdd']==0 and r['soldWithCopiedDiscount']==0,r)
  # cart reset
  p.evaluate("""()=>{__newCart();updatePosItem(0,'sellingPrice','10000');}""")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  r=p.evaluate("""()=>{const it=posItems[0];const d=it.discount;clearPosForm();posItems=[it];posItems[0].discount=d;const n=S.get('posSales').length;__pay('100000');checkoutPos();__close();return {sold:S.get('posSales').length-n}}""")
  chk('Cart RESET invalidates approvals (same line object smuggled back in is blocked)',r['sold']==0,r)
  # cancel while pending via reset
  r=p.evaluate("""()=>{__newCart();updatePosItem(0,'sellingPrice','10000');const o={open:__modalOn()};clearPosForm();o.closedByReset=!__modalOn();o.pending=(typeof _pendingPriceApproval);return o}""")
  chk('Cart reset closes a pending approval modal',r['open'] and r['closedByReset'] and r['pending']=='undefined',r)
  # stale price when product catalog price changes after add
  r=p.evaluate("""()=>{__newCart();const p0=S.get('products').find(x=>x.id==='pT');S.update('products',{...p0,price:17000});const n=S.get('posSales').length;window.__t=[];__pay('100000');checkoutPos();__close();const o={sold:S.get('posSales').length-n,msg:window.__t.slice(-1)[0]};S.update('products',p0);return o}""")
  chk('Edge: catalog price changed mid-cart -> cashier told to re-add item (no silent stale price)',r['sold']==0 and 'not approved' in (r['msg'] or ''),r)
  # credit-limit (4.3.6 flow): approved price, credit limit exceeded -> Owner credit-override pop-up; tamper before approving
  p.evaluate("""()=>{__newCart();updatePosItem(0,'sellingPrice','12000');}""")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  r=p.evaluate("""()=>{const o={};window.__s0=S.get('sales').length;
    document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value='cT';document.getElementById('posDeposit').value='0';document.getElementById('posDueDate').value=todayStr();
    document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();
    o.creditApprovalShown=__modalOn()&&/limit/i.test(document.getElementById('paIntro').textContent);o.soldBeforeApproval=S.get('sales').length-window.__s0;
    posItems[0].discount=90; // tamper with the price-approved line while the credit pop-up is open
    return o}""")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r2=p.evaluate("()=>({sold:S.get('sales').length-window.__s0,buttonFree:!document.getElementById('posCheckoutBtn').disabled})")
  chk('Credit-limit (4.3.6): tampering after price approval, before credit approval, is caught at save time',r['creditApprovalShown'] and r['soldBeforeApproval']==0 and r2['sold']==0 and r2['buttonFree'],{**r,**r2})
  r=p.evaluate("""()=>{__close();document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));__newCart();updatePosItem(0,'sellingPrice','12000');return __modalOn()}""")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  p.evaluate("""()=>{window.__s0=S.get('sales').length;document.getElementById('posTypeCredit').checked=true;setPosType('credit');document.getElementById('posCustomer').value='cT';document.getElementById('posDeposit').value='0';document.getElementById('posDueDate').value=todayStr();
    document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();}""")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(450)
  r=p.evaluate("""()=>{__close();const s=S.get('sales').slice(-1)[0];return {sold:S.get('sales').length-window.__s0,amount:s&&s.amount,meta:s&&s.items[0].priceApprovedBy}}""")
  chk('Credit-limit (4.3.6): Owner credit approval with untouched approved price completes at approved price with approval metadata',r['sold']==1 and r['amount']==12000 and r['meta']=='Business Owner',r)
  # logout / switch user
  p.evaluate("""()=>{__newCart();updatePosItem(0,'sellingPrice','10000');}""")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  r=p.evaluate("""()=>{const it=posItems[0];const d=it.discount;Auth.logout();const o={modalClosed:!__modalOn()};
    // a different cashier logs in and inherits the cart
    return o}""")
  p.evaluate("()=>{document.getElementById('empIdScreen').style.display='none'}")
  r2=p.evaluate("""async()=>{const c=await createEmployee({fullName:'Second Cashier',username:'cash2',password:'1234',role:'cashier'});await Auth.loginEmployee(c.employee.id,'1234');onEmployeeSessionStarted();go('pos');
    const o={cartSurvives:posItems.length};if(!posItems.length){addPosItemFromProduct('pT');posItems[0].discount=37.5}
    const n=S.get('posSales').length;__pay('100000');document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();__close();o.soldWithInheritedApproval=S.get('posSales').length-n;return o}""")
  chk('Logout/switch user: approval does not carry over to the next employee',r2['soldWithInheritedApproval']==0,r2)
  chk('Cashier session: no JS errors across all tests',errs==[],errs)
  p.context.close()
  # ===== SUPERVISOR: no exemption =====
  p,errs=page(b); p.evaluate(SEED,'supervisor')
  r=p.evaluate("()=>{__newCart();updatePosItem(0,'sellingPrice','10000');return {req:priceApprovalRequired(),modal:__modalOn(),disc:posItems[0].discount}}")
  chk('Supervisor (non-owner): also requires Owner approval (no exempt role)',r['req'] and r['modal'] and r['disc']==0,r); p.context.close()
  # ===== REFRESH =====
  p,errs=page(b); p.evaluate(SEED,'cashier')
  p.evaluate("()=>{__newCart();updatePosItem(0,'sellingPrice','10000')}")
  p.fill('#paPassword','ownerpass9'); p.click('#paApproveBtn'); p.wait_for_timeout(400)
  before=p.evaluate("()=>posItems[0].discount")
  p.reload(); p.wait_for_timeout(2500)
  r=p.evaluate("()=>({cart:typeof posItems!=='undefined'?posItems.length:-1,grants:typeof _priceGrants})")
  chk('REFRESH: cart and approvals are gone (memory only, nothing persisted)',abs(before-37.5)<1e-9 and r['cart']==0,r)
  stored=p.evaluate("""async()=>{const ks=[];for(let i=0;i<localStorage.length;i++)ks.push(localStorage.key(i));return JSON.stringify(ks).toLowerCase().includes('approv')||JSON.stringify(S.get('posSales')).includes('priceApproved')}""")
  chk('Nothing approval-related is persisted to storage by the approval itself',stored==False)
  p.context.close()
  # ===== FR =====
  p,errs=page(b); p.evaluate(SEED,'cashier'); p.evaluate("()=>setLang('fr')")
  p.evaluate("()=>{__newCart();updatePosItem(0,'sellingPrice','10000')}")
  txt=p.evaluate("()=>({title:document.querySelector('#mPriceApproval .modal-title').textContent,intro:document.querySelector('#paIntro').textContent,reg:document.querySelector('#paL2').textContent,chg:document.getElementById('paChange').textContent,btn:document.getElementById('paApproveBtn').textContent,cancel:document.querySelector('#mPriceApproval .modal-ftr .btn-outline').textContent})")
  chk('FR: modal fully translated',('Approbation' in txt['title']) and 'propriétaire' in txt['intro'] and 'Prix normal' in txt['reg'] and 'Remise' in txt['chg'] and txt['btn']=='Approuver' and txt['cancel']=='Annuler',txt)
  p.fill('#paPassword','nope'); p.click('#paApproveBtn'); p.wait_for_timeout(300)
  fe=p.evaluate("()=>document.getElementById('paError').textContent")
  chk('FR: wrong-password message translated',fe.startswith('Mot de passe'),fe)
  p.evaluate("()=>{clearPosForm();__newCart();posItems[0].discount=50;window.__t=[];__pay('100000');checkoutPos();}")
  msg=p.evaluate("()=>window.__t.slice(-1)[0]")
  chk('FR: blocked-checkout message translated and names the product',msg and 'Rice Bag' in msg and 'approuvée' in msg,msg)
  p.evaluate("()=>setLang('en')")
  chk('FR/EN tests: no JS errors',errs==[],errs); p.context.close()
  b.close()
srv.shutdown()
f=[r for r in results if not r[1]]
print('\nTOTAL',len(results),'FAIL',len(f))
