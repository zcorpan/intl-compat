"""Combine group verdicts (out-detect/classes.csv) with detection results into per-page classes and
per-stratum rates, extrapolated to desktop root pages.

usage: python3 classify.py out-detect/results.jsonl out-detect/groups.json out-detect/classes.csv queries/sample.csv > out-detect/class-summary.md
A page's class is its most significant group's category (ORDER below). Bounds are exact
Clopper-Pearson 95% intervals on the sampled rate.
"""
import csv, json, math, sys, collections

ORDER = ['tag-sensitive', 'fallback-probe', 'passthrough', 'bot-or-fraud', 'fingerprint-id', 'analytics',
         'language-only', 'unclear']


def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def cp(k, n, a=0.05):
    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p) < a / 2)
    upper = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p) > a / 2)
    return lower, upper


def main(results, groups_path, classes_path, sample_path):
    groups = json.load(open(groups_path))
    cls = {int(r['group']): r for r in csv.DictReader(open(classes_path))}
    page_groups = collections.defaultdict(list)
    for i, g in enumerate(groups):
        for p in g['page_list']:
            page_groups[p].append(cls[i]['category'])
    rows = [json.loads(l) for l in open(results)]
    strata = {}
    for r in csv.DictReader(open(sample_path)):
        strata[r['stratum']] = (int(r['stratum_pages']), int(r['stratum_intl_pages']))
    by = collections.defaultdict(collections.Counter)
    n = collections.Counter()
    for r in rows:
        if r.get('error'):
            continue
        n[r['stratum']] += 1
        cats = page_groups.get(r['page'])
        if cats:
            by[r['stratum']][min(cats, key=ORDER.index)] += 1
            by[r['stratum']]['any read'] += 1
    order = ['top1k', 'top10k', 'top100k', 'top1M', 'rest']
    total_pages = sum(strata[s][0] for s in order)
    total_intl = sum(strata[s][1] for s in order)
    print('Desktop root pages, 2026-11-01 crawl; sample = pages hitting a Blink Intl constructor counter, '
          'loaded without errors. Class = most significant use on the page.\n')
    print('| Class | ' + ' | '.join(f'{s} (n={n[s]})' for s in order) + ' | Extrapolated % of Intl pages | % of all root pages |')
    print('|---|' + '---|' * (len(order) + 2))
    for c in ['any read'] + ORDER:
        cells, est = [], 0.0
        lo_sum = hi_sum = 0.0
        for s in order:
            k = by[s][c]
            cells.append(str(k))
            est += k / n[s] * strata[s][1]
            lo, hi = cp(k, n[s])
            lo_sum += lo * strata[s][1]
            hi_sum += hi * strata[s][1]
        print(f'| {c} | ' + ' | '.join(cells) +
              f' | {100 * est / total_intl:.1f} ({100 * lo_sum / total_intl:.1f}–{100 * hi_sum / total_intl:.1f}) | {100 * est / total_pages:.2f} |')
    print(f'\nStratum sizes (root pages / with an Intl counter): ' +
          ', '.join(f'{s} {strata[s][0]}/{strata[s][1]}' for s in order) +
          f'. Intervals: per-stratum Clopper–Pearson bounds summed (conservative).')


if __name__ == '__main__':
    main(*sys.argv[1:5])
