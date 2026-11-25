"""Detection pass: load pages in Chrome with detect/trace.js and record reads of resolvedOptions().locale.

usage: .venv/bin/python detect.py <chrome> <sample.csv> <out.jsonl> [--concurrency N] [--limit N]
       .venv/bin/python detect.py <chrome> --selftest
Resumes: pages already in out.jsonl are skipped.
"""
import argparse, asyncio, csv, hashlib, json, os, sys, time
from playwright.async_api import async_playwright
import re
from harness import scrub, serve, here

# Drop query strings and fragments from stack frame URLs but keep the :line:col position.
FRAME_URL = re.compile(r'((?:https?|blob):[^\s?#;()]+)[?#;][^\s()]*?(:\d+:\d+)(?=\)|$)', re.M)


def scrub_stack(s):
    return scrub(FRAME_URL.sub(r'\1\2', s))

TRACE = open(here('detect', 'trace.js')).read()
# Bodies of scripts and documents whose code read the locale, by sha256; untrusted page material,
# gitignored, only for the code-review dossiers.
BODIES = here('dossiers', 'bodies')
STACK_URL = re.compile(r'\(?((?:https?|blob):[^\s()]+?):\d+:\d+\)?$', re.M)
CALLS_JS = '() => window.__intlTraceCalls ? {...window.__intlTraceCalls} : null'


async def visit(browser, url, wait=3000):
    ctx = await browser.new_context(viewport={'width': 1366, 'height': 768}, ignore_https_errors=True)
    events, raw_urls, responses = [], set(), {}

    def on_event(source, ev):
        if isinstance(ev, dict) and len(events) < 300:
            if ev.get('kind') == 'locale':
                raw_urls.update(STACK_URL.findall(ev.get('stack', ''))[:4])
            ev = {k: (scrub_stack(v) if k == 'stack' else scrub(v))[:2000] if isinstance(v, str) else v
                  for k, v in ev.items()}
            events.append(ev)
    await ctx.expose_binding('__intlTrace', on_event)
    await ctx.add_init_script(TRACE)
    page = await ctx.new_page()
    rec = {}
    errors = []
    page.on('pageerror', lambda e: len(errors) < 10 and errors.append(scrub(str(e))[:300]))
    page.on('response', lambda r: r.request.resource_type in ('script', 'document') and
            len(responses) < 2000 and responses.setdefault(r.url, r))
    try:
        resp = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        rec['status'] = resp.status if resp else None
        try:
            await page.wait_for_load_state('load', timeout=15000)
        except Exception:
            rec['loadTimeout'] = True
        await page.wait_for_timeout(wait)
        calls = []
        for fr in page.frames[:20]:
            try:
                c = await asyncio.wait_for(fr.evaluate(CALLS_JS), 5)
                if c:
                    calls.append(c)
            except Exception:
                pass
        rec['calls'] = calls
        bodies = {}
        for u in list(raw_urls)[:20]:
            r = responses.get(u)
            if not r:
                continue
            try:
                b = await asyncio.wait_for(r.body(), 10)
            except Exception:
                continue
            h = hashlib.sha256(b).hexdigest()[:16]
            os.makedirs(BODIES, exist_ok=True)
            path = os.path.join(BODIES, h + '.txt')
            if not os.path.exists(path):
                open(path, 'wb').write(b)
            bodies[scrub_stack(u + ':1:1')[:-4]] = h
        rec['bodies'] = bodies
    except Exception as e:
        rec['error'] = scrub(str(e).splitlines()[0])[:300]
    rec['events'] = events
    rec['pageErrors'] = errors
    try:
        await asyncio.wait_for(ctx.close(), 15)
    except Exception:
        pass
    return rec


async def guarded(coro, seconds=75):
    try:
        return await asyncio.wait_for(coro, seconds)
    except asyncio.TimeoutError:
        return {'error': f'visit timed out after {seconds}s', 'events': []}


async def run(chrome, rows, out, concurrency):
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['idx'] for l in open(out) if l.strip()}
    todo = [r for r in rows if r['idx'] not in done]
    print(f'{len(todo)} to do, {len(done)} done', file=sys.stderr)
    q = asyncio.Queue()
    for r in todo:
        q.put_nowait(r)
    t0 = time.time()
    n = 0
    async with async_playwright() as p:
        state = {'browser': await p.chromium.launch(executable_path=chrome), 'fails': 0}
        lock = asyncio.Lock()
        with open(out, 'a') as f:
            async def worker():
                nonlocal n
                while not q.empty():
                    r = q.get_nowait()
                    rec = await guarded(visit(state['browser'], r['page']))
                    async with lock:
                        # page masked like other output (country hosts); idx is the row in the sample
                        f.write(json.dumps({'idx': r['idx'], 'page': scrub(r['page']), 'rank': int(r['rank']), 'stratum': r['stratum'],
                                            'intl': r['intl'], **rec}, ensure_ascii=False) + '\n')
                        f.flush()
                        n += 1
                        if n % 50 == 0:
                            print(f'{n}/{len(todo)} {n / (time.time() - t0) * 60:.0f}/min', file=sys.stderr)
                        state['fails'] = state['fails'] + 1 if 'timed out' in rec.get('error', '') or \
                            'closed' in rec.get('error', '') else 0
                        if state['fails'] >= 4 or not state['browser'].is_connected():
                            print('relaunching browser', file=sys.stderr)
                            try:
                                await state['browser'].close()
                            except Exception:
                                pass
                            state['browser'] = await p.chromium.launch(executable_path=chrome)
                            state['fails'] = 0
            await asyncio.gather(*[worker() for _ in range(concurrency)])
        await state['browser'].close()


async def selftest(chrome):
    base = serve(here('detect'))
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chrome)
        rec = await visit(b, base + 'test.html', wait=500)
        ctx = await b.new_context()
        pg = await ctx.new_page()
        await pg.goto(base + 'test.html')
        plain = await pg.title()
        ctx2 = await b.new_context()
        await ctx2.add_init_script(TRACE)
        pg2 = await ctx2.new_page()
        await pg2.goto(base + 'test.html')
        traced = await pg2.title()
        await b.close()
    for e in rec['events']:
        print(e['kind'], e['svc'], e['args'], e['value'], e['stack'].split('\n')[0].strip())
    print('calls', rec.get('calls'))
    print('plain ', plain)
    print('traced', traced)
    print('same page-visible results:', plain == traced)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('chrome')
    ap.add_argument('sample', nargs='?')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--concurrency', type=int, default=8)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        asyncio.run(selftest(a.chrome))
    else:
        rows = [dict(r, idx=i) for i, r in enumerate(csv.DictReader(open(a.sample)))][:a.limit]
        asyncio.run(run(a.chrome, rows, a.out, a.concurrency))
