"""A/B comparison of a resolvedOptions().locale variant under one real locale configuration.

A, A2: the browser as a user with <locale> gets it, with ab/rewrite.js counting only; B: the same
browser and wrapper with <variant> (see VARIANTS in ab/rewrite.js) rewriting `locale`. One Chrome launch per locale, headed
(headless Chrome ignores -AppleLanguages), attached over CDP since Playwright rejects those args.

usage: .venv/bin/python ab.py chrome <locale> <variant> ab/pages.jsonl <out-dir> [--concurrency N]
       .venv/bin/python ab.py chrome <locale> <variant> --sanity
Results: <out-dir>/results.jsonl, one line per (page, locale, variant); rerun to resume.
"""
import argparse, asyncio, json, os, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright
import ab_diff, change, harness

CHROME = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
# Full page text (not the template's first 3000 characters): formatted dates sit anywhere.
FULL_TEXT = harness.MEASURE_JS = harness.MEASURE_JS.replace('.slice(0, 3000)', '.slice(0, 50000)')
REWRITE = open(harness.here('ab', 'rewrite.js')).read().replace(
    '/*CLDR_TABLE*/null', open(harness.here('ab', 'cldr-table.json')).read())
PASSBACK = open(harness.here('ab', 'passback.js')).read()
CHALLENGE_JS = """() => {
  const v = s => [...document.querySelectorAll(s)].map(e => (e.value || '').length);
  return { rewrites: window.__abRewrites ?? null, passback: window.__abPassback ?? null,
           visible: (() => { const p = window.__abPassback, t = document.body ? document.body.innerText : '';
             return p ? p.samples.filter(s => typeof s.got === 'string' && s.got.length > 1 && t.includes(s.got)).length : null; })(),
           defaultLocale: new Intl.DateTimeFormat().resolvedOptions().locale,
           turnstile: v('[name="cf-turnstile-response"]'), hcaptcha: v('[name="h-captcha-response"]'),
           recaptcha: v('[name="g-recaptcha-response"]') };
}"""


def setvar(name, value):
    return f"Object.defineProperty(window, {json.dumps(name)}, {{ value: {json.dumps(value)} }});"


class CdpChrome:
    """A headed Chrome Canary for one locale, launched with -AppleLanguages and attached over CDP."""

    def __init__(self, p, locale):
        self.p, self.locale = p, locale

    async def start(self):
        self.dir = tempfile.mkdtemp(prefix='ab-chrome-')
        self.proc = subprocess.Popen(
            [CHROME, f'--user-data-dir={self.dir}', '--remote-debugging-port=0', '--no-first-run',
             '--no-default-browser-check', '--window-position=0,0', '-AppleLanguages', f'({self.locale})',
             'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = os.path.join(self.dir, 'DevToolsActivePort')
        for _ in range(200):
            if os.path.exists(port_file) and open(port_file).read().strip():
                break
            time.sleep(0.1)
        port = open(port_file).read().split()[0]
        for attempt in range(5):  # the port file can appear before Chrome accepts connections
            try:
                self.b = await self.p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=30000)
                break
            except Exception:
                if attempt == 4:
                    self.proc.kill()
                    shutil.rmtree(self.dir, ignore_errors=True)
                    raise
                await asyncio.sleep(2)
        self.version = self.b.version
        return self

    def is_connected(self):
        return self.b.is_connected()

    async def new_context(self, **kw):
        return await self.b.new_context(**kw)

    async def close(self):
        try:
            await asyncio.wait_for(self.b.close(), 20)
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.rmtree(self.dir, ignore_errors=True)


def configure(variant):
    # A counts what the variant would change; B's __abVariant takes precedence and applies it.
    change.INIT_JS = REWRITE + '\n' + setvar('__abCount', variant) + '\n' + PASSBACK
    change.AFTER_INIT_JS = setvar('__abVariant', variant)
    change.EXTRA_MEASURE_JS = CHALLENGE_JS


async def sanity(p, locale, variant):
    """Local page: default locale is the real one, A counts but doesn't change, B changes."""
    url = harness.serve(harness.here('ab')) + 'sanity.html'
    br = await CdpChrome(p, locale).start()
    try:
        out = {}
        for setup in ('before', 'after'):
            ctx = await br.new_context()
            await ctx.add_init_script(REWRITE + '\n' + PASSBACK)
            await ctx.add_init_script(setvar('__abVariant', variant) if setup == 'after' else setvar('__abCount', variant))
            pg = await ctx.new_page()
            await pg.goto(url)
            out[setup] = await pg.evaluate('window.__sanity()')
            await ctx.close()
        return {'browser': 'chrome', 'version': br.version, 'locale': locale, 'variant': variant, **out}
    finally:
        await br.close()


async def run(args):
    configure(args.variant)
    os.makedirs(f'{args.out_dir}/shots', exist_ok=True)
    path = f'{args.out_dir}/results.jsonl'
    key = lambda r: (r['page'], r['locale'], r['variant'])
    done = {key(r) for r in map(json.loads, open(path))} if os.path.exists(path) else set()
    rows = [json.loads(l) for l in open(args.pages)]
    async with async_playwright() as p:
        state = {'br': await CdpChrome(p, args.locale).start(), 'timeouts': 0}
        print('chrome', state['br'].version, args.locale, args.variant, flush=True)
        sem, lock = asyncio.Semaphore(args.concurrency), asyncio.Lock()

        async def one(r):
            if (r['page'], args.locale, args.variant) in done:
                return
            async with sem:
                visits = {}
                for tag, setup in (('A', 'before'), ('A2', 'before'), ('B', 'after')):
                    br = state['br']
                    shot = f"{args.out_dir}/shots/{r['idx']}-{args.locale}-{args.variant}-{tag}.png"
                    rec = await harness.guarded(harness.visit(br, r['page'], r['client'], setup, shot))
                    visits[tag] = rec
                    hung = rec.get('error', '').startswith('visit timed out')
                    async with lock:
                        state['timeouts'] = state['timeouts'] + 1 if hung else 0
                        if state['br'] is br and (state['timeouts'] >= 3 or not br.is_connected()):
                            print('relaunching', flush=True)
                            state['br'] = await CdpChrome(p, args.locale).start()
                            state['timeouts'] = 0
                            async def close_later(old=br):
                                await asyncio.sleep(95)  # visits still on it finish or time out first
                                await old.close()
                            asyncio.get_running_loop().create_task(close_later())
            a, a2, b = visits['A'], visits['A2'], visits['B']
            res = {**r, 'browser': 'chrome', 'version': state['br'].version, 'locale': args.locale,
                   'variant': args.variant, **visits,
                   'textRatioAA2': harness.text_ratio(a, a2), 'textRatioAB': harness.text_ratio(a, b),
                   'pixAA2': harness.pixel_diff(a.get('shot'), a2.get('shot')),
                   'pixAB': harness.pixel_diff(a.get('shot'), b.get('shot'))}
            ab_diff.write(f'{args.out_dir}/diffs.jsonl', res, a, a2, b)
            with open(path, 'a') as f:
                f.write(json.dumps(harness.scrub_record(res), ensure_ascii=False) + '\n')
            print(r['idx'], r['class'], res['textRatioAA2'], res['textRatioAB'], res['pixAB'],
                  (b.get('extra') or {}).get('rewrites'), flush=True)

        await asyncio.gather(*(one(r) for r in rows))
        await state['br'].close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('browser', choices=['chrome'])
    ap.add_argument('locale')
    ap.add_argument('variant', choices=['B1', 'B2', 'B3', 'C1', 'C2', 'SU', 'SL'])
    ap.add_argument('pages', nargs='?')
    ap.add_argument('out_dir', nargs='?')
    ap.add_argument('--concurrency', type=int, default=4)
    ap.add_argument('--sanity', action='store_true')
    args = ap.parse_args()
    if args.sanity:
        async def s():
            async with async_playwright() as p:
                print(json.dumps(await sanity(p, args.locale, args.variant), ensure_ascii=False))
        asyncio.run(s())
    else:
        asyncio.run(run(args))


if __name__ == '__main__':
    main()
