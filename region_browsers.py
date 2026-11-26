"""What Intl gives for each pair in region-pairs.json (region_check.py) in Chrome Canary and Firefox Nightly:
formatted output, resolvedOptions() and Intl.Locale getters for the tag and for the shorter tag, and
which differ. Runs on about:blank (no network).

usage: .venv/bin/python region_browsers.py > region-browsers.txt   (writes region-browsers.json)
"""
import asyncio, json, os
from playwright.async_api import async_playwright
from selenium import webdriver
import blocklist

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
FIREFOX = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
UPDATES = os.path.expanduser('~/Library/Caches/Mozilla/updates/Applications/Firefox Nightly/updates/0')

JS = r"""
(pairs) => {
  const dates = [new Date(Date.UTC(2024, 0, 7, 15, 4, 5)), new Date(Date.UTC(2024, 6, 1, 3, 4, 5))];
  const tz = { timeZone: 'UTC' };
  const safe = f => { try { const v = f(); return v === undefined ? 'undefined' : JSON.stringify(v); } catch (e) { return 'error: ' + e.name; } };
  const fp = tag => {
    const o = {};
    const dtf = opts => new Intl.DateTimeFormat(tag, { ...tz, ...opts });
    const fmt = (name, opts) => { o['fmt dtf ' + name] = safe(() => dates.map(d => dtf(opts).format(d))); };
    fmt('default', {});
    for (const s of ['full', 'long', 'medium', 'short']) { fmt('date ' + s, { dateStyle: s }); fmt('time ' + s, { timeStyle: s }); }
    fmt('hour', { hour: 'numeric' });
    fmt('hour minute', { hour: 'numeric', minute: 'numeric' });
    fmt('weekday month', { weekday: 'long', month: 'long', day: 'numeric' });
    fmt('dayPeriod', { hour: 'numeric', dayPeriod: 'short' });
    o['fmt toLocaleString'] = safe(() => dates.map(d => d.toLocaleString(tag, tz)));
    o['fmt dtf range'] = safe(() => dtf({ dateStyle: 'medium' }).formatRange(dates[0], dates[1]));
    const nf = (name, opts, v) => { o['fmt nf ' + name] = safe(() => new Intl.NumberFormat(tag, opts).format(v)); };
    nf('default', {}, 1234567.891);
    nf('percent', { style: 'percent' }, 0.256);
    nf('compact', { notation: 'compact' }, 1234567);
    nf('compact long', { notation: 'compact', compactDisplay: 'long' }, 1234567);
    nf('EUR', { style: 'currency', currency: 'EUR' }, 1234.5);
    nf('USD', { style: 'currency', currency: 'USD' }, 1234.5);
    nf('unit', { style: 'unit', unit: 'kilometer-per-hour', unitDisplay: 'long' }, 12);
    nf('small', {}, 1234);
    o['fmt rtf'] = safe(() => { const r = new Intl.RelativeTimeFormat(tag, { numeric: 'auto' }); return [r.format(-1, 'day'), r.format(-5, 'day'), r.format(3, 'hour')]; });
    o['fmt list'] = safe(() => new Intl.ListFormat(tag).format(['a', 'b', 'c']));
    o['fmt plural'] = safe(() => { const p = new Intl.PluralRules(tag), q = new Intl.PluralRules(tag, { type: 'ordinal' }); return [0, 1, 2, 3, 5, 11, 1.5].map(n => p.select(n) + '/' + q.select(n)); });
    o['fmt displaynames'] = safe(() => { const d = new Intl.DisplayNames(tag, { type: 'region' }), l = new Intl.DisplayNames(tag, { type: 'language' }); return [d.of('US'), d.of('DE'), l.of('fr'), l.of('en-US')]; });
    o['fmt collator'] = safe(() => ['ch', 'c', 'cz', 'ä', 'a', 'z', 'ö', 'o', 'å'].sort(new Intl.Collator(tag).compare));
    const ro = safe(() => { const r = new Intl.DateTimeFormat(tag, { hour: 'numeric' }).resolvedOptions(); return [r.hourCycle, r.calendar, r.numberingSystem]; });
    o['opts dtf hourCycle/calendar/numberingSystem'] = ro;
    o['opts nf numberingSystem'] = safe(() => new Intl.NumberFormat(tag).resolvedOptions().numberingSystem);
    let L = null; try { L = new Intl.Locale(tag); } catch (e) {}
    const g = (name, m, prop) => { o['locale ' + name] = safe(() => L[m] ? L[m]() : L[prop]); };
    g('weekInfo', 'getWeekInfo', 'weekInfo');
    g('hourCycles', 'getHourCycles', 'hourCycles');
    g('calendars', 'getCalendars', 'calendars');
    g('collations', 'getCollations', 'collations');
    g('numberingSystems', 'getNumberingSystems', 'numberingSystems');
    g('textInfo', 'getTextInfo', 'textInfo');
    // Only the count: zone names would match .publish-terms (the tester's city).
    o['locale timeZones'] = safe(() => { const z = L.getTimeZones ? L.getTimeZones() : L.timeZones; return z && z.length; });
    o.resolved = safe(() => new Intl.DateTimeFormat(tag).resolvedOptions().locale);
    return o;
  };
  return pairs.map(p => {
    const a = fp(p.tag), b = fp(p.base);
    const diff = Object.keys(a).filter(k => k !== 'resolved' && a[k] !== b[k]).map(k => [k, a[k], b[k]]);
    return { ...p, resolvedTag: a.resolved, resolvedBase: b.resolved, diff };
  });
}
"""


async def chrome(pairs):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path=CHROME, chromium_sandbox=True)
        pg = await br.new_page()
        await pg.goto('about:blank')
        out = await pg.evaluate(JS, pairs)
        version = br.version
        await br.close()
    return version, out


def firefox(pairs):
    if os.path.isdir(UPDATES) and os.listdir(UPDATES):
        raise SystemExit(f'a Firefox update is staged in {UPDATES}; apply it (restart Firefox) before running')
    o = webdriver.FirefoxOptions()
    o.binary_location = FIREFOX
    o.add_argument('-headless')
    for k in ('browser.safebrowsing.malware.enabled', 'browser.safebrowsing.phishing.enabled'):
        o.set_preference(k, True)
    for k, v in blocklist.firefox_prefs().items():
        o.set_preference(k, v)
    d = webdriver.Firefox(options=o)
    try:
        d.get('about:blank')
        out = d.execute_script(f'return ({JS})(arguments[0])', pairs)
        version = d.capabilities.get('browserVersion') + ' ' + str(d.capabilities.get('moz:buildID', ''))
    finally:
        d.quit()
    return version, out


def report(name, version, out):
    print(f'== {name} {version} ==')
    for group in ('drop', 'likely'):
        rows = [r for r in out if r['group'] == group]
        differ = [r for r in rows if r['diff']]
        print(f'-- {group}: {len(differ)} of {len(rows)} pairs differ')
        counts = {}
        for r in differ:
            for k, *_ in r['diff']:
                counts[k] = counts.get(k, 0) + 1
        print('   keys (pairs):', ', '.join(f'{k} {n}' for k, n in sorted(counts.items(), key=lambda x: -x[1])) or 'none')
        for r in differ:
            keys = [k for k, *_ in r['diff']]
            print(f"   {r['tag']} -> {r['base']} (resolve to {r['resolvedTag']} / {r['resolvedBase']}): {', '.join(keys)}")
            for k, a, b in r['diff']:
                if k != 'locale timeZones':
                    print(f'      {k}: {a[:200]}  vs  {b[:200]}')


def main():
    pairs = json.load(open(os.path.join(HERE, 'region-pairs.json')))
    flat = [{**p, 'group': g} for g in ('drop', 'likely') for p in pairs[g]]
    results = {}
    cv, co = asyncio.run(chrome(flat))
    results['chrome'] = {'version': cv, 'pairs': co}
    fv, fo = firefox(flat)
    results['firefox'] = {'version': fv, 'pairs': fo}
    json.dump(results, open(os.path.join(HERE, 'region-browsers.json'), 'w'), indent=0, ensure_ascii=False)
    for name, r in results.items():
        report(name, r['version'], r['pairs'])


if __name__ == '__main__':
    main()
