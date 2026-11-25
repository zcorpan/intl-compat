"""Group detection events by calling script and code position.

usage: python3 group.py out-detect/results.jsonl out-detect/groups.json [kinds]
kinds: comma-separated event kinds to group (default `locale`; e.g. `localeFrom,localeUse,localeInfo`).
Each locale read's caller is the first stack frame with a URL (native frames like JSON.stringify
are skipped). Script URLs are normalized (hashes, version numbers, per-site ids) so one library on
many sites forms one group; positions are kept per distinct script URL for the dossiers.
"""
import json, re, sys, collections

FRAME = re.compile(r'at (?:(.*?) \()?((?:https?|blob):[^\s)]+?|<anonymous>|[^\s()]+):(\d+):(\d+)\)?$')


def frames(stack):
    out = []
    for line in stack.split('\n'):
        m = FRAME.search(line.strip())
        if m:
            out.append({'fn': m.group(1) or '', 'url': m.group(2), 'line': int(m.group(3)), 'col': int(m.group(4))})
    return out


COLLAPSE = [
    (r'^challenges\.cloudflare\.com/cdn-cgi/challenge-platform/.*', 'challenges.cloudflare.com/(turnstile)'),
    (r'^[^/]*/cdn-cgi/challenge-platform/.*', '<site>/cdn-cgi/challenge-platform'),
    (r'^js(-[a-z]+\d)?\.hs-analytics\.net/.*', 'js.hs-analytics.net/analytics'),
    (r'^newassets\.hcaptcha\.com/.*', 'newassets.hcaptcha.com/hsw.js'),
    (r'^cdn\.tsyndicate\.com/.*', 'cdn.tsyndicate.com/sdk'),
]


def norm(url):
    u = re.sub(r'^https?://(www\.)?', '', url)
    for pat, rep in COLLAPSE:
        if re.match(pat, u):
            return rep
    u = re.sub(r'[0-9a-f]{8,}', '<h>', u, flags=re.I)
    u = re.sub(r'\b\d+(\.\d+)+\b', '<v>', u)
    u = re.sub(r'(?<=[/._-])[A-Za-z0-9_-]{20,}(?=[/._-]|$)', '<id>', u)
    u = re.sub(r'\d{4,}', '<n>', u)
    return u


def main(src, dst, kinds='locale'):
    kinds = set(kinds.split(','))
    groups = collections.defaultdict(lambda: {'pages': set(), 'svcs': collections.Counter(), 'args': collections.Counter(),
                                              'values': collections.Counter(), 'examples': []})
    pages = [json.loads(l) for l in open(src)]
    for r in pages:
        for e in r.get('events', []):
            if e['kind'] not in kinds:
                continue
            fs = [f for f in frames(e['stack']) if f['url'].startswith(('http', 'blob'))]
            top = fs[0] if fs else None
            key = norm(top['url']) if top else '(no url frame: inline/eval)'
            g = groups[key]
            g['pages'].add(r['page'])
            g['svcs'][e['svc'] if len(kinds) == 1 else e['kind'] + ':' + e['svc']] += 1
            g['args'][e['args'][:60]] += 1
            g['values'][e['value']] += 1
            if len(g['examples']) < 5 and all(x['page'] != r['page'] for x in g['examples']):
                g['examples'].append({'page': r['page'], 'svc': e['svc'], 'args': e['args'], 'frames': fs[:4],
                                      'href': e.get('href')})
    out = []
    for k, g in groups.items():
        out.append({'key': k, 'pages': len(g['pages']), 'page_list': sorted(g['pages']), 'svcs': dict(g['svcs']),
                    'args': dict(g['args']), 'values': dict(g['values']), 'examples': g['examples']})
    out.sort(key=lambda g: -g['pages'])
    json.dump(out, open(dst, 'w'), indent=1, ensure_ascii=False)
    n = sum(any(e['kind'] in kinds for e in r.get('events', [])) for r in pages)
    print(f'{len(pages)} pages, {n} with {"/".join(sorted(kinds))} events, {len(out)} groups')
    for g in out[:60]:
        print(g['pages'], g['key'][:90], dict(g['svcs']), list(g['args'])[:3])


if __name__ == '__main__':
    main(*sys.argv[1:4])
