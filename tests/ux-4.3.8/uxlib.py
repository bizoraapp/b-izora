"""Shared helpers for the Bizora 4.3.8 UX suite. Path-independent: serves the repo root on a free port."""
import os, sys, json, time, threading, http.server, functools, socketserver
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UA = 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36'
TODAY_SEED = '2026-01-05'

class _H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
class _S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True

def serve():
    srv = _S(('127.0.0.1', 0), functools.partial(_H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/index.html'

RESULTS = []
WARNS = []
def chk(layer, name, cond, info='', warn=False):
    """warn=True: advisory finding (printed as WARN, does not fail the run)."""
    if warn and not cond:
        WARNS.append((layer, name)); print('WARN', '|', layer, '|', name, '| ' + json.dumps(info, ensure_ascii=False, default=str)[:600]); return
    RESULTS.append((layer, name, bool(cond)))
    print(('PASS' if cond else 'FAIL'), '|', layer, '|', name, '' if cond else '| ' + json.dumps(info, ensure_ascii=False, default=str)[:600])

def summary():
    layers = {}
    for l, n, c in RESULTS:
        a = layers.setdefault(l, [0, 0]); a[1] += 1; a[0] += c
    print('\n=== UX SUMMARY ===')
    for l, (p, t) in layers.items(): print(f'{l:<34} {p}/{t}')
    p = sum(c for _, _, c in RESULTS); t = len(RESULTS)
    print(f'{"TOTAL":<34} {p}/{t}   (advisory warnings: {len(WARNS)})')
    return p == t

def new_page(browser, url, lang='en', vw=360, vh=640, offline=False, fresh=False):
    """Phone-sized page. Returns (page, errors). Dismisses nothing: caller decides about the first-run wizard."""
    ctx = browser.new_context(viewport={'width': vw, 'height': vh}, user_agent=UA, has_touch=True, is_mobile=True,
                              device_scale_factor=2, service_workers='block', timezone_id='Africa/Douala', locale='fr-CM' if lang == 'fr' else 'en-US')
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') or r.request.url.startswith('data:') or r.request.url.startswith('blob:') else r.abort())   # no real network: fonts fall back like on a weak connection
    p = ctx.new_page(); errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' else None)
    p.goto(url + ('?devreset=1' if fresh else '')); p.wait_for_timeout(1800)
    return p, errs, ctx

def close_modals(p):
    p.evaluate("()=>document.querySelectorAll('.modal-bg.on').forEach(m=>m.classList.remove('on'))")
