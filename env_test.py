"""Locale environments in Firefox and Chrome: which launch configuration gives which observable locale.

usage: .venv/bin/python env_test.py <chrome|firefox> <config-name>... (or 'all') > env/<browser>.jsonl
"""
import asyncio, http.server, json, os, shutil, socketserver, sys, tempfile, threading

CHROME = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
FIREFOX = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
HERE = os.path.dirname(os.path.abspath(__file__))

LANGPACKS = os.path.expanduser('~/.cache/intl-compat-langpacks')
# Firefox UI locale a user in each locale would run (Firefox has no zh-HK build; HK users get zh-TW).
FX_UI = {'en-US': None, 'en-GB': 'en-GB', 'ar-SA': 'ar', 'ar-EG': 'ar', 'pt-BR': 'pt-BR', 'pt-PT': 'pt-PT',
         'zh-CN': 'zh-CN', 'zh-TW': 'zh-TW', 'zh-HK': 'zh-TW', 'is-IS': 'is'}

def langpack(ui):
    return os.path.join(LANGPACKS, f'firefox-163.0a1.{ui}.langpack.xpi') if ui else None

def apple(langs=None, locale=None):
    a = []
    if langs: a += ['-AppleLanguages', '(' + ', '.join(langs) + ')']
    if locale: a += ['-AppleLocale', locale]
    return a

# name: (launch args, Firefox prefs, Firefox langpack locale, override locale)
CONFIGS = {
    'default': ([], {}, None, None),
    'apple-en-GB': (apple(['en-GB']), {}, None, None),
    'apple-en-US-locale-en_FI': (apple(['en-US'], 'en_FI'), {}, None, None),
    'apple-en-FI': (apple(['en-FI']), {}, None, None),
    'apple-en-SE': (apple(['en-SE']), {}, None, None),
}
CONFIGS['override-en-FI'] = ([], {'intl.accept_languages': 'en-GB'}, None, 'en-FI')
for loc in ['en-US', 'en-GB', 'ar-SA', 'ar-EG', 'pt-BR', 'pt-PT', 'zh-CN', 'zh-TW', 'zh-HK', 'is-IS']:
    CONFIGS[f'apple-{loc}'] = (apple([loc]), {}, None, None)
    ui = FX_UI[loc]
    CONFIGS[f'real-{loc}'] = (apple([loc]), {'intl.locale.requested': ui} if ui else {}, langpack(ui), None)
    CONFIGS[f'override-{loc}'] = ([], {'intl.accept_languages': loc}, None, loc)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=os.path.join(HERE, 'env'), **kw)
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith('/report.js'): return super().do_GET()
        al = self.headers.get('Accept-Language', '')
        body = (f'<!doctype html><html data-accept-language="{al}"><meta charset=utf-8>'
                '<script src=/report.js></script>env').encode()
        self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

def serve():
    s = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Handler); s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{s.server_address[1]}/'

async def chrome(url, name, cfg):
    """Launch Chrome directly (Playwright rejects -AppleLanguages style args) and attach over CDP."""
    import subprocess, time
    from playwright.async_api import async_playwright
    args, _, _, override = cfg
    d = tempfile.mkdtemp()
    proc = subprocess.Popen([CHROME, f'--user-data-dir={d}', '--remote-debugging-port=0', '--no-first-run',
                             '--no-default-browser-check', *args, 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port_file = os.path.join(d, 'DevToolsActivePort')
        for _ in range(100):
            if os.path.exists(port_file) and open(port_file).read().strip(): break
            time.sleep(0.1)
        port = open(port_file).read().split()[0]
        async with async_playwright() as p:
            b = await p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
            ctx = b.contexts[0] if not override else await b.new_context(locale=override)
            page = await ctx.new_page()
            await page.goto(url)
            r = await page.evaluate('window.__report()')
            await b.close()
    finally:
        proc.terminate(); proc.wait(10)
        shutil.rmtree(d, ignore_errors=True)
    return r

def firefox(url, name, cfg):
    from selenium import webdriver
    args, prefs, langpack, override = cfg
    o = webdriver.FirefoxOptions(); o.binary_location = FIREFOX; o.enable_bidi = True
    for a in args: o.add_argument(a)
    for k, v in prefs.items(): o.set_preference(k, v)
    drv = webdriver.Firefox(options=o)
    try:
        if langpack:
            drv.install_addon(langpack, temporary=True)
            import time; time.sleep(1)
        if override:
            drv.emulation.set_locale_override(locale=override, contexts=[drv.current_window_handle])
        drv.get(url)
        return drv.execute_async_script('const cb = arguments[0]; window.__report().then(cb, e => cb(String(e)))')
    finally:
        drv.quit()

def main():
    browser, names = sys.argv[1], sys.argv[2:]
    if names == ['all']: names = list(CONFIGS)
    url = serve()
    for n in names:
        cfg = CONFIGS[n]
        try:
            r = asyncio.run(chrome(url, n, cfg)) if browser == 'chrome' else firefox(url, n, cfg)
        except Exception as e:
            r = {'error': f'{type(e).__name__}: {e}'[:300]}
        print(json.dumps({'browser': browser, 'config': n, **r}, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
