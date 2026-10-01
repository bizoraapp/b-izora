import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright
DIR=sys.argv[1] if len(sys.argv)>1 else '/home/claude/main'
SP='/tmp/claude-0/-home-claude/d20444c6-f35c-54ec-9840-7188b4997f3e/scratchpad/'
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=DIR); h.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8805),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
results=[]
def chk(n,c,info=''):
    results.append((n,bool(c))); print(('PASS' if c else 'FAIL'),'|',n,'|',json.dumps(info,ensure_ascii=False)[:700] if not c else '')
def fresh(b,vw=390):
    ctx=b.new_context(service_workers='block',viewport={'width':vw,'height':820}); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://127.0.0.1:8805/index.html'); p.wait_for_timeout(2200)
    p.evaluate("()=>{document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))}"); return p,errs
SETUP_MODERN="""async()=>{window.__t=[];window.toast=(m)=>{window.__t.push(String(m))};
  document.getElementById('sOwnerPassword').value='realOwner9';document.getElementById('sOwnerPasswordConfirm').value='realOwner9';await saveOwnerPassword();
  window.__code=document.getElementById('recoveryCodeText').textContent;document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
  S.add('expenses',{id:'e1',date:todayStr(),amount:50000,category:'rent',description:'Shop rent'});
  const c=await createEmployee({fullName:'Cash Ier',username:'cashier1',password:'1234',role:'cashier'});window.__emp=c.employee.id;return window.__code}"""
SETUP_LEGACY="""async()=>{window.__t=[];window.toast=(m)=>{window.__t.push(String(m))};
  const salt=genSalt();setAccessControl({enabled:true,pendingSetup:false,ownerPasswordHash:await hashPassword('legacyOwner9',salt),ownerPasswordSalt:salt,recoveryCodeHash:'',recoveryCodeSalt:''});
  S.add('expenses',{id:'e1',date:todayStr(),amount:50000,category:'rent',description:'Shop rent'});
  const c=await createEmployee({fullName:'Cash Ier',username:'cashier1',password:'1234',role:'cashier'});window.__emp=c.employee.id;return true}"""
LOGIN_CASHIER="""async()=>{await Auth.loginEmployee(window.__emp,'1234');document.getElementById('empIdScreen').style.display='none';onEmployeeSessionStarted();}"""
vis=lambda p,id: p.evaluate(f"()=>{{const e=document.getElementById('{id}');return !!e&&getComputedStyle(e).display!=='none'&&!!(e.offsetWidth||e.offsetHeight)}}")
with sync_playwright() as pw:
  b=pw.chromium.launch()
  # ================== 1. ORIGINAL TAKEOVER (recovery code exists) ==================
  p,errs=fresh(b); code=p.evaluate(SETUP_MODERN); p.wait_for_timeout(1200); p.reload(); p.wait_for_timeout(2500)
  p.evaluate("()=>{window.__t=[];window.toast=(m)=>{window.__t.push(String(m))};window.__emp=S.get('employees')[0].id}")
  p.evaluate(LOGIN_CASHIER)
  r=p.evaluate("()=>{delExpense('e1');const c=document.getElementById('mConfirm');if(c.classList.contains('on'))document.getElementById('mConfirmBtn').click();return S.get('expenses').some(e=>e.id==='e1')}")
  chk('Takeover setup: cashier cannot delete the protected expense',r)
  p.evaluate("()=>switchUser()"); p.wait_for_timeout(300)
  p.click("text=I am the Business Owner"); p.wait_for_timeout(200); p.click("#ownerForgotBtn"); p.wait_for_timeout(200)
  chk('Takeover: recovery-code entry shown; "Don\'t have the code either?" is NOT visible',vis(p,'ownerRecCodeEntry') and not vis(p,'ownerRecNoCodeLink'))
  chk('Takeover: "Don\'t have the code either?" cannot be clicked',p.locator("text=Don't have the code either?").is_visible()==False)
  # forged UI state: reveal the hidden link and reset panel, try RESET through the real buttons
  p.evaluate("()=>{document.getElementById('ownerRecNoCodeLink').style.display='block'}"); p.click("text=Don't have the code either?"); p.wait_for_timeout(200)
  r1=p.evaluate("()=>({resetPanel:getComputedStyle(document.getElementById('ownerRecReset')).display,toast:window.__t.slice(-1)[0]||''})")
  chk('Forged UI: revealed link -> showOwnerRecoveryReset() refuses, reset panel stays closed',r1['resetPanel']=='none' and 'recovery code exists' in r1['toast'],r1)
  p.evaluate("()=>{document.getElementById('ownerRecCodeEntry').style.display='none';document.getElementById('ownerRecReset').style.display='block'}")
  p.fill('#ownerResetConfirmInput','RESET'); p.click("text=Turn Off Access Control"); p.wait_for_timeout(400)
  r=p.evaluate("()=>{const ac=getAccessControl();return {acEnabled:ac.enabled,pw:!!ac.ownerPasswordHash,code:!!ac.recoveryCodeHash,isOwner:Auth.isOwner()&&!!Auth.isEmployeeMode()&&document.getElementById('empIdScreen').style.display==='none',toast:window.__t.slice(-1)[0]||'',idScreen:getComputedStyle(document.getElementById('empIdScreen')).display}}")
  chk('Takeover: typing RESET is refused — Access Control stays ON, owner password + code intact',r['acEnabled'] and r['pw'] and r['code'] and 'recovery code exists' in r['toast'],r)
  chk('Takeover: person at lock screen did NOT become Business Owner (identify screen still up)',r['idScreen']!='none',r)
  r=p.evaluate("()=>{window.__t=[];confirmOwnerRecoveryReset();const ac=getAccessControl();return {acEnabled:ac.enabled,pw:!!ac.ownerPasswordHash,toast:window.__t.slice(-1)[0]||''}}")
  chk('Direct confirmOwnerRecoveryReset() call refused when a code exists',r['acEnabled'] and r['pw'] and 'recovery code exists' in r['toast'],r)
  r=p.evaluate("()=>{showOwnerRecoveryReset();return getComputedStyle(document.getElementById('ownerRecReset')).display}")
  chk('Direct showOwnerRecoveryReset() call refused when a code exists',r=='none',r)
  # expense still present; any subsequent attempt as unauthenticated session
  r=p.evaluate("()=>{document.getElementById('empIdScreen').style.display='none';delExpense('e1');const c=document.getElementById('mConfirm');if(c.classList.contains('on'))document.getElementById('mConfirmBtn').click();return {stillThere:S.get('expenses').some(e=>e.id==='e1'),owner:Auth.isOwner()}}")
  # Note: with Access Control on and nobody logged in, Auth._current=null means "owner" in the code model; the identify screen is the gate.
  print('   info (devtools-only, pre-existing): hiding the identify overlay by hand while nobody is logged in leaves the session as Owner:',r)
  p.evaluate("()=>{S.add('expenses',{id:'e1',date:todayStr(),amount:50000,category:'rent',description:'Shop rent'});showEmployeeIdentifyScreen();showOwnerLoginPanel();}")
  # recovery-code verification can't be bypassed by forging the verified-code variable
  r=p.evaluate("""async()=>{window.__t=[];ownerRecoveryVerifiedCode='AAAA-BBBB-CCCC';document.getElementById('ownerRecNewPassword').value='hacker99';document.getElementById('ownerRecNewPasswordConfirm').value='hacker99';
    await submitOwnerRecoveryNewPassword();const bad=await Auth.loginOwner('hacker99');const good=await Auth.loginOwner('realOwner9');Auth._current=null;return {hackerPw:bad.ok,realPw:good.ok,toast:window.__t.slice(-1)[0]||''}}""")
  chk('Forged ownerRecoveryVerifiedCode + direct submitOwnerRecoveryNewPassword() refused (real password unchanged)',(not r['hackerPw']) and r['realPw'],r)
  # wrong recovery code
  p.evaluate("()=>{showOwnerForgotPanel()}"); p.fill('#ownerRecCodeInput','WXYZ-WXYZ-WXYZ'); p.click("#ownerRecCodeEntry >> text=Verify"); p.wait_for_timeout(400)
  r=p.evaluate("()=>({err:document.getElementById('ownerRecCodeError').textContent,newPwPanel:getComputedStyle(document.getElementById('ownerRecNewPw')).display})")
  chk('Recovery-code failure: wrong code rejected, new-password step not reached',r['err']!='' and r['newPwPanel']=='none',r)
  # correct recovery code -> new password
  p.evaluate("()=>{showOwnerForgotPanel()}"); p.fill('#ownerRecCodeInput',code); p.click("#ownerRecCodeEntry >> text=Verify"); p.wait_for_timeout(400)
  p.fill('#ownerRecNewPassword','newOwner77'); p.fill('#ownerRecNewPasswordConfirm','newOwner77'); p.click("text=Save New Password"); p.wait_for_timeout(700)
  r=p.evaluate("""async()=>{const ac=getAccessControl();const newCodeShown=document.getElementById('mRecoveryCode').classList.contains('on');document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
    const n=await Auth.loginOwner('newOwner77');const o=await Auth.loginOwner('realOwner9');return {enabled:ac.enabled,newPw:n.ok,oldPw:o.ok,codeRotated:newCodeShown,owner:Auth.isOwner(),emps:S.get('employees').length,aud:S.get('auditLog').slice(-6).map(a=>a.type+'|'+a.user+'|'+a.msg)}}""")
  chk('Correct recovery code -> new owner password works (old one no longer), code rotated, employees kept',r['enabled'] and r['newPw'] and not r['oldPw'] and r['codeRotated'] and r['emps']==1,r)
  r=p.evaluate("()=>{delExpense('e1');const c=document.getElementById('mConfirm');if(c.classList.contains('on'))document.getElementById('mConfirmBtn').click();return !S.get('expenses').some(e=>e.id==='e1')}")
  chk('Legitimate owner (recovered with code) can delete the expense',r)
  chk('Modern-path: no JS errors',errs==[],errs); p.context.close()

  # ================== 2. LEGACY OWNER (no recovery code) ==================
  p,errs=fresh(b); p.evaluate(SETUP_LEGACY); p.wait_for_timeout(1200); p.reload(); p.wait_for_timeout(2500)
  p.evaluate("()=>{window.__t=[];window.toast=(m)=>{window.__t.push(String(m))};window.__emp=S.get('employees')[0].id}")
  p.evaluate(LOGIN_CASHIER)
  p.evaluate("()=>{go('pos')}")
  p.evaluate("()=>switchUser()"); p.wait_for_timeout(300)
  p.click("text=I am the Business Owner"); p.wait_for_timeout(200); p.click("#ownerForgotBtn"); p.wait_for_timeout(200)
  chk('Legacy: no-code notice + "Reset Access Control" still offered (escape hatch kept)',vis(p,'ownerRecNoCode'))
  p.click("#ownerRecNoCode >> text=Reset Access Control"); p.wait_for_timeout(200)
  p.fill('#ownerResetConfirmInput','RESET'); p.click("text=Turn Off Access Control"); p.wait_for_timeout(600)
  r=p.evaluate("()=>{const ac=getAccessControl();const log=S.get('auditLog');const w=[...log].reverse().find(a=>a.type==='security');return {enabled:ac.enabled,flag:!!ac.unverifiedResetAt,lastUserStored:ac.unverifiedResetLastUser,emps:S.get('employees').length,exp:S.get('expenses').length,warn:w&&{user:w.user,role:w.role,msg:w.msg,date:w.date,time:w.time}}}")
  w=r['warn'] or {}
  chk('Legacy RESET works (owner not locked out); employees/expenses untouched',(not r['enabled']) and r['flag'] and r['emps']==1 and r['exp']==1,r)
  chk('Legacy RESET audit warning: type Security, says UNVERIFIED, names last user with time, has timestamp',w.get('msg','').startswith('UNVERIFIED lock-screen reset — no owner password or recovery code. Last user on this device: Cash Ier (') and 'Reset at' in w.get('msg','') and w.get('date') and w.get('time'),w)
  chk('Legacy RESET warning is attributed to "Unverified Owner", not "Business Owner", and does not claim Cash Ier did it',w.get('user')=='Unverified Owner (after lock-screen reset)' and w.get('role')=='Unverified Owner (after lock-screen reset)',w)
  r=p.evaluate("()=>{delExpense('e1');const c=document.getElementById('mConfirm');if(c.classList.contains('on'))document.getElementById('mConfirmBtn').click();const d=[...S.get('auditLog')].reverse().find(a=>a.type==='delete');return {deleted:!S.get('expenses').some(e=>e.id==='e1'),user:d&&d.user,role:d&&d.role,msg:d&&d.msg}}")
  chk('After legacy reset: later actions attributed "Unverified Owner (after lock-screen reset)" in the audit path',r['deleted'] and r['user']=='Unverified Owner (after lock-screen reset)' and r['role']=='Unverified Owner (after lock-screen reset)',r)
  r=p.evaluate("()=>{go('settings');return {rows:[...document.querySelectorAll('.audit-row-warn')].length}}")
  p.evaluate("()=>openAuditLog&&openAuditLog()"); p.wait_for_timeout(300)
  r=p.evaluate("()=>{const rows=[...document.querySelectorAll('.audit-row.audit-row-warn')].map(r=>r.innerText.replace(/\\s+/g,' '));return {warnRows:rows.filter(x=>/Security Warning/.test(x)).length,sample:rows.find(x=>/UNVERIFIED/.test(x))||''}}")
  chk('Audit Log screen: reset shown as highlighted "⚠️ Security Warning" row',r['warnRows']>=1 and 'UNVERIFIED' in r['sample'],r)
  p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
  # survives reload
  p.wait_for_timeout(1200); p.reload(); p.wait_for_timeout(2500)
  r=p.evaluate("()=>{window.toast=()=>{};log('system','test after reload');const a=S.get('auditLog').slice(-1)[0];return {user:a.user,flag:!!getAccessControl().unverifiedResetAt}}")
  chk('Unverified attribution persists across reload until verified identity restored',r['user']=='Unverified Owner (after lock-screen reset)' and r['flag'],r)
  # restore verified identity: set a new owner password (creates recovery code)
  r=p.evaluate("""async()=>{window.__t=[];window.toast=(m)=>{window.__t.push(String(m))};document.getElementById('sOwnerPassword').value='owner2025';document.getElementById('sOwnerPasswordConfirm').value='owner2025';await saveOwnerPassword();
    const codeShown=document.getElementById('mRecoveryCode').classList.contains('on');document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'));
    const ac=getAccessControl();const tail=S.get('auditLog').slice(-3).map(a=>a.type+'|'+a.user+'|'+a.msg.slice(0,90));log('system','after restore');const after=S.get('auditLog').slice(-1)[0].user;
    return {flag:!!ac.unverifiedResetAt,code:!!ac.recoveryCodeHash,codeShown,tail,after}}""")
  chk('New owner password after legacy reset: recovery code created, marker cleared, transition logged as Security by Unverified Owner, later entries "Business Owner"',(not r['flag']) and r['code'] and r['codeShown'] and any(x.startswith('security|Unverified Owner') for x in r['tail']) and r['after']=='Business Owner',r)
  # now the anonymous reset is closed
  r=p.evaluate("()=>{window.__t=[];document.getElementById('ownerResetConfirmInput').value='RESET';confirmOwnerRecoveryReset();return {enabled:getAccessControl().enabled,toast:window.__t.slice(-1)[0]||''}}")
  chk('After recovery code exists, anonymous RESET is permanently closed',r['enabled'] and 'recovery code exists' in r['toast'],r)
  chk('Legacy-reset path: no JS errors',errs==[],errs); p.context.close()

  # ================== 3. LEGACY OWNER legitimate login -> required code ==================
  p,errs=fresh(b); p.evaluate(SETUP_LEGACY); p.wait_for_timeout(1200); p.reload(); p.wait_for_timeout(2500)
  p.evaluate("()=>{window.__t=[];window.toast=(m)=>{window.__t.push(String(m))}}")
  p.click("text=I am the Business Owner"); p.wait_for_timeout(200)
  p.fill('#ownerLoginPassword','legacyOwner9'); p.click("#ownerLoginBox button.lrp-btn.primary, #ownerLoginBox >> text=Log In"); p.wait_for_timeout(800)
  r=p.evaluate("()=>({owner:Auth.isOwner(),idScreen:document.getElementById('empIdScreen').style.display,code:!!getAccessControl().recoveryCodeHash,modal:document.getElementById('mRecoveryCode').classList.contains('on'),codeText:document.getElementById('recoveryCodeText').textContent,toast:window.__t.slice(-1)[0]||'',aud:S.get('auditLog').slice(-1)[0].msg})")
  chk('Legacy owner legitimate login: recovery code created and shown, logged',r['owner'] and r['idScreen']=='none' and r['code'] and r['modal'] and len(r['codeText'])>=12 and 'Recovery code created at owner login' in r['aud'],r)
  p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
  r=p.evaluate("""async()=>{Auth._current=null;await submitOwnerLogin.call(null).catch(()=>{});return 1}""")
  r=p.evaluate("()=>{window.__t=[];document.getElementById('ownerResetConfirmInput').value='RESET';confirmOwnerRecoveryReset();return {enabled:getAccessControl().enabled,toast:window.__t.slice(-1)[0]||''}}")
  chk('After required code creation, anonymous RESET closed for legacy owner too',r['enabled'] and 'recovery code exists' in r['toast'],r)
  chk('Legacy login path: no JS errors',errs==[],errs); p.context.close()

  # ================== 4. UNCHANGED BEHAVIOUR ==================
  p,errs=fresh(b); code=p.evaluate(SETUP_MODERN)
  r=p.evaluate("""async()=>{Auth.logout();document.getElementById('empIdScreen').style.display='none';
    const bad=await Auth.loginOwner('nope');const ok=await Auth.loginOwner('realOwner9');const owner=Auth.isOwner();
    const nCodeBefore=getAccessControl().recoveryCodeHash;await ensureOwnerRecoveryCode();const same=getAccessControl().recoveryCodeHash===nCodeBefore;
    const e1=await Auth.loginEmployee(window.__emp,'1234');const e2=await Auth.loginEmployee(window.__emp,'bad');
    return {badOwner:bad.ok,okOwner:ok.ok,owner,codeNotRegenerated:same,empOk:e1.ok,empBad:e2.ok,acOn:getAccessControl().enabled,auditUserForEmployee:S.get('auditLog').filter(a=>a.type==='login').slice(-1)[0].user}}""")
  chk('Normal owner login unchanged; existing recovery code not regenerated at login',(not r['badOwner']) and r['okOwner'] and r['codeNotRegenerated'],r)
  chk('Employee login unchanged; attribution for employee is their own name',r['empOk'] and not r['empBad'] and r['auditUserForEmployee']=='Cash Ier',r)
  chk('Access Control remains on / unchanged',r['acOn'],r)
  r=p.evaluate("()=>({preserved:START_FRESH_PRESERVED_STORES.includes('auditLogs'),targetsExcludeAudit:!startFreshTargetStores().includes('auditLogs'),storeName:KEY_TO_STORE.auditLog})")
  chk('Start Fresh still preserves auditLogs (store name matches)',r['preserved'] and r['targetsExcludeAudit'] and r['storeName']=='auditLogs',r)
  # device PIN flow untouched: confirmLockReset still works with RESET
  r=p.evaluate("()=>{setSecurity({lockType:'pin4',pin:'1234',autoLockMins:0,recoveryQ:'',recoveryHash:''});window.__t=[];document.getElementById('lockResetConfirmInput').value='RESET';confirmLockReset();return getSecurity().lockType}")
  chk('Device PIN "Forgot PIN → RESET" behaviour unchanged (out of scope)',r=='none',r)
  chk('Unchanged-behaviour checks: no JS errors',errs==[],errs); p.context.close()

  # ================== 5. FR + 360 ==================
  p,errs=fresh(b,360); p.evaluate(SETUP_MODERN); p.evaluate("()=>{setLang('fr');window.__t=[];document.getElementById('ownerResetConfirmInput').value='RESET';confirmOwnerRecoveryReset()}")
  fr=p.evaluate("()=>window.__t.slice(-1)[0]||''")
  chk('FR: refusal message translated','code de récupération existe' in fr,fr)
  p.evaluate("()=>{switchUser()}"); p.wait_for_timeout(300); p.click("text=I am the Business Owner"); p.wait_for_timeout(150); p.click("#ownerForgotBtn"); p.wait_for_timeout(300)
  fits=p.evaluate("()=>document.documentElement.scrollWidth<=innerWidth")
  p.screenshot(path=SP+'owner_forgot_360.png')
  chk('360px: owner recovery panel (code entry only) fits, no overflow',fits and vis(p,'ownerRecCodeEntry') and not vis(p,'ownerRecNoCodeLink'))
  p.context.close()
  p,errs2=fresh(b,360); p.evaluate(SETUP_LEGACY); p.evaluate("()=>setLang('fr')")
  r=p.evaluate("""async()=>{window.__t=[];Auth._current=null;await submitOwnerLogin().catch(()=>{});return 1}""")
  p.fill('#ownerLoginPassword','legacyOwner9') if vis(p,'ownerLoginPassword') else None
  r=p.evaluate("""async()=>{window.__t=[];const r=await Auth.loginOwner('legacyOwner9');await ensureOwnerRecoveryCode();return window.__t.slice(-1)[0]||''}""")
  chk('FR: required-recovery-code message translated','code de récupération a été créé' in r,r)
  p.wait_for_timeout(300); p.screenshot(path=SP+'owner_code_modal_360.png')
  chk('FR/360: no JS errors',errs==[] and errs2==[],errs+errs2); p.context.close()
  b.close()
srv.shutdown()
f=[x for x in results if not x[1]]
print('\nTOTAL',len(results),'FAIL',len(f)); [print('  FAILED:',x[0]) for x in f]
