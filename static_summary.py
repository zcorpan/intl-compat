"""Bucket static recall-check hits (out-detect/static.jsonl) by known library pattern."""
import collections, json, re, sys

BUCKETS = [
    ('intl-messageformat lazy defaultLocale', r'memoizedDefaultLocale|\.defaultLocale\s*=\s*new Intl\.NumberFormat\(\)\.resolvedOptions\(\)\.locale'),
    ('Sentry CultureContext (runs on error events)', r'locale:\s*\w+\.locale,\s*timezone:\s*\w+\.timeZone,\s*calendar'),
    ('Luxon system locale/zone', r'get type\(\)\{return"system"\}'),
    ('timeZone only (regex false positive)', r'resolvedOptions\(\)\.timeZone'),
]

rows = [json.loads(l) for l in open(sys.argv[1])]
pages = collections.Counter()
for r in rows:
    if not r['hits']:
        continue
    kinds = set()
    for h in r['hits']:
        s = h['snippet']
        k = next((name for name, pat in BUCKETS if re.search(pat, s)), 'other')
        kinds.add(k)
    # A page's most informative bucket: anything but the false positive wins.
    real = sorted(kinds - {'timeZone only (regex false positive)'})
    pages[real[0] if len(real) == 1 else ('several: ' + ', '.join(real) if real else 'timeZone only (regex false positive)')] += 1
print(f'{len(rows)} pages without detected reads; {sum(pages.values())} with static matches')
for k, v in pages.most_common():
    print(f'{v:4}  {k}')
