import threading,http.server,functools,json,sys
from playwright.sync_api import sync_playwright
out={}
for d,port in [('/home/claude/bz16',8821),('/home/claude/main',8822)]:
  h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=d);h.log_message=lambda *a:None
  srv=http.server.ThreadingHTTPServer(('127.0.0.1',port),h);threading.Thread(target=srv.serve_forever,daemon=True).start()
  with sync_playwright() as pw:
    b=pw.chromium.launch();p=b.new_page();errs=[];p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto(f'http://127.0.0.1:{port}/index.html');p.wait_for_timeout(2500)
    r=p.evaluate("""async()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));window.toast=()=>{};(typeof loadSampleData==='function')&&loadSampleData();
      await DevSuite.runAll();try{DevSuite._renderTestResults()}catch(e){}
      await DevSuite.runValidator().catch(e=>String(e));
      const t=DevSuite._testResults;return {v:APP_VERSION,pass:t.filter(x=>x.status==='PASS').length,fail:t.filter(x=>x.status==='FAIL').map(x=>x.name+': '+x.detail),warn:t.filter(x=>x.status==='WARNING').map(x=>x.name),total:t.length,val:DevSuite._lastValidation}}""")
    r['errs']=errs;out[d]=r;b.close()
  srv.shutdown()
print(json.dumps(out,indent=1,ensure_ascii=False,default=str)[:3000])
