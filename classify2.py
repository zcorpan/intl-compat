"""Per-page classes and rates for the extended sample (queries/sample2.csv): random picks per rank
stratum, extrapolated to desktop root pages with an Intl counter, and the targeted picks (pages with the
LocaleInfoFunctions WebDX counter, pages with the Intl.Locale counter) as rates within those populations.

usage: python3 classify2.py out-detect2/results.jsonl out-detect2/groups.json out-detect2/classes.csv queries/sample2.csv
Results rows carry idx = row index in sample2.csv. Bounds: per-stratum Clopper-Pearson 95%, summed.
"""
import csv, json, math, sys, collections
from classify import ORDER


def cdf(k, n, p):  # binomial CDF in log space (sample sizes overflow floats otherwise)
    if p <= 0: return 1.0
    if p >= 1: return 0.0 if k < n else 1.0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq for i in range(k + 1)]
    m = max(terms)
    return min(1.0, math.exp(m) * sum(math.exp(t - m) for t in terms))


def cp(k, n, a=0.05):  # exact Clopper-Pearson bounds
    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - cdf(k - 1, n, p) < a / 2)
    upper = 1.0 if k == n else solve(lambda p: cdf(k, n, p) > a / 2)
    return lower, upper

STRATA = ['top1k', 'top10k', 'top100k', 'top1M', 'rest']
PICKS = {'random': 'stratum_intl_pages', 'locale_info': 'stratum_locale_info_pages', 'intl_locale': 'stratum_intl_locale_pages'}


def table(title, rows, pop, classes):
    n = collections.Counter(r['stratum'] for r in rows)
    by = collections.defaultdict(collections.Counter)
    for r in rows:
        if r['classes']:
            by[r['stratum']]['any read'] += 1
            by[r['stratum']][min(r['classes'], key=ORDER.index)] += 1
    strata = [s for s in STRATA if n[s]]
    total = sum(pop[s] for s in strata)
    print(f'\n{title}\n')
    print('| Class | ' + ' | '.join(f'{s} (n={n[s]})' for s in strata) + ' | Extrapolated % (95% bounds) |')
    print('|---|' + '---|' * (len(strata) + 1))
    for c in ['any read'] + classes:
        est = lo = hi = 0.0
        for s in strata:
            k = by[s][c]
            est += k / n[s] * pop[s]
            a, b = cp(k, n[s])
            lo, hi = lo + a * pop[s], hi + b * pop[s]
        print(f'| {c} | ' + ' | '.join(str(by[s][c]) for s in strata) +
              f' | {100 * est / total:.2f} ({100 * lo / total:.2f}–{100 * hi / total:.2f}) |')
    return total


def main(results, groups_path, classes_path, sample_path):
    groups = json.load(open(groups_path))
    cls = {int(r['group']): r['category'] for r in csv.DictReader(open(classes_path))}
    page_cls = collections.defaultdict(set)
    for i, g in enumerate(groups):
        for p in g['page_list']:
            page_cls[p].add(cls[i])
    sample = list(csv.DictReader(open(sample_path)))
    ok = []
    for l in open(results):
        r = json.loads(l)
        if r.get('error'):
            continue
        s = sample[r['idx']]
        ok.append({'stratum': s['stratum'], 'picks': s['pick'].split(), 'classes': page_cls.get(r['page'], set()), 'row': s})
    print('Desktop root pages, 2026-11-01 crawl, loaded without errors. Class = most significant use on the page.')
    for pick, col in PICKS.items():
        rows = [r for r in ok if pick in r['picks']]
        pop = {}
        for r in rows:
            pop[r['stratum']] = int(r['row'][col])
        title = {'random': 'Random pages with an Intl constructor counter, per rank stratum',
                 'locale_info': 'Pages with the LocaleInfoFunctions WebDX counter (Intl.Locale get*() info methods)',
                 'intl_locale': 'Pages with the Intl.Locale constructor counter'}[pick]
        total = table(title, rows, pop, ORDER)
        print(f'\nPopulation: {total:,} pages (' + ', '.join(f'{s} {pop[s]:,}' for s in STRATA if s in pop) + ').')


if __name__ == '__main__':
    main(*sys.argv[1:5])
