"""Tidy A/B results for committing: move passback samples (formatted outputs: dates carry the
tester's time zone) into passback-samples.jsonl next to each results.jsonl (gitignored), and tidy
error strings.

usage: python3 ab_publish.py out-ab-*/results.jsonl
"""
import json, os, re, sys

B64 = re.compile(r'(base64,)\s*[A-Za-z0-9+/=]{40,}')


def tidy(e):
    # Errors were cut at 300 characters: drop the cut-off last token (a partial host reads as another
    # country's), and mask inline base64 payloads (fonts, images).
    if len(e) >= 300 and ' ' in e:
        e = e.rsplit(' ', 1)[0] + ' …'
    return B64.sub(r'\1<payload>', e)


for path in sys.argv[1:]:
    rows, samples = [], []
    for l in open(path):
        r = json.loads(l)
        pb = (r['B'].get('extra') or {}).get('passback') or {}
        if isinstance(pb.get('samples'), list):  # a count once moved, so rerunning is safe
            if pb['samples']:
                samples.append({'idx': r['idx'], 'locale': r['locale'], 'variant': r['variant'], 'samples': pb['samples']})
            pb['samples'] = len(pb['samples'])
        for t in ('A', 'A2', 'B'):
            v = r.get(t) or {}
            for k in ('pageErrors', 'console'):
                if isinstance(v.get(k), list):
                    v[k] = [tidy(e) if isinstance(e, str) else e for e in v[k]]
        rows.append(r)
    if samples:
        with open(os.path.join(os.path.dirname(path), 'passback-samples.jsonl'), 'a') as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + '\n')
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(path, len(rows), 'rows,', len(samples), 'with samples moved')
