"""Recall check for the detection pass: load pages without detected reads and search their script and
document bodies for code that reads `locale` from a resolvedOptions() result.

usage: .venv/bin/python static_check.py <chrome> out-detect/results.jsonl out-detect/static.jsonl <n> <seed>
Takes a seeded sample of n pages that had no locale reads. A match is `resolvedOptions()` followed
within 300 characters by `.locale` or a `locale` destructuring; that is a superset (it also matches
`.timeZone` code next to unrelated `.locale` reads), so matches are reviewed, not counted blindly.
"""
import asyncio, hashlib, json, os, re, sys
from playwright.async_api import async_playwright
from harness import scrub

PAT = re.compile(rb'resolvedOptions\(\)(?:(?!resolvedOptions\(\)).){0,300}?(?:\.locale\b|\{[^}]{0,80}\blocale\b[^}]{0,80}\})', re.S)


async def visit(browser, url):
    ctx = await browser.new_context(viewport={'width': 1366, 'height': 768}, ignore_https_errors=True)
    page = await ctx.new_page()
    responses = []
    page.on('response', lambda r: r.request.resource_type in ('script', 'document') and responses.append(r))
    rec = {'hits': []}
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        try:
            await page.wait_for_load_state('load', timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)
        for r in responses[:400]:
            try:
                b = await asyncio.wait_for(r.body(), 10)
            except Exception:
                continue
            for m in list(PAT.finditer(b))[:3]:
                a = max(0, m.start() - 200)
                rec['hits'].append({'url': scrub(r.url), 'sha': hashlib.sha256(b).hexdigest()[:16],
                                    'snippet': scrub(b[a:m.end() + 100].decode('utf-8', 'replace'))})
    except Exception as e:
        rec['error'] = scrub(str(e).splitlines()[0])[:300]
    try:
        await asyncio.wait_for(ctx.close(), 15)
    except Exception:
        pass
    return rec


async def main(chrome, results, out, n, seed):
    rows = [json.loads(l) for l in open(results)]
    neg = [r for r in rows if not r.get('error') and not any(e['kind'] == 'locale' for e in r.get('events', []))]
    neg.sort(key=lambda r: hashlib.sha256((r['page'] + seed).encode()).hexdigest())
    todo = neg[:n]
    q = asyncio.Queue()
    for r in todo:
        q.put_nowait(r)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chrome, chromium_sandbox=True, ignore_default_args=['--disable-background-networking', '--disable-component-update'])
        with open(out, 'w') as f:
            async def worker():
                while not q.empty():
                    r = q.get_nowait()
                    try:
                        rec = await asyncio.wait_for(visit(b, r['page']), 90)
                    except asyncio.TimeoutError:
                        rec = {'error': 'timeout', 'hits': []}
                    f.write(json.dumps({'page': scrub(r['page']), 'stratum': r['stratum'], **rec}, ensure_ascii=False) + '\n')
                    f.flush()
            await asyncio.gather(*[worker() for _ in range(6)])
        await b.close()


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]))
