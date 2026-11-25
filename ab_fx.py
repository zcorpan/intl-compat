"""ab.py's comparison in Firefox Nightly: Selenium + BiDi, a fresh session per visit.

The locale comes from WebDriver BiDi emulation.setLocaleOverride plus intl.accept_languages, which
gave the same values as the real configurations env_test.py could produce (-AppleLanguages doesn't
reach Firefox). ab/rewrite.js is a BiDi preload script (all frames). Measures the top frame only.

usage: .venv/bin/python ab_fx.py <locale> <variant> ab/pages.jsonl <out-dir> [--concurrency N]
       .venv/bin/python ab_fx.py <locale> <variant> --sanity
"""
import argparse, concurrent.futures, json, os, threading, time, warnings
from selenium import webdriver
import ab_diff, harness

FIREFOX = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
# Full page text (not the template's first 3000 characters): formatted dates sit anywhere.
FULL_TEXT = harness.MEASURE_JS = harness.MEASURE_JS.replace('.slice(0, 3000)', '.slice(0, 50000)')
REWRITE = open(harness.here('ab', 'rewrite.js')).read().replace(
    '/*CLDR_TABLE*/null', open(harness.here('ab', 'cldr-table.json')).read())
PASSBACK = open(harness.here('ab', 'passback.js')).read()
MEASURE = 'return (' + FULL_TEXT.strip() + ')()'
EXTRA = """return ((() => {
  const v = s => [...document.querySelectorAll(s)].map(e => (e.value || '').length);
  return { rewrites: window.__abRewrites ?? null, passback: window.__abPassback ?? null,
           visible: (() => { const p = window.__abPassback, t = document.body ? document.body.innerText : '';
             return p ? p.samples.filter(s => typeof s.got === 'string' && s.got.length > 1 && t.includes(s.got)).length : null; })(),
           defaultLocale: new Intl.DateTimeFormat().resolvedOptions().locale,
           turnstile: v('[name="cf-turnstile-response"]'), hcaptcha: v('[name="h-captcha-response"]'),
           recaptcha: v('[name="g-recaptcha-response"]') };
})())"""


def setvar(name, value):
    return f"Object.defineProperty(window, {json.dumps(name)}, {{ value: {json.dumps(value)} }});"


def session(locale, variant, setup):
    o = webdriver.FirefoxOptions()
    o.binary_location = FIREFOX
    o.enable_bidi = True
    o.add_argument('-headless')
    o.set_preference('intl.accept_languages', locale)
    for k in ('browser.safebrowsing.malware.enabled', 'browser.safebrowsing.phishing.enabled'):
        o.set_preference(k, True)  # Marionette turns Safe Browsing off
    o.accept_insecure_certs = True
    d = webdriver.Firefox(options=o)
    var = setvar('__abVariant', variant) if setup == 'after' else setvar('__abCount', variant)
    # A function declaration, not an IIFE: BiDi calls it. (pin() is the newer name; this one works.)
    warnings.simplefilter('ignore', DeprecationWarning)
    d.script.add_preload_script('() => {\n' + var + '\n' + REWRITE + '\n' + PASSBACK + '\n}')
    d.emulation.set_locale_override(locale=locale, user_contexts=['default'])
    d.set_window_size(1366, 768)
    iw, ih = d.execute_script('return [innerWidth, innerHeight]')
    d.set_window_size(1366 + 1366 - iw, 768 + 768 - ih)
    return d


def visit(locale, variant, setup, url, shot, wait=3):
    rec, errors = {}, []
    d = None
    try:
        d = session(locale, variant, setup)
        d.script.add_javascript_error_handler(lambda e: len(errors) < 10 and errors.append(harness.scrub(str(getattr(e, 'text', e)))[:300]))
        d.set_page_load_timeout(30)
        try:
            d.get(url)
        except Exception as e:
            if 'Timeout' not in type(e).__name__:
                raise
            rec['loadTimeout'] = True
        time.sleep(wait)
        m = d.execute_script(MEASURE)
        m['url'] = harness.scrub(m['url'])
        rec.update(m)
        rec['extra'] = d.execute_script(EXTRA)
        try:
            png = d.get_full_page_screenshot_as_png()
            open(shot, 'wb').write(png)
            from PIL import Image
            im = Image.open(shot)
            if im.height > 4000:
                im.crop((0, 0, im.width, 4000)).save(shot)
            rec['shot'] = shot
        except Exception as e:
            rec['shotError'] = harness.scrub(str(e).splitlines()[0])[:200]
    except Exception as e:
        rec['error'] = harness.scrub((str(e).splitlines() or [type(e).__name__])[0])[:300]
    finally:
        if d:
            try:
                d.quit()
            except Exception:
                pass
    rec['pageErrors'] = errors
    return rec


def run(args):
    os.makedirs(f'{args.out_dir}/shots', exist_ok=True)
    path = f'{args.out_dir}/results.jsonl'
    key = lambda r: (r['page'], r['locale'], r['variant'])
    done = {key(r) for r in map(json.loads, open(path))} if os.path.exists(path) else set()
    rows = [r for r in map(json.loads, open(args.pages)) if (r['page'], args.locale, args.variant) not in done]
    lock = threading.Lock()

    def one(r):
        visits = {}
        for tag, setup in (('A', 'before'), ('A2', 'before'), ('B', 'after')):
            shot = f"{args.out_dir}/shots/{r['idx']}-{args.locale}-{args.variant}-{tag}.png"
            visits[tag] = visit(args.locale, args.variant, setup, r['page'], shot)
        a, a2, b = visits['A'], visits['A2'], visits['B']
        res = {**r, 'browser': 'firefox', 'locale': args.locale, 'variant': args.variant, **visits,
               'textRatioAA2': harness.text_ratio(a, a2), 'textRatioAB': harness.text_ratio(a, b),
               'pixAA2': harness.pixel_diff(a.get('shot'), a2.get('shot')),
               'pixAB': harness.pixel_diff(a.get('shot'), b.get('shot'))}
        ab_diff.write(f'{args.out_dir}/diffs.jsonl', res, a, a2, b)
        with lock, open(path, 'a') as f:
            f.write(json.dumps(harness.scrub_record(res), ensure_ascii=False) + '\n')
        print(r['idx'], r['class'], res['textRatioAA2'], res['textRatioAB'], res['pixAB'],
              (b.get('extra') or {}).get('rewrites'), flush=True)

    with concurrent.futures.ThreadPoolExecutor(args.concurrency) as ex:
        for f in concurrent.futures.as_completed([ex.submit(one, r) for r in rows]):
            if f.exception():
                print('failed:', harness.scrub(str(f.exception()))[:200], flush=True)


def sanity(args):
    url = harness.serve(harness.here('ab')) + 'sanity.html'
    out = {}
    for setup in ('before', 'after'):
        d = session(args.locale, args.variant, setup)
        try:
            d.get(url)
            out[setup] = d.execute_script('return window.__sanity()')
            out[setup]['version'] = d.capabilities['browserVersion']
        finally:
            d.quit()
    print(json.dumps({'browser': 'firefox', 'locale': args.locale, 'variant': args.variant, **out}, ensure_ascii=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('locale')
    ap.add_argument('variant', choices=['B1', 'B2', 'B3', 'C1', 'C2', 'SU', 'SL'])
    ap.add_argument('pages', nargs='?')
    ap.add_argument('out_dir', nargs='?')
    ap.add_argument('--concurrency', type=int, default=5)
    ap.add_argument('--sanity', action='store_true')
    a = ap.parse_args()
    sanity(a) if a.sanity else run(a)
