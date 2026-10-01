import threading,http.server,functools,json,statistics
from playwright.sync_api import sync_playwright
GEN="""(n)=>{const T=todayStr();const P='2025-06-01';const ps=[],sa=[],py=[],ex=[],cl=[],cu=[];
 for(let i=0;i<Math.max(50,n/10);i++)cu.push({id:'c'+i,name:'Cust '+i,phone:'+2376'+String(i).padStart(8,'0'),limit:0,status:'active',added:P});
 const d=i=>i%1000===0?T:P;
 for(let i=0;i<n/2;i++)ps.push({id:'ps'+i,receiptNum:'R'+i,date:d(i),cid:null,items:[{productId:'sm',name:'Soap',qty:1,price:2000,subtotal:2000}],subtotal:2000,total:2000,paid:2500,change:500,method:i%3?'cash':'mobile-money',type:'cash'});
 for(let i=0;i<n/4;i++)sa.push({id:'s'+i,cid:'c'+(i%cu.length),amount:5000,date:d(i),due:P,items:[{name:'x',qty:1,price:5000,subtotal:5000}],status:'partial',docNum:'INV-'+i});
 for(let i=0;i<n/4;i++)py.push({id:'y'+i,invId:'s'+i,cid:'c'+(i%cu.length),amount:2000,date:d(i),method:i%2?'cash':'mobile-money'});
 for(let i=0;i<n/20;i++)ex.push({id:'e'+i,category:'transport',amount:1000,date:d(i),notes:'',payMethod:'cash'});
 for(let i=0;i<n/50;i++)cl.push({id:'cl'+i,cid:'c'+(i%cu.length),type:i%2?'earned':'refunded',amount:100,date:d(i),note:'',relatedInvId:null,method:'cash'});
 MEM.customers=cu;MEM.posSales=ps;MEM.sales=sa;MEM.payments=py;MEM.expenses=ex;MEM.creditLedger=cl;invalidateFinanceIndices();
 S.add('products',{id:'sm',sku:'SKU-1',name:'Soap',category:'X',cost:300,price:2000,stock:1e9,unit:'pcs',tax:0,status:'active',added:P});
 window.toast=()=>{};return true}"""
MEAS="""()=>{const med=a=>a.sort((x,y)=>x-y)[Math.floor(a.length/2)];
 const rd=[];for(let i=0;i<7;i++){const t=performance.now();renderCashDrawer();rd.push(performance.now()-t);}
 const sale=[];for(let i=0;i<5;i++){document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));resetPosForm();addPosItemFromProduct('sm');document.getElementById('posTypeCash').checked=true;setPosType('cash');document.getElementById('posMethod').value='cash';document.getElementById('posReceived').value='2000';calcPosTotals();document.getElementById('posCheckoutBtn').disabled=false;const t=performance.now();checkoutPos();sale.push(performance.now()-t);}
 const pay=[];for(let i=0;i<5;i++){document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));openModal('mAddPay');resetPayForm();const c=document.getElementById('pCustomer');const inv=S.get('sales')[100+i];if(![...c.options].some(o=>o.value===inv.cid))c.add(new Option(inv.cid,inv.cid));c.value=inv.cid;const s=document.getElementById('pInvoice');if(![...s.options].some(o=>o.value===inv.id))s.add(new Option(inv.id,inv.id));s.value=inv.id;document.getElementById('pAmount').value='100';const t=performance.now();savePay();pay.push(performance.now()-t);}
 return {drawer:+med(rd).toFixed(1),sale:+med(sale).toFixed(1),pay:+med(pay).toFixed(1),expected:document.getElementById('cdExpected').textContent}}"""
res={}
for tag,d,port in [('4.3.7','/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/v437',8833),('4.3.8','/home/claude/main',8834)]:
  h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=d);h.log_message=lambda *a:None
  srv=http.server.ThreadingHTTPServer(('127.0.0.1',port),h);threading.Thread(target=srv.serve_forever,daemon=True).start()
  with sync_playwright() as pw:
    b=pw.chromium.launch()
    for n in [1000,10000,50000,100000]:
      ctx=b.new_context(service_workers='block',viewport={'width':390,'height':800});p=ctx.new_page()
      p.goto(f'http://127.0.0.1:{port}/index.html');p.wait_for_timeout(2200)
      cdp=ctx.new_cdp_session(p);cdp.send('Emulation.setCPUThrottlingRate',{'rate':4})
      p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
      p.evaluate(GEN,n);p.evaluate("()=>go('inventory')")
      res[(tag,n)]=p.evaluate(MEAS);ctx.close()
    b.close()
  srv.shutdown()
print('N        | drawer render ms 4.3.7 -> 4.3.8 | record cash sale ms | record payment ms')
for n in [1000,10000,50000,100000]:
  a,b_=res[('4.3.7',n)],res[('4.3.8',n)]
  print(f"{n:>7} | {a['drawer']:>6} -> {b_['drawer']:<6} | {a['sale']:>6} -> {b_['sale']:<6} | {a['pay']:>6} -> {b_['pay']:<6} | exp {a['expected']} vs {b_['expected']}")
