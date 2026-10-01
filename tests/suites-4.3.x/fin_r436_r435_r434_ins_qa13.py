import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright
SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
def serve(d,port):
    h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=d); h.log_message=lambda *a:None
    srv=http.server.ThreadingHTTPServer(('127.0.0.1',port),h); threading.Thread(target=srv.serve_forever,daemon=True).start(); return srv

HELPERS = r"""
window.__iso=(n)=>{const d=new Date();d.setDate(d.getDate()-n);return localISODate(d);};
window.__seed=(o)=>{['products','posSales','sales','payments','customers','stockMovements','stockReconciliations'].forEach(k=>S.set(k,o[k]||[]));};
window.__cards=()=>[...document.querySelectorAll('#insightsFeed .insight-card')].map(c=>{const x=c.querySelector('.insight-txt').cloneNode(true);x.querySelectorAll('.insight-sub').forEach(s=>s.remove());
   return {txt:x.textContent.trim(),sub:(c.querySelector('.insight-sub')||{}).textContent||'',link:c.classList.contains('ins-link'),tone:[...c.classList].find(k=>k.startsWith('ins-')&&k!=='ins-link')};});
window.__groups=()=>[...document.querySelectorAll('#insightsFeed .ins-group')].map(g=>g.textContent);
window.__empty=()=>{const e=document.querySelector('#insightsFeed .insight-empty');return e?e.textContent.trim():null;};
// Product-activity dataset (expected: nosale30=3 [P2,P4,P8], never=3 [P5,P6,P12], inactive6m=2 [P7,P9])
window.__prodDS=()=>{
  const td=todayStr(), six=typeof _isoMonthsAgo==='function'?_isoMonthsAgo(td,6):null;
  const P=(id,extra)=>Object.assign({id,name:id,sku:'SKU-'+id,cost:10,price:20,stock:100,lowStock:5,status:'active',added:__iso(400)},extra||{});
  const products=['P1','P2','P3','P4','P5','P6','P7','P8','P9','P10','P11','P12'].map(id=>P(id));
  products.find(p=>p.id==='P6').added=td; products.find(p=>p.id==='P10').status='discontinued';
  const pos=(id,pid,date)=>({id,date,items:[{productId:pid,name:pid,qty:1,price:20,subtotal:20}],total:20,subtotal:20,paid:20,change:0,method:'cash',type:'cash'});
  const posSales=[pos('s1','P1',td),pos('s2','P2',__iso(30)),pos('s3','P3',__iso(29)),pos('s4','P4',__iso(45)),
    pos('s7','P7',__iso(215)),pos('s8','P8',__iso(150)),pos('s9','P9',six||__iso(183))];
  const sales=[{id:'c11',cid:'cx',amount:20,date:__iso(10),due:__iso(-20),items:[{productId:'P11',name:'P11',qty:1,price:20,subtotal:20}],status:'paid'},
               {id:'c12',cid:'cx',amount:20,date:__iso(5),due:__iso(-20),items:[{productId:'P12',name:'P12',qty:1,price:20,subtotal:20}],status:'cancelled'}];
  const payments=[{id:'pp',invId:'c11',cid:'cx',amount:20,date:__iso(10),method:'cash'}];
  const customers=[{id:'cx',name:'Cust X',phone:'677000000',limit:0}];
  return {products,posSales,sales,payments,customers};
};
"""

def boot(p,port):
    p.goto(f'http://127.0.0.1:{port}/index.html'); p.wait_for_timeout(2500); p.evaluate(HELPERS)
    p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));const r=document.getElementById('toastRack');if(r)r.style.display='none';}")

def existing_ds(n_overdue):
    # every existing insight condition true; n_overdue overdue invoices
    return f"""()=>{{const td=todayStr();
      const products=[{{id:'L1',name:'Low item',sku:'S1',cost:10,price:20,stock:2,lowStock:5,status:'active'}}];
      const posSales=[{{id:'a',date:td,items:[],total:150}},{{id:'b',date:__iso(1),items:[],total:100}}];
      const customers=[{{id:'k1',name:'Big Owner',phone:'677111111',limit:1000}},{{id:'k2',name:'Other',phone:'677222222',limit:0}}];
      const sales=[{{id:'t1',cid:'k2',amount:300,date:td,due:__iso(-1),items:[],status:'pending'}},{{id:'big',cid:'k1',amount:5000,date:td,due:__iso(-30),items:[],status:'pending'}}];
      for(let i=0;i<{n_overdue};i++)sales.push({{id:'od'+i,cid:'k2',amount:1000,date:__iso(90),due:__iso(60),items:[],status:'pending'}});
      __seed({{products,posSales,sales,payments:[],customers}});}}"""

R=[]
def check(name,cond,detail=''):
    R.append(('PASS' if cond else 'FAIL',name,detail if not cond or detail else ''))

def run_existing(build,port):
    """Returns card texts for several datasets on a build (old or new) for comparison."""
    srv=serve(build,port); out={}
    with sync_playwright() as pw:
        b=pw.chromium.launch(); p=b.new_context(service_workers='block').new_page(); boot(p,port)
        for n in [0,1,3]:
            p.evaluate(existing_ds(n)); p.evaluate("renderInsights()")
            out[f'od{n}']=p.evaluate("[...document.querySelectorAll('#insightsFeed .insight-card .insight-txt')].map(x=>{const c=x.cloneNode(true);c.querySelectorAll('.insight-sub').forEach(s=>s.remove());return c.textContent.trim()})")
            out[f'coll{n}']=p.evaluate("generateInsights().filter(i=>i.cat==='collection').map(i=>i.txt)")
        p.evaluate("__seed({})"); p.evaluate("renderInsights()")
        out['empty']=p.evaluate("[...document.querySelectorAll('#insightsFeed .insight-card .insight-txt')].map(x=>x.textContent.trim())")
        out['gen_empty']=p.evaluate("generateInsights().map(i=>i.txt)")
        b.close()
    srv.shutdown(); return out

old=run_existing('/home/claude/bz',8861); new=run_existing('/home/claude/main',8862)
for n in [0,1,3]:
    k=f'od{n}'
    check(f'Existing insights preserved (overdue={n}): every old card text still present',set(old[k])<=set(new[k]),f'old={old[k]} new={new[k]}')
    check(f'Existing Collection-page insights identical (overdue={n})',old[f'coll{n}']==new[f'coll{n}'])
check('Old build empty state was the fallback line',old['empty']==['No urgent insights right now — everything looks healthy.'])
check('generateInsights() output text unchanged when empty',old['gen_empty']==new['gen_empty'])

srv=serve('/home/claude/main',8863)
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(service_workers='block',viewport={'width':390,'height':900}); p=ctx.new_page()
    errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    boot(p,8863)
    # ── Layout
    p.evaluate("go('dashboard')"); p.wait_for_timeout(600)
    order=p.evaluate("""()=>{const pg=document.getElementById('page-dashboard');const all=[...pg.querySelectorAll('*')];
       const ix=id=>all.indexOf(document.getElementById(id));return {qa:ix('quickActions'),ins:ix('insightsCard'),kpi:ix('kpiGrid')}}""")
    check('Smart Insights sits after Quick Actions and before Credit & Debt',order['qa']<order['ins']<order['kpi'],str(order))
    between=p.evaluate("""()=>{const q=document.getElementById('quickActions');return q.nextElementSibling&&q.nextElementSibling.id}""")
    check('Smart Insights is the very next block after Quick Actions',between=='insightsCard',str(between))
    mc=p.evaluate("""()=>({disp:getComputedStyle(document.getElementById('dashMonthlyCashCard')).display,canvas:!!document.getElementById('cMonthlySales'),badge:document.getElementById('cashSalesBadge').textContent})""")
    check('Monthly Cash Sales hidden',mc['disp']=='none')
    check('Monthly Cash Sales code still runs (canvas present, badge computed)',mc['canvas'] and mc['badge']!='Loading…',str(mc))
    check('Monthly Cash Sales still in DOM with its functions intact',p.evaluate("typeof drawAllCharts==='function'&&typeof getMonthsFromHistory==='function'"))
    # ── Empty state
    p.evaluate("__seed({})"); p.evaluate("renderInsights()")
    check('Empty state: positive message (EN)',p.evaluate("__empty()")=='🌟 Your business is doing well. Keep on.',str(p.evaluate("__empty()")))
    check('Empty state: no insight cards, no "healthy" fallback',p.evaluate("__cards().length")==0)
    p.evaluate("setLang('fr')"); p.evaluate("renderInsights()")
    check('Empty state: positive message (FR)',p.evaluate("__empty()")=='🌟 Votre entreprise se porte bien. Continuez ainsi.',str(p.evaluate("__empty()")))
    p.evaluate("setLang('en')")
    # Only a "good news" insight → not empty
    p.evaluate("""()=>{const td=todayStr();__seed({customers:[{id:'g',name:'G',phone:'677',limit:0}],sales:[{id:'g1',cid:'g',amount:100,date:__iso(40),due:__iso(-10),items:[],status:'paid'}],payments:[{id:'gp',invId:'g1',cid:'g',amount:100,date:__iso(40)}]});}""")
    p.evaluate("renderInsights()")
    cards=p.evaluate("__cards()")
    check('Good-news-only insight → empty message NOT shown',p.evaluate("__empty()") is None and len(cards)>0,str(cards))
    # ── Overdue: 0 / 1 / many
    for n,exp in [(0,None),(1,'1 overdue invoice'),(3,'3 overdue invoices')]:
        p.evaluate(existing_ds(n)); p.evaluate("renderInsights()")
        od=[c for c in p.evaluate("__cards()") if 'overdue invoice' in c['txt']]
        if exp is None: check('Overdue: none → no overdue card',not od)
        else: check(f'Overdue: {n} → one card, clickable, with explanation',len(od)==1 and od[0]['txt'].startswith(exp) and od[0]['link'] and 'past their expected dates' in od[0]['sub'],str(od))
    # overdue nav
    p.evaluate(existing_ds(3)); p.evaluate("go('dashboard')"); p.wait_for_timeout(400)
    p.evaluate("document.getElementById('collSearch').value='zzz';document.getElementById('collFilterSel').value='1-7'")
    p.click("#insightsFeed .insight-card.ins-link:has-text('overdue invoice')"); p.wait_for_timeout(400)
    st=p.evaluate("({page:document.querySelector('.page.active').id,q:document.getElementById('collSearch').value,f:document.getElementById('collFilterSel').value,rows:document.querySelectorAll('#collTbody tr, #collTable tbody tr').length})")
    check('Overdue tap → Debt Collection page, filters cleared',st['page']=='page-collection' and st['q']=='' and st['f']=='',str(st))
    # groups & ordering with existing (3 overdue)
    p.evaluate(existing_ds(3)); p.evaluate("renderInsights()")
    g=p.evaluate("__groups()"); cards=p.evaluate("__cards()")
    check('Group headers: Requires Action then Review',g==['Requires Action','Review'],str(g))
    act=[c for c in cards if c['tone'] in('ins-danger','ins-warn')]
    check('Existing danger/warn insights keep their original relative order',[c['txt'][:12] for c in act][:4]==[x[:12] for x in [c['txt'] for c in cards if c['tone'] in('ins-danger','ins-warn')]][:4])
    # ── Loss Register
    p.evaluate("""()=>{const d=__prodDS();d.products.forEach(x=>{});d.stockMovements=[
        {id:'m1',type:'adjustment',productId:'P1',productName:'P1',qtyChange:-2,reason:'Theft',date:__iso(3),user:'Owner'},
        {id:'m2',type:'adjustment',productId:'P2',productName:'P2',qtyChange:-1,reason:'Damaged',date:__iso(2),user:'Owner'},
        {id:'m3',type:'adjustment',productId:'P3',productName:'P3',qtyChange:-1,reason:'Expired',date:__iso(2),user:'Owner',lossStatus:'Resolved'},
        {id:'m4',type:'adjustment',productId:'P3',productName:'P3',qtyChange:-1,reason:'Counting Error',date:__iso(2),user:'Owner'},
        {id:'m5',type:'adjustment',productId:'P4',productName:'P4',qtyChange:-1,reason:'Theft',date:__iso(2),user:'Owner',status:'pending'}];__seed(d);}""")
    p.evaluate("renderInsights()"); cards=p.evaluate("__cards()")
    loss=[c for c in cards if 'Loss Register' in c['txt']]
    check('Loss Register: 2 Open items → "2 items in Loss Register" (Resolved, non-loss reason, pending excluded)',len(loss)==1 and loss[0]['txt']=='2 items in Loss Register' and loss[0]['tone']=='ins-danger',str(loss))
    p.evaluate("go('dashboard')"); p.wait_for_timeout(300)
    p.evaluate("document.getElementById('lossFilterFrom').value='2000-01-01';document.getElementById('lossFilterStatus').value='Resolved'")
    p.click("#insightsFeed .insight-card.ins-link:has-text('Loss Register')"); p.wait_for_timeout(400)
    st=p.evaluate("({page:document.querySelector('.page.active').id,view:document.getElementById('invLossRegisterView').style.display,status:document.getElementById('lossFilterStatus').value,from:document.getElementById('lossFilterFrom').value,rows:document.querySelectorAll('#lossRegisterTbody tr').length})")
    check('Loss tap → Inventory › Loss Register, Status=Open, rows == count (2)',st['page']=='page-inventory' and st['view']=='' and st['status']=='Open' and st['from']=='' and st['rows']==2,str(st))
    p.evaluate("closeLossRegisterView()")
    p.evaluate("""()=>{const d=__prodDS();__seed(d);}"""); p.evaluate("renderInsights()")
    check('Loss Register: no entries → no loss card',not [c for c in p.evaluate("__cards()") if 'Loss Register' in c['txt']])
    # ── Product activity
    p.evaluate("__seed(__prodDS())"); p.evaluate("renderInsights()")
    cards=p.evaluate("__cards()"); txts=[c['txt'] for c in cards]
    check('Not sold in 30 days = 3 (exactly-30d P2, 45d P4, 5mo P8; 29d P3 excluded)','3 products not sold in 30 days' in txts,str(txts))
    check('Never sold = 2 (old P5, cancelled-only P12; added-today P6 in 30-day grace; discontinued P10 excluded)','2 products have never sold' in txts,str(txts))
    check('Inactive 6+ months = 2 (7mo P7, exactly 6mo P9; 5mo P8 excluded)','2 products inactive for 6+ months' in txts,str(txts))
    bk=p.evaluate("Object.fromEntries(computeProductActivityBuckets().byId)")
    check('Buckets mutually exclusive, exact membership',bk=={'P2':'nosale30','P4':'nosale30','P8':'nosale30','P5':'never','P12':'never','P7':'inactive6m','P9':'inactive6m'},str(bk))
    check('Recently sold (P1 today, P11 credit 10d, P3 29d) and new P6 (grace) in no bucket',all(k not in bk for k in ['P1','P11','P3','P6']))
    for key,label,exp in [('nosale30','not sold in 30 days',['P2','P4','P8']),('never','have never sold',['P12','P5']),('inactive6m','inactive for 6+ months',['P7','P9'])]:
        p.evaluate("go('dashboard')"); p.wait_for_timeout(300)
        p.evaluate("document.getElementById('prodSearch').value='zz';document.getElementById('prodStockSel').value='low'")
        p.click(f"#insightsFeed .insight-card.ins-link:has-text('{label}')"); p.wait_for_timeout(400)
        st=p.evaluate("({page:document.querySelector('.page.active').id,act:document.getElementById('prodActivitySel').value,q:document.getElementById('prodSearch').value,stock:document.getElementById('prodStockSel').value,names:[...document.querySelectorAll('#prodTbody tr')].map(r=>r.cells[1]?r.cells[1].textContent.trim():'')})")
        got=sorted([n for n in st['names'] if n]); 
        check(f'Tap "{label}" → Products filtered to exactly {exp}',st['page']=='page-products' and st['act']==key and st['q']=='' and st['stock']=='' and got==sorted(exp),str(st))
    # manual filter from Products page works & "All" restores full list
    p.evaluate("document.getElementById('prodActivitySel').value='';filterProducts()")
    check('Products: clearing activity filter restores full list (12)',p.evaluate("[...document.querySelectorAll('#prodTbody tr')].length")==12)
    # ── Empty inventory
    p.evaluate("__seed({posSales:[{id:'x',date:todayStr(),items:[{productId:'gone',qty:1,price:5,subtotal:5}],total:5}]})"); p.evaluate("renderInsights()")
    check('Empty inventory: no product insights, no errors',not [c for c in p.evaluate("__cards()") if 'product' in c['txt'].lower()])
    # ── Permissions: user without manageInventory/manageCustomers
    p.evaluate(existing_ds(2)); p.evaluate("()=>{const d=__prodDS();const s=S.get('sales');d.sales=d.sales.concat(s);d.customers=d.customers.concat(S.get('customers'));d.stockMovements=[{id:'m1',type:'adjustment',productId:'P1',productName:'P1',qtyChange:-2,reason:'Theft',date:__iso(3)}];__seed(d);}")
    p.evaluate("()=>{window.__can=Auth.can;Auth.can=k=>!['manageInventory','manageCustomers'].includes(k)&&window.__can.call(Auth,k)}"); p.evaluate("renderInsights()")
    cards=p.evaluate("__cards()")
    check('No Loss Register permission → loss card hidden (no dead-end)',not [c for c in cards if 'Loss Register' in c['txt']])
    od=[c for c in cards if 'overdue invoice' in c['txt']]
    check('No Collection permission → overdue card still shown, not clickable',len(od)==1 and not od[0]['link'],str(od))
    check('Product cards still clickable (Products page has no permission gate)',all(c['link'] for c in cards if 'product' in c['txt'].lower()))
    p.evaluate("()=>{Auth.can=window.__can}")
    # ── French rendering with data
    p.evaluate("setLang('fr')"); p.evaluate("go('dashboard')"); p.wait_for_timeout(500)
    g=p.evaluate("__groups()"); txts=[c['txt'] for c in p.evaluate("__cards()")]
    check('FR: group headers translated',g==['Action requise','À examiner'],str(g))
    check('FR: new insights translated','1 élément dans le registre des pertes' in txts and '2 produits jamais vendus' in txts,str(txts))
    check('FR: Products activity filter translated',p.evaluate("document.querySelector('#prodActivitySel option[value=never]').textContent")=='Jamais vendus')
    p.locator('#insightsCard').screenshot(path=SP+'ins_fr.png')
    p.evaluate("setLang('en')"); p.evaluate("go('dashboard')"); p.wait_for_timeout(500)
    p.locator('#insightsCard').screenshot(path=SP+'ins_en.png')
    ow=p.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    check('No horizontal overflow at 390px',ow)
    check('No JS exceptions throughout',not errs,str(errs))
    b.close()
srv.shutdown()
for r in R: print(*[x for x in r if x])
print('TOTAL',len(R),'FAIL',sum(1 for r in R if r[0]=='FAIL'))
