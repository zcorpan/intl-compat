"""Match dossier code around a locale read to already-classified groups, so a library bundled into many
first-party chunks inherits its verdict. Identifiers are normalized; property names and strings kept.

usage: python3 fingerprint.py <classified dossiers dir> <classes.csv> <new dossiers dir> > matches.json
"""
import csv, glob, json, re, sys

KW = set('new return var let const function if else typeof void this null true false undefined in of instanceof for while do try catch'.split())


def norm(code):
    code = re.sub(r'\s+', '', code)
    return re.sub(r'(?<![.\w$])[A-Za-z_$][\w$]*', lambda m: m.group(0) if m.group(0) in KW else 'x', code)


def windows(path, before=60, after=120):
    s = open(path, encoding='utf-8', errors='replace').read()
    out = []
    for m in re.finditer(r'/\*>>>READ HERE<<<\*/', s):
        a, b = s[max(0, m.start() - 400):m.start()], s[m.end():m.end() + 600]
        out.append(norm(a)[-before:] + '|' + norm(b)[:after])
    return out


def main(old_dir, classes, new_dir):
    cls = {int(r['group']): r for r in csv.DictReader(open(classes))}
    known = {}
    for f in glob.glob(f'{old_dir}/group-*.md'):
        g = int(re.search(r'(\d+)\.md$', f).group(1))
        for w in windows(f)[:1]:  # first frame of each example
            known.setdefault(w, set()).add(g)
    out = {}
    for f in sorted(glob.glob(f'{new_dir}/group-*.md')):
        ws = windows(f)
        hits = set()
        for w in ws:
            hits |= known.get(w, set())
        out[f] = sorted({(cls[g]['category'], cls[g]['vendor']) for g in hits if g in cls})
    json.dump(out, sys.stdout, indent=0)


if __name__ == '__main__':
    main(*sys.argv[1:4])
