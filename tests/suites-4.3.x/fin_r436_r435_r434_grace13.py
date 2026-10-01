import threading, http.server, functools, json
from playwright.sync_api import sync_playwright
SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
HELPERS=open(SP+'ins_qa.py').read().split('HELPERS = r"""')[1].split('"""')[0]
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory='/home/claude/main'); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8895),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
SEED=r"""()=>{
 const P=(id,added)=>{const p={id,name:id,sku:'S-'+id,cost:10,price:20,stock:100,lowStock:5,status:'active'};if(added!==undefined)p.added=added;return p;};
 const products=[P('G1',todayStr()),P('G2',__iso(29)),P('G3',__iso(30)),P('G4',__iso(90)),
   P('G5',__iso(29)),P('G6',__iso(60)),P('G6b',__iso(400)),P('G7'),P('G8',__iso(-10)),P('G10','abc')];
 // CSV import: exact record shape produced by the import path (line 16766)
 products.push({...P('G9'),notes:'Imported via CSV',added:todayStr()});
 products.push({...P('G9b'),notes:'Imported via CSV',added:__iso(45)});
 const pos=(id,pid,date)=>({id,date,items:[{productId:pid,name:pid,qty:1,price:20,subtotal:20}],total:20});
 __seed({products,posSales:[pos('a','G5',todayStr()),pos('b','G6',__iso(40)),pos('c','G6b',__iso(200))]});
}"""
exp={'G1':None,'G2':None,'G3':'never','G4':'never','G5':None,'G6':'nosale30','G6b':'inactive6m','G7':'never','G8':None,'G9':None,'G9b':'never','G10':'never'}
labels={'G1':'1. added today + never sold','G2':'2. added 29d ago + never sold','G3':'3. added exactly 30d ago + never sold','G4':'4. added 90d ago + never sold',
 'G5':'5. added 29d ago + sold (today)','G6':'6a. added 60d ago + sold 40d ago','G6b':'6b. added 400d ago + sold 200d ago','G7':'7. missing "added"','G8':'8. future "added" (+10d)',
 'G9':'9a. CSV import today','G9b':'9b. CSV import 45d ago','G10':'extra: malformed "added"'}
R=[]
with sync_playwright() as pw:
  b=pw.chromium.launch(); p=b.new_context(service_workers='block').new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
  p.goto('http://127.0.0.1:8895/index.html'); p.wait_for_timeout(2500); p.evaluate(HELPERS)
  p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}")
  p.evaluate(SEED)
  got=p.evaluate("Object.fromEntries(computeProductActivityBuckets().byId)")
  for k,v in exp.items():
    g=got.get(k); R.append(('PASS' if g==v else 'FAIL',labels[k],f'expected {v or "no bucket"}, got {g or "no bucket"}'))
  # 10. non-overlap + count == filtered list, per bucket
  counts=p.evaluate("computeProductActivityBuckets().counts")
  R.append(('PASS' if sum(counts.values())==len(got) else 'FAIL','10. buckets non-overlapping (each product in ≤1 bucket)',str(counts)))
  p.evaluate("renderInsights()"); txt=p.evaluate("document.getElementById('insightsFeed').innerText")
  for key,phrase in [('never','have never sold'),('nosale30','not sold in 30 days'),('inactive6m','inactive for 6+ months')]:
    p.evaluate(f"openInsight('{key}')")
    listed=sorted(p.evaluate("[...document.querySelectorAll('#prodTbody tr')].map(r=>r.cells[1]&&r.cells[1].textContent.replace('Imported via CSV','').trim()).filter(Boolean)"))
    want=sorted(k for k,v in exp.items() if v==key)
    shown=[l for l in txt.split('\n') if phrase in l]
    n=int(shown[0].split()[0]) if shown else 0
    R.append(('PASS' if listed==want and n==len(want) else 'FAIL',f'10. "{key}" insight count == filtered list',f'card={n} list={listed}'))
  R.append(('PASS' if not errs else 'FAIL','no JS errors',str(errs)))
  b.close()
srv.shutdown()
for r in R: print(*r,sep=' | ')
print('TOTAL',len(R),'FAIL',sum(r[0]=='FAIL' for r in R))
