"""Known-bad hosts for live runs: lists in security/ (gitignored), turned into launch settings that make
them unresolvable, plus a pre-check that drops sample pages on a listed host.

security/blocklist.txt: one host per line (known-bad hosts, threat-intel snapshots); security/urlhaus/*.txt: hosts-file
format (`0.0.0.0 host`). A listed host also blocks its subdomains.
usage: python3 blocklist.py <pages.csv|pages.jsonl>...   (prints listed pages and the host count)
"""
import csv, glob, json, os, re, sys
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = re.compile(r'^[a-z0-9.-]+\.[a-z0-9-]+$')


def hosts():
    out = set()
    for p in [os.path.join(HERE, 'security', 'blocklist.txt')] + glob.glob(os.path.join(HERE, 'security', 'urlhaus', '*.txt')):
        if not os.path.exists(p):
            continue
        for line in open(p, encoding='utf-8', errors='replace'):
            line = line.split('#', 1)[0].split()
            h = (line[-1] if line else '').lower().strip('.')
            if HOST.match(h) and h not in ('localhost', '0.0.0.0'):
                out.add(h)
    return sorted(out)


def chrome_args():
    hs = hosts()
    rules = ', '.join(f'MAP {h} ~NOTFOUND, MAP *.{h} ~NOTFOUND' for h in hs)
    return [f'--host-resolver-rules={rules}'] if hs else []


def firefox_prefs():
    # Resolves the hosts (not subdomains) to localhost, where nothing serves them.
    hs = hosts()
    return {'network.dns.localDomains': ','.join(hs)} if hs else {}


def listed(url, hs=None):
    hs = set(hosts()) if hs is None else hs
    h = (urlsplit(url).hostname or '').lower()
    parts = h.split('.')
    return any('.'.join(parts[i:]) in hs for i in range(len(parts) - 1))


if __name__ == '__main__':
    hs = set(hosts())
    print(f'{len(hs)} hosts')
    for path in sys.argv[1:]:
        rows = list(csv.DictReader(open(path))) if path.endswith('.csv') else [json.loads(l) for l in open(path)]
        bad = [r['page'] for r in rows if listed(r['page'], hs)]
        print(f'{path}: {len(bad)} of {len(rows)} pages on a listed host', *bad, sep='\n  ')
