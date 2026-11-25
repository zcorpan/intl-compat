"""Pages for the A/B comparison: every page whose most significant use is passthrough, tag-sensitive,
fallback-probe or unclear, plus a seeded sample of bot-or-fraud pages (challenge outcomes).

usage: python3 ab_pages.py [N_BOT] > ab/pages.jsonl
"""
import csv, hashlib, json, sys, collections
from classify import ORDER

N_BOT = int(sys.argv[1]) if len(sys.argv) > 1 else 30
groups = json.load(open('out-detect/groups.json'))
cls = {int(r['group']): r for r in csv.DictReader(open('out-detect/classes.csv'))}
page_groups = collections.defaultdict(list)
for i, g in enumerate(groups):
    for p in g['page_list']:
        page_groups[p].append(i)
rows = {r['page']: r for r in map(json.loads, open('out-detect/results.jsonl'))}
out, bots = [], []
for page, gs in page_groups.items():
    top = min(gs, key=lambda i: ORDER.index(cls[i]['category']))
    c = cls[top]['category']
    r = rows[page]
    rec = {'idx': r['idx'], 'page': page, 'client': 'desktop', 'stratum': r['stratum'], 'class': c,
           'groups': sorted(gs)}
    if c in ('passthrough', 'tag-sensitive', 'fallback-probe', 'unclear'):
        out.append(rec)
    elif c == 'bot-or-fraud':
        bots.append(rec)
bots.sort(key=lambda r: hashlib.sha256(('intl-compat-ab' + r['page']).encode()).hexdigest())
for r in sorted(out + bots[:N_BOT], key=lambda r: r['idx']):
    print(json.dumps(r))
