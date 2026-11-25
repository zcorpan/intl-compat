"""Flag A/B pages for review: B differs from A by more than A2 does (text, pixels), or only B has
errors, a failed load, or a missing challenge token.

usage: python3 ab_analyze.py out-ab-*/results.jsonl > out-ab/flagged.md
"""
import collections, json, re, sys

NUM = re.compile(r'\d+')
# Per-visit ids (blob URLs, UUIDs, hex tokens) would make the same error look new.
IDS = re.compile(r'blob:\S+|\b[0-9a-f]{8}-[0-9a-f-]{27}\b|\b(?=[a-z]*\d)[0-9a-f]{8,}\b', re.I)


def errs(v):
    # Page errors and console errors/warnings, ids and numbers masked (timestamps).
    return {NUM.sub('N', IDS.sub('ID', e)) for e in v.get('pageErrors', []) + [c for c in v.get('console', []) if c.startswith('error')]}


def tokens(v):
    x = v.get('extra') or {}
    return {k: sum(1 for n in x.get(k) or [] if n) for k in ('turnstile', 'hcaptcha', 'recaptcha')}


def flags(r):
    a, a2, b = r['A'], r['A2'], r['B']
    f = []
    if b.get('error') and not a.get('error'):
        f.append('B load error')
    if a.get('error') and a2.get('error') and b.get('error'):
        return ['all failed']
    if r['textRatioAB'] is not None and r['textRatioAA2'] is not None and r['textRatioAB'] < r['textRatioAA2'] - 0.02:
        f.append(f"text {r['textRatioAA2']}→{r['textRatioAB']}")
    if r['pixAB'] is not None and r['pixAA2'] is not None and r['pixAB'] > r['pixAA2'] + 0.02:
        f.append(f"pixels {r['pixAA2']}→{r['pixAB']}")
    new = errs(b) - errs(a) - errs(a2)
    if new:
        f.append(f'{len(new)} new errors')
    ta, ta2, tb = tokens(a), tokens(a2), tokens(b)
    for k in ta:
        if ta[k] and ta2[k] and not tb[k]:
            f.append(f'no {k} token')
    if a.get('status') != b.get('status') and a.get('status') == a2.get('status'):
        f.append(f"status {a.get('status')}→{b.get('status')}")
    return f


def main(paths):
    rows = [json.loads(l) for p in paths for l in open(p)]
    by = collections.defaultdict(list)
    for r in rows:
        by[(r['browser'], r['locale'], r['variant'])].append(r)
    for (br, loc, var), rs in sorted(by.items()):
        rewrote = sum(1 for r in rs if ((r['B'].get('extra') or {}).get('rewrites') or 0) > 0)
        fl = [(r, flags(r)) for r in rs]
        print(f'## {br} {loc} {var}: {len(rs)} pages, B rewrote a read on {rewrote}, '
              f'{sum(1 for _, f in fl if f == ["all failed"])} failed in all visits, '
              f'{sum(1 for _, f in fl if f and f != ["all failed"])} flagged\n')
        print('| idx | class | rewrites | flags |\n|---|---|---|---|')
        for r, f in sorted(fl, key=lambda x: x[0]['idx']):
            if f and f != ['all failed']:
                print(f"| {r['idx']} | {r['class']} | {(r['B'].get('extra') or {}).get('rewrites')} | {'; '.join(f)} |")
        print()


if __name__ == '__main__':
    main(sys.argv[1:])
