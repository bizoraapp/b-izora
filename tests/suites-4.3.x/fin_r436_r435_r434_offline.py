import threading, http.server, functools, json
from playwright.sync_api import sync_playwright
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory='/home/claude/main'); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8891),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
R={}
with sync_playwright() as pw:
  b=pw.chromium.launch(); ctx=b.new_context(); p=ctx.new_page()
  errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
  # Simulate a device upgrading from live 4.2.7: pre-seed live (v120) and older (v114, v113) caches
  p.goto('http://127.0.0.1:8891/offline.html'); p.wait_for_timeout(500)
  p.evaluate("async()=>{for(const v of ['v113','v114','v120']){const c=await caches.open('bizora-'+v);await c.put('/x',new Response('x'));}}")
  p.goto('http://127.0.0.1:8891/index.html'); p.wait_for_timeout(3000)
  p.evaluate("async()=>{await navigator.serviceWorker.ready}"); p.wait_for_timeout(1500)
  p.reload(); p.wait_for_timeout(2500)
  R['controlled']=p.evaluate("!!navigator.serviceWorker.controller")
  R['caches_after_upgrade']=sorted(p.evaluate("caches.keys()"))
  ctx.set_offline(True)
  p.reload(); p.wait_for_timeout(3000)
  R['offline_reload_version']=p.evaluate("typeof APP_VERSION!=='undefined'?APP_VERSION:null")
  p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}")
  p.evaluate("go('dashboard')"); p.wait_for_timeout(500)
  R['offline_insights_rendered']=p.evaluate("!!document.querySelector('#insightsFeed .insight-empty, #insightsFeed .insight-card')")
  R['offline_insights_text']=p.evaluate("document.getElementById('insightsFeed').innerText.slice(0,60)")
  p.evaluate("openInsight('never')"); R['offline_nav_products']=p.evaluate("document.querySelector('.page.active').id")
  R['errors']=errs
  b.close()
srv.shutdown(); print(json.dumps(R,indent=1))
