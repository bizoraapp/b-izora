"""Real backup export -> restore into a FRESH browser profile via the real handleFile() path.
Usage: python3 restore438.py <dir> <port>"""
import threading,http.server,functools,json,sys
from playwright.sync_api import sync_playwright
DIR=sys.argv[1]; PORT=int(sys.argv[2]); SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=DIR);h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),h);threading.Thread(target=srv.serve_forever,daemon=True).start()
res=[]
def chk(n,c,i=''): res.append((n,bool(c)));print(('PASS' if c else 'FAIL'),'|',n,'' if c else '| '+json.dumps(i,ensure_ascii=False,default=str)[:600])
SEED=open(SP+'seed438.js').read()
DIGEST="""()=>{const strip=a=>a.map(r=>{const{updated_at,...x}=r;return x}).sort((a,b)=>String(a.id).localeCompare(String(b.id)));
  const o={};for(const k of ['customers','sales','payments','products','posSales','creditLedger','expenses','stockMovements','employees'])o[k]=JSON.stringify(strip(S.get(k)||[]));
  o.cashDrawer=JSON.stringify(S.obj('cashDrawer',{}));o.payMethods=S.get('payments').map(p=>p.id+':'+(p.method===undefined?'(none)':p.method)).sort();
  o.clMethods=S.get('creditLedger').map(e=>e.id+':'+e.method).sort();o.expMethods=S.get('expenses').map(e=>e.id+':'+e.payMethod).sort();
  o.counts=Object.fromEntries(['customers','sales','payments','products','posSales','creditLedger','expenses'].map(k=>[k,S.get(k).length]));
  o.debts=Object.fromEntries(S.get('customers').map(c=>[c.name,custDebt(c.id)]));o.credit=Object.fromEntries(S.get('customers').map(c=>[c.name,Math.round(custCreditBalance(c.id))]));return o}"""
RESTORE="""async(txt)=>{const T=[];const ot=window.toast;window.toast=(m,ty)=>{T.push((ty||'')+':'+String(m));};const errs=[];const oe=window.onerror;
  handleFile(new File([txt],'bizora-backup.json',{type:'application/json'}));await new Promise(r=>setTimeout(r,900));
  const conf=document.getElementById('mConfirm').classList.contains('on');const msg=document.getElementById('mConfirmMsg').textContent;
  if(conf)document.getElementById('mConfirmBtn').click();await new Promise(r=>setTimeout(r,1200));window.toast=ot;return {confirmShown:conf,confirmMsg:msg,toasts:T}}"""
with sync_playwright() as pw:
  b=pw.chromium.launch()
  # ---- 1. build real data through real app functions, export a real backup ----
  ctx=b.new_context(service_workers='block');p=ctx.new_page();errs=[];p.on('pageerror',lambda e:errs.append(str(e)[:200]))
  p.goto(f'http://127.0.0.1:{PORT}/index.html');p.wait_for_timeout(2500);p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
  p.evaluate(SEED)
  txt=p.evaluate("""async()=>{let blob=null;const o=URL.createObjectURL;URL.createObjectURL=b=>{blob=b;return o.call(URL,b)};exportBackup();URL.createObjectURL=o;await new Promise(r=>setTimeout(r,400));return await blob.text()}""")
  open(SP+'real_backup_'+str(PORT)+'.json','w').write(txt)
  before=p.evaluate(DIGEST); ctx.close()
  data=json.loads(txt)
  chk('Export: real backup file produced with all stores',all(k in data for k in ['customers','sales','payments','products','posSales','creditLedger','expenses','cashDrawer']),list(data.keys()))
  print('   backup contents:',{k:len(v) for k,v in data.items() if isinstance(v,list)},'| payment methods:',sorted(set(str(x.get('method')) for x in data['payments'])))
  # ---- 2. restore into a FRESH profile ----
  ctx=b.new_context(service_workers='block');p=ctx.new_page();errs2=[];p.on('pageerror',lambda e:errs2.append(str(e)[:200]))
  p.goto(f'http://127.0.0.1:{PORT}/index.html');p.wait_for_timeout(2500);p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
  r=p.evaluate(RESTORE,txt); after=p.evaluate(DIGEST)
  print('   restore result:',json.dumps({**r,'pageErrors':errs2},ensure_ascii=False)[:700])
  chk('Restore: confirmation shown (validation completed)',r['confirmShown'],r)
  chk('Restore: no uncaught JS error',errs2==[],errs2)
  chk('Restore: success message shown',any(t.startswith('success:') for t in r['toasts']),r['toasts'])
  for k in ['customers','sales','payments','products','posSales','creditLedger','expenses','stockMovements']:
      chk(f'Restore: {k} identical to backup (updated_at re-stamp ignored)',after[k]==before[k],{'before':before['counts'].get(k),'after':after['counts'].get(k)})
  chk('Restore: cash drawer identical',after['cashDrawer']==before['cashDrawer'],[before['cashDrawer'],after['cashDrawer']])
  chk('Restore: every payment method identical',after['payMethods']==before['payMethods'],[before['payMethods'],after['payMethods']])
  chk('Restore: credit-ledger and expense methods identical',after['clMethods']==before['clMethods'] and after['expMethods']==before['expMethods'],'')
  chk('Restore: debts and account credit identical',after['debts']==before['debts'] and after['credit']==before['credit'],[before['debts'],after['debts']])
  # ---- 3. restore the same file again: merge-by-id means no duplicates ----
  r2=p.evaluate(RESTORE,txt); again=p.evaluate(DIGEST)
  chk('Re-restore of same file: no duplicates (merge by id preserved)',again['counts']==after['counts'],[after['counts'],again['counts']])
  # ---- 4. malformed files rejected safely, nothing changes ----
  for lbl,bad in [('not JSON','{{{not json'),('JSON array','[1,2,3]'),('no Bizora data','{"hello":1}'),('truncated file',txt[:len(txt)//2])]:
      r3=p.evaluate(RESTORE,bad); now=p.evaluate(DIGEST)
      chk(f'Malformed backup ({lbl}): rejected with an error message, data untouched',not r3['confirmShown'] and any(t.startswith('error:') for t in r3['toasts']) and now['counts']==after['counts'],r3)
  chk('Restore phase: no uncaught JS errors overall',errs2==[],errs2)
  chk('Backup contains the 4.3.8 deposit methods (POS MoMo deposit, invoice bank deposit)',any(x.get('notes')=='Deposit at POS checkout' and x.get('method')=='mobile-money' for x in data['payments']) and any(x.get('notes')=='Deposit at time of sale' and x.get('method')=='bank-transfer' for x in data['payments']),[ (x.get('notes'),x.get('method')) for x in data['payments']])
  # ---- 5. a failure part-way is reported as a failure, never as success ----
  ctx.close();ctx=b.new_context(service_workers='block');p=ctx.new_page();errs3=[];p.on('pageerror',lambda e:errs3.append(str(e)[:200]))
  p.goto(f'http://127.0.0.1:{PORT}/index.html');p.wait_for_timeout(2500);p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
  p.evaluate("()=>{const os=S.set;window.__boom=true;S.set=(k,v)=>{if(k==='payments'&&window.__boom){window.__boom=false;throw new Error('simulated storage failure');}return os(k,v)};}")
  r5=p.evaluate(RESTORE,txt)
  lg=p.evaluate("()=>S.get('activities').concat(S.get('auditLog')).map(a=>a.msg).filter(m=>/Backup restore/.test(m))")
  chk('Partial failure: error message shown, NO success message, failure logged',any(t.startswith('error:') and 'simulated storage failure' in t for t in r5['toasts']) and not any(t.startswith('success:') for t in r5['toasts']) and any('FAILED' in m for m in lg),{'toasts':r5['toasts'],'log':lg})
  chk('Partial failure: no uncaught JS error',errs3==[],errs3)
  b.close()
srv.shutdown()
print('TOTAL',len(res),'PASS',sum(c for _,c in res),'FAIL',sum(1 for _,c in res if not c))
