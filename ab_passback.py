"""Per run: pages where B passed a rewritten tag back to Intl, and where that changed an output.

usage: python3 ab_passback.py out-ab-*/results.jsonl [--samples]
--samples prints the differing outputs (page text, timezone strings: terminal only, don't commit).
"""
import collections, json, sys


def main(paths, samples):
    by = collections.defaultdict(list)
    for p in paths:
        for l in open(p):
            r = json.loads(l)
            by[(r['browser'], r['locale'], r['variant'])].append(r)
    print('| run | pages | B rewrote | passed back | output differs | differing output visible |')
    print('|---|---|---|---|---|---|')
    hits = []
    for k, rs in sorted(by.items()):
        pb = [(r, (r['B'].get('extra') or {}).get('passback') or {}) for r in rs]
        rew = sum(1 for r in rs if ((r['B'].get('extra') or {}).get('rewrites') or 0) > 0)
        back = sum(1 for _, p in pb if p.get('calls'))
        diff = [(r, p) for r, p in pb if p.get('differ')]
        vis = sum(1 for r, _ in diff if (r['B'].get('extra') or {}).get('visible'))
        print(f'| {" ".join(k)} | {len(rs)} | {rew} | {back} | {len(diff)} | {vis} |')
        hits += [(k, r, p) for r, p in diff]
    print()
    for k, r, p in hits:
        whats = collections.Counter(s['what'] for s in p['samples']) if isinstance(p['samples'], list) else {'samples': p['samples']}
        print(' '.join(k), r['idx'], r['class'], f"differ {p['differ']}/{p['calls']}",
              'visible', (r['B'].get('extra') or {}).get('visible'), dict(whats))
        if samples and isinstance(p['samples'], list):
            for s in p['samples'][:4]:
                print('   ', json.dumps(s, ensure_ascii=False)[:240])


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if x != '--samples']
    main(a, '--samples' in sys.argv)
