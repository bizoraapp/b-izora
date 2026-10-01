import threading, http.server, functools, json
from playwright.sync_api import sync_playwright
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory='/home/claude/main'); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8853),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
def page(b):
  p=b.new_context(service_workers='block',viewport={'width':390,'height':800}).new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
  p.goto('http://127.0.0.1:8853/index.html'); p.wait_for_timeout(2200)
  p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}"); return p,errs
with sync_playwright() as pw:
  b=pw.chromium.launch()
  # 1. cashier workflows
  p,errs=page(b)
  print('WORKFLOWS',json.dumps(p.evaluate("""async()=>{
    const toasts=[];const ot=toast;window.toast=(m,t)=>{toasts.push(m);};
    S.add('products',{id:'pT',sku:'SKU-T',name:'Test Item',category:'X',cost:500,price:1000,stock:50,lowStock:5,unit:'pcs',tax:0,added:todayStr()});
    S.add('customers',{id:'cT',name:'Test Cust',phone:'+237670000001',limit:0,status:'active',added:todayStr()});
    setAccessControl({...getAccessControl(),enabled:true,ownerPasswordHash:'x',ownerPasswordSalt:'y'});
    const c=await createEmployee({fullName:'Cash',username:'cash',password:'1234',role:'cashier'});
    await Auth.loginEmployee(c.employee.id,'1234');onEmployeeSessionStarted();
    const R={};const n=k=>S.get(k).length;
    // cash sale
    go('pos');R.onPos=document.querySelector('.page.active').id;
    const ps0=n('posSales');resetPosForm();addPosItemFromProduct('pT');addPosItemFromProduct('pT');
    document.getElementById('posReceived').value='2000';checkoutPos();
    R.cashSale=n('posSales')-ps0; const last=S.get('posSales').slice(-1)[0]; R.cashTotal=last&&last.total;
    document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
    // credit sale
    const s0=n('sales');resetPosForm();document.getElementById('posTypeCredit').checked=true;setPosType('credit');
    document.getElementById('posCustomer').value='cT';addPosItemFromProduct('pT');
    document.getElementById('posDeposit').value='0';document.getElementById('posDueDate').value=todayStr();
    document.getElementById('posCheckoutBtn').disabled=false;checkoutPos();
    R.creditSale=n('sales')-s0; const inv=S.get('sales').slice(-1)[0]; R.invBalance=inv&&invBalance(inv.id);
    document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
    // repayment
    go('payments');R.onPay=document.querySelector('.page.active').id;
    openModal('mAddPay');resetPayForm();
    const pc=document.getElementById('pCustomer');pc.value='cT';pc.dispatchEvent(new Event('change'));
    await new Promise(r=>setTimeout(r,100));
    const pi=document.getElementById('pInvoice');if(![...pi.options||[]].some(o=>o.value===inv.id)){R.invOptMissing=true}
    pi.value=inv.id;pi.dispatchEvent(new Event('change'));document.getElementById('pAmount').value='400';
    const p0=n('payments');savePay();R.repayment=n('payments')-p0;R.balAfter=invBalance(inv.id);R.custDebt=custDebt('cT');
    R.stockLeft=S.get('products').find(x=>x.id==='pT').stock;
    R.toasts=toasts.slice(-8);window.toast=ot;return R}"""),indent=0),'errs',errs)
  p.context.close()
  # 2. owner on Backup -> cashier logs in -> must land on dashboard
  p,errs=page(b)
  print('SESSION SWITCH',p.evaluate("""async()=>{
    setAccessControl({...getAccessControl(),enabled:true,ownerPasswordHash:'x',ownerPasswordSalt:'y'});
    go('backup');const before=document.querySelector('.page.active').id;
    const c=await createEmployee({fullName:'Cash',username:'cash',password:'1234',role:'cashier'});
    await Auth.loginEmployee(c.employee.id,'1234');onEmployeeSessionStarted();
    const afterBackup=document.querySelector('.page.active').id;
    Auth._current=null;onEmployeeSessionStarted();go('help');
    await Auth.loginEmployee(c.employee.id,'1234');onEmployeeSessionStarted();
    return {before,afterBackup,afterHelp:document.querySelector('.page.active').id}}"""),'errs',errs)
  p.context.close()
  # 3. custom permissions: owner grants viewHelp to cashier via editor; legacy custom record without viewHelp
  p,errs=page(b)
  print('CUSTOM PERMS',p.evaluate("""async()=>{
    const R={};
    // legacy custom record saved by 4.3.0 (no viewHelp key)
    S.setObj('rolePermissions',{cashier:{...DEFAULT_ROLE_PERMISSIONS.cashier,viewHelp:undefined},supervisor:{recordSales:true,manageCustomers:true,viewReports:true,manageInventory:true,addProducts:true,editProducts:true,viewFinancials:true,exportReports:true,accessSettings:false,manageExpenses:true,approveAdjustments:false}});
    const cr=S.obj('rolePermissions');delete cr.cashier.viewHelp;S.setObj('rolePermissions',cr);
    R.legacyCashierHelp=!!getRolePermissions('cashier').viewHelp; R.legacySupervisorHelp=!!getRolePermissions('supervisor').viewHelp;
    // editor shows the toggle, owner turns it on for cashier
    openRolePermissions();document.getElementById('rpRoleSelect').value='cashier';renderRolePermissionsForm();
    R.toggleRendered=!!document.getElementById('rp_viewHelp'); R.toggleInitiallyChecked=document.getElementById('rp_viewHelp').checked;
    document.getElementById('rp_viewHelp').checked=true;saveRolePermissionsForm();closeModal('mRolePermissions');
    setAccessControl({...getAccessControl(),enabled:true,ownerPasswordHash:'x',ownerPasswordSalt:'y'});
    const c=await createEmployee({fullName:'Cash',username:'cash',password:'1234',role:'cashier'});
    await Auth.loginEmployee(c.employee.id,'1234');onEmployeeSessionStarted();
    R.helpNavVisibleAfterGrant=!document.getElementById('nav-help').classList.contains('role-hidden');
    go('help');R.helpOpens=document.querySelector('.page.active').id;
    R.otherPermsUnchanged=JSON.stringify(Object.fromEntries(Object.entries(getRolePermissions('cashier')).filter(([k])=>k!=='viewHelp')))===JSON.stringify(Object.fromEntries(Object.entries(DEFAULT_ROLE_PERMISSIONS.cashier).filter(([k])=>k!=='viewHelp')));
    return R}"""),'errs',errs)
  p.context.close()
  # 4. storekeeper dashboard quick actions + FR toast text
  p,errs=page(b)
  print('STOREKEEPER/FR',p.evaluate("""async()=>{
    const toasts=[];const ot=toast;window.toast=(m,t)=>{toasts.push(m);};
    setAccessControl({...getAccessControl(),enabled:true,ownerPasswordHash:'x',ownerPasswordSalt:'y'});
    const c=await createEmployee({fullName:'SK',username:'sk',password:'1234',role:'storekeeper'});
    await Auth.loginEmployee(c.employee.id,'1234');onEmployeeSessionStarted();
    quickNewSale('cash');quickSearchInvoice();await new Promise(r=>setTimeout(r,200));
    const page1=document.querySelector('.page.active').id;
    setLang('fr');go('financial');exportCSV('ledger');sendOwnerEndOfDayWhatsAppSummary();exportBackup();setLang('en');
    window.toast=ot;return {page1,toasts}}"""),'errs',errs)
  p.context.close(); b.close()
srv.shutdown()
