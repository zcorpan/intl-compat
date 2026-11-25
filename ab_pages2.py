"""Page lists for Henri's variants, from the extended detection (out-detect2) and the Luxon 10k pages.

usage: python3 ab_pages2.py   (writes ab/pages-b3.jsonl, ab/pages-collator.jsonl, ab/pages-segmenter.jsonl)
B3: every page whose most significant class is tag-sensitive, unclear or language-only, pages with
Intl.Locale uses the reviewers couldn't settle, plus seeded samples of passthrough pages and of the Luxon
pages found by the 10k body scan (idx offset by 100000). Collator: pages reading a Collator's locale (all
but Turnstile, plus a seeded 30 Turnstile pages). Segmenter: every page reading a Segmenter's locale.
Pages on a block-listed host are left out.
"""
import csv, hashlib, json, collections
import blocklist
from classify import ORDER

SEED = 'intl-compat-ab2'
key = lambda p: hashlib.sha256((SEED + p).encode()).hexdigest()
groups = json.load(open('out-detect2/groups.json'))
cls = {int(r['group']): r for r in csv.DictReader(open('out-detect2/classes.csv'))}
idx = {}
for l in open('out-detect2/results.jsonl'):
    r = json.loads(l)
    if not r.get('error'):
        idx[r['page']] = (r['idx'], r['stratum'])
page_groups = collections.defaultdict(list)
for i, g in enumerate(groups):
    for p in g['page_list']:
        page_groups[p].append(i)
bad = set(blocklist.hosts())


def rec(p, klass, gs):
    i, s = idx[p]
    return {'idx': i, 'page': p, 'client': 'desktop', 'stratum': s, 'class': klass, 'groups': gs}


def best(p):
    return min((cls[g]['category'] for g in page_groups[p]), key=ORDER.index)


pages = [p for p in page_groups if p in idx and not blocklist.listed(p, bad)]
b3 = [rec(p, best(p), page_groups[p]) for p in pages if best(p) in ('tag-sensitive', 'unclear', 'language-only')]
locale = json.load(open('out-detect2/groups-locale.json'))
unsettled = {'asset.fwcdn3.com', 'passport.amazon.jobs', 'cloudfront.net/release/web-hornet', 'd18x2fcr51hnc9.cloudfront.net',
             'sky.blackbaudcdn.net', 'adsagentclientafd', 'static.matterport.com'}
seen = {r['page'] for r in b3}
for g in locale:
    if any(u in g['key'] for u in unsettled):
        for p in g['page_list']:
            if p in idx and p not in seen and not blocklist.listed(p, bad):
                b3.append(rec(p, 'locale-unsettled', page_groups.get(p, [])))
                seen.add(p)
passthrough = sorted((p for p in pages if best(p) == 'passthrough' and p not in seen), key=key)[:60]
b3 += [rec(p, 'passthrough', page_groups[p]) for p in passthrough]
lux = sorted({r['page'] for r in csv.DictReader(open('queries/luxon_10k.csv'))} - seen - set(passthrough), key=key)
lux = [p for p in lux if not blocklist.listed(p, bad)][:40]
b3 += [{'idx': 100000 + n, 'page': p, 'client': 'desktop', 'stratum': 'luxon-10k', 'class': 'luxon-static', 'groups': []}
       for n, p in enumerate(lux)]

coll, seg = [], []
turnstile = [i for i, g in enumerate(groups) if g['key'] == 'challenges.cloudflare.com/(turnstile)']
for p in pages:
    svcs = {s for g in page_groups[p] for s in groups[g]['svcs']}
    gs = page_groups[p]
    if 'Segmenter' in svcs:
        seg.append(rec(p, best(p), gs))
    if 'Collator' in svcs and any('Collator' in groups[g]['svcs'] and g not in turnstile for g in gs):
        coll.append(rec(p, best(p), gs))
ts = sorted((p for p in pages if any(g in turnstile for g in page_groups[p]) and p not in {r['page'] for r in coll}), key=key)[:30]
coll += [rec(p, 'bot-or-fraud', page_groups[p]) for p in ts]

for name, rows in (('b3', b3), ('collator', coll), ('segmenter', seg)):
    with open(f'ab/pages-{name}.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    print(name, len(rows), collections.Counter(r['class'] for r in rows))
