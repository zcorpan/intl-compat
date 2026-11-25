"""Which services' resolved locales bot-defense, fraud and fallback-probe scripts read, and after which
constructor locales argument (none, `[]`, explicit), on the random picks of the extended sample.

usage: python3 bot_noarg.py out-detect2/results.jsonl out-detect2/groups.json out-detect2/classes.csv queries/sample2.csv > out-detect2/bot-noarg.md
A page counts for a category if any of its reads comes from a group of that category (not only its
most significant one). Extrapolated to desktop root pages: per-stratum rates weighted by the stratum's
Intl-counter pages, over all desktop root pages, with summed Clopper-Pearson bounds, as in classify2.py.
"""
import collections, csv, json, sys
from classify2 import cp, pct as fmt_rate
from group import frames, norm

SVCS = ['DateTimeFormat', 'NumberFormat', 'Collator', 'PluralRules', 'RelativeTimeFormat', 'ListFormat',
        'DisplayNames', 'Segmenter', 'DurationFormat']
CATS = ['bot-or-fraud', 'fallback-probe']


def arg_kind(a):
    return 'none' if a == 'none' else '[]' if a.replace(' ', '') == '[]' else 'explicit'


def main(results, groups_path, classes_path, sample_path):
    groups = json.load(open(groups_path))
    cls = {int(r['group']): r['category'] for r in csv.DictReader(open(classes_path))}
    cat_of = {g['key']: cls[i] for i, g in enumerate(groups)}
    sample = list(csv.DictReader(open(sample_path)))
    n, pop, root = collections.Counter(), {}, {}
    reads = {c: collections.defaultdict(lambda: collections.defaultdict(collections.Counter)) for c in CATS}
    for l in open(results):
        r = json.loads(l)
        s = sample[r['idx']]
        if r.get('error') or 'random' not in s['pick'].split():
            continue
        n[s['stratum']] += 1
        pop[s['stratum']] = int(s['stratum_intl_pages'])
        root[s['stratum']] = int(s['stratum_pages'])
        for e in r.get('events', []):
            if e['kind'] != 'locale':
                continue
            fs = [f for f in frames(e['stack']) if f['url'].startswith(('http', 'blob'))]
            c = cat_of.get(norm(fs[0]['url']) if fs else '(no url frame: inline/eval)')
            if c in reads:
                reads[c][r['page']][e['svc']][arg_kind(e['args'])] += 1
    print('Random sample pages (unweighted); share of pages whose bot or fraud script reads each service\'s '
          'resolved locale, by constructor locales argument.\n')
    stratum = {r['page']: sample[r['idx']]['stratum'] for r in map(json.loads, open(results))}
    weighted = {}
    for c in CATS:
        pages = reads[c]
        print(f'{c}: {len(pages)} pages\n')
        print('| Service | pages reading | % of these pages | no argument | `[]` | explicit |\n|---|---|---|---|---|---|')
        for svc in SVCS:
            rd = [p for p in pages if svc in pages[p]]
            k = collections.Counter()
            for p in rd:
                for a in pages[p][svc]:
                    k[a] += 1
            pct = lambda x: f'{100 * x / len(rd):.0f}%' if x else '0'
            share = f'{100 * len(rd) / len(pages):.0f}%' if rd else '0'
            print(f'| {svc} | {len(rd)} | {share} | ' +
                  (' | '.join(pct(k[a]) for a in ('none', '[]', 'explicit')) if rd else '| |') + ' |')
            weighted[(c, svc)] = rd
        weighted[(c, 'any')] = list(pages)
        print()

    def rate(ps):
        by = collections.Counter(stratum[p] for p in ps)
        d = sum(root.values()) / 100
        est = sum(by[s] / n[s] * pop[s] for s in n) / d
        lo = sum(cp(by[s], n[s])[0] * pop[s] for s in n) / d
        hi = sum(cp(by[s], n[s])[1] * pop[s] for s in n) / d
        return fmt_rate(est, lo, hi)
    print(f'\nExtrapolated to desktop root pages (2026-11-01, {sum(root.values()):,} pages, {sum(pop.values()):,} with an Intl counter), '
          'weighted by rank stratum:\n')
    print('| Bot or fraud script reads, after construction without a locales argument | % of desktop root pages (95% bounds) |\n|---|---|')
    for svc in ['any'] + SVCS[:-1]:
        ps = [p for p in weighted[('bot-or-fraud', svc)] if svc == 'any' or reads['bot-or-fraud'][p][svc]['none']]
        print(f'| {svc} | {rate(ps)} |')
    for svc in ('DateTimeFormat', 'Segmenter'):
        print(f'| fallback probe (`"ZZ"`/`[]`), {svc} | {rate(weighted[("fallback-probe", svc)])} |')

if __name__ == '__main__':
    main(*sys.argv[1:5])
