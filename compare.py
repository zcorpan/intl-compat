# Loads each sampled page before (A, then A2 for page noise) and after (B) the change, and appends
# one JSON line per page to <out-dir>/results.jsonl. Pages already there are skipped, so rerun to resume.
# Usage: compare.py <chrome> <sample.jsonl> <out-dir> [<after-chrome>] [--concurrency N]
# Give <after-chrome> to compare a build that implements the change against an unmodified build.
import argparse, asyncio, json, os, sys
from playwright.async_api import async_playwright
import change, harness

ap = argparse.ArgumentParser()
ap.add_argument('chrome')
ap.add_argument('sample')
ap.add_argument('out_dir')
ap.add_argument('after_chrome', nargs='?')
ap.add_argument('--concurrency', type=int, default=4)
args = ap.parse_args()
os.makedirs(f'{args.out_dir}/shots', exist_ok=True)
results_path = f'{args.out_dir}/results.jsonl'
done = set()
if os.path.exists(results_path):
    done = {(r['page'], r['client']) for r in map(json.loads, open(results_path))}


async def sanity(before, after):
    if not change.SANITY_JS:
        print('no sanity check configured', flush=True)
        return
    url = harness.serve(harness.here('sanity')) + change.SANITY_PAGE
    for setup, br in (('before', before), ('after', after)):
        ctx = await br.new_context()
        for js in (change.INIT_JS, change.AFTER_INIT_JS if setup == 'after' else None):
            if js:
                await ctx.add_init_script(js)
        pg = await ctx.new_page()
        await pg.goto(url)
        await pg.wait_for_timeout(3000)  # like visits; polyfills and extensions may act after load
        if setup == 'after' and change.AFTER_LOAD_JS:
            await pg.evaluate(change.AFTER_LOAD_JS)
        ok = bool(await pg.evaluate(change.SANITY_JS)) == (setup == 'after')
        print(setup, 'sanity check', 'passed' if ok else 'FAILED', flush=True)
        await ctx.close()
        if not ok:
            sys.exit(1)


async def main():
    rows = [json.loads(l) for l in open(args.sample)]
    async with async_playwright() as p:
        exes = {'before': args.chrome, 'after': args.after_chrome or args.chrome}
        browsers = {s: await harness.launch(p, exe, s) for s, exe in exes.items()}
        print('before', browsers['before'].version, 'after', browsers['after'].version, flush=True)
        await sanity(browsers['before'], browsers['after'])
        sem = asyncio.Semaphore(args.concurrency)
        # A wedged or crashed browser fails every later visit: relaunch it after 3 timeouts in a row.
        timeouts = {s: 0 for s in exes}
        lock, retired = asyncio.Lock(), []

        async def close(br):
            try:
                await asyncio.wait_for(br.close(), 20)
            except Exception:
                pass

        async def relaunch(setup, old):
            async with lock:
                if browsers[setup] is not old:
                    return
                print('relaunching', setup, flush=True)
                browsers[setup] = await harness.launch(p, exes[setup], setup)
                timeouts[setup] = 0
            retired.append(old)

            async def close_later():
                await asyncio.sleep(95)  # other pages' visits on it finish or time out (guarded) first
                await close(old)
            asyncio.get_running_loop().create_task(close_later())

        async def one(idx, r):
            if (r['page'], r['client']) in done:
                return
            async with sem:
                visits = {}
                for tag, setup in (('A', 'before'), ('A2', 'before'), ('B', 'after')):
                    shot = f"{args.out_dir}/shots/{idx}-{tag}.png"
                    br = browsers[setup]
                    rec = await harness.guarded(harness.visit(br, r['page'], r['client'], setup, shot))
                    visits[tag] = rec
                    hung = rec.get('error', '').startswith('visit timed out')
                    timeouts[setup] = timeouts[setup] + 1 if hung else 0
                    if timeouts[setup] >= 3 or (hasattr(br, 'is_connected') and not br.is_connected()):
                        await relaunch(setup, br)
            a, a2, b = visits['A'], visits['A2'], visits['B']
            res = {'idx': idx, **r, **visits,
                   'textRatioAA2': harness.text_ratio(a, a2), 'textRatioAB': harness.text_ratio(a, b),
                   'pixAA2': harness.pixel_diff(a.get('shot'), a2.get('shot')),
                   'pixAB': harness.pixel_diff(a.get('shot'), b.get('shot'))}
            with open(results_path, 'a') as f:
                f.write(json.dumps(harness.scrub_record(res)) + '\n')
            print(idx, r['stratum'], res['textRatioAB'], res['pixAB'], flush=True)

        await asyncio.gather(*(one(i, r) for i, r in enumerate(rows)))
        for br in [*browsers.values(), *retired]:
            await close(br)

asyncio.run(main())
