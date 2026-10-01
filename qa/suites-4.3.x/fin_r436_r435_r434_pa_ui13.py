import threading, http.server, functools, json
from playwright.sync_api import sync_playwright
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory='/home/claude/main'); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8854),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
with sync_playwright() as pw:
  b=pw.chromium.launch(); p=b.new_context(service_workers='block',viewport={'width':390,'height':860}).new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
  p.goto('http://127.0.0.1:8854/index.html'); p.wait_for_timeout(2200)
  p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}")
  p.evaluate("""async()=>{S.add('products',{id:'pT',sku:'S1',name:'Rice Bag',category:'G',cost:13500,price:16000,stock:100,lowStock:5,tax:0,added:todayStr()});
    const salt=genSalt();setAccessControl({...getAccessControl(),enabled:true,ownerPasswordSalt:salt,ownerPasswordHash:await hashPassword('ownerpass9',salt)});
    const c=await createEmployee({fullName:'Cash Ier',username:'cash',password:'1234',role:'cashier'});await Auth.loginEmployee(c.employee.id,'1234');onEmployeeSessionStarted();go('pos');resetPosForm();addPosItemFromProduct('pT');}""")
  # REAL interaction: type into the selling-price box and blur (fires onchange), exactly as a cashier would
  inp=p.locator('#posItemsBody .pos-item-row input.num-fmt').nth(1)   # qty is nth(0), selling price nth(1)
  inp.click(); inp.fill('12000'); inp.press('Tab'); p.wait_for_timeout(300)
  print('modal open after real typing:',p.evaluate("document.getElementById('mPriceApproval').classList.contains('on')"),'| field shows:',inp.input_value(),'| grand:',p.evaluate("document.getElementById('posGrandTotal').textContent"))
  p.screenshot(path=SP+'pa_modal_en.png')
  p.fill('#paPassword','ownerpass9'); p.press('#paPassword','Enter'); p.wait_for_timeout(500)   # Enter key submits
  print('after Enter w/ correct pw -> modal:',p.evaluate("document.getElementById('mPriceApproval').classList.contains('on')"),'| field shows:',inp.input_value(),'| grand:',p.evaluate("document.getElementById('posGrandTotal').textContent"),'| body overflow restored:',p.evaluate("document.body.style.overflow==''"))
  p.fill('#posReceived','50000'); p.click('#posCheckoutBtn'); p.wait_for_timeout(500)
  print('real Complete Sale click -> saved total:',p.evaluate("S.get('posSales').slice(-1)[0].total"),'| approver on line:',p.evaluate("S.get('posSales').slice(-1)[0].items[0].priceApprovedBy"))
  # Backdrop tap / Escape closes modal without applying
  p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));resetPosForm();addPosItemFromProduct('pT')}")
  inp=p.locator('#posItemsBody .pos-item-row input.num-fmt').nth(1); inp.click(); inp.fill('9000'); inp.press('Tab'); p.wait_for_timeout(250)
  p.keyboard.press('Escape'); p.wait_for_timeout(200)
  print('Escape -> modal:',p.evaluate("document.getElementById('mPriceApproval').classList.contains('on')"),'| price still catalog:',p.evaluate("posItems[0].discount===0"),'| field shows:',inp.input_value())
  # after Escape, a fresh edit works normally and the old pending is replaced
  inp.click(); inp.fill('8000'); inp.press('Tab'); p.wait_for_timeout(250)
  print('new edit after Escape -> modal shows new price:',p.evaluate("document.getElementById('paProposed').textContent"))
  # French screenshot
  p.evaluate("()=>setLang('fr')"); p.evaluate("()=>{cancelPriceApproval();}"); inp.click(); inp.fill('8000'); inp.press('Tab'); p.wait_for_timeout(250); p.screenshot(path=SP+'pa_modal_fr.png')
  # no horizontal overflow on modal at 360
  p.set_viewport_size({'width':360,'height':720}); p.wait_for_timeout(200)
  print('modal fits 360px (no h-overflow):',p.evaluate("(()=>{const m=document.querySelector('#mPriceApproval .modal');const r=m.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth})()"))
  print('errors',errs); b.close()
srv.shutdown()
