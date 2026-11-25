"""Build one dossier per group: beautified code around each stack frame that read the locale.

usage: .venv/bin/python dossier.py out-detect/results.jsonl out-detect/groups.json dossiers/
Dossiers hold untrusted page material (gitignored) for the read-only page-reviewer agents.
"""
import json, os, re, sys
import jsbeautifier
from group import frames

BEFORE, AFTER = 1500, 1500


def snippet(body, line, col):
    lines = body.split('\n')
    if line > len(lines):
        return None
    off = sum(len(l) + 1 for l in lines[:line - 1]) + col - 1
    a, b = max(0, off - BEFORE), min(len(body), off + AFTER)
    raw = body[a:off] + '/*>>>READ HERE<<<*/' + body[off:b]
    try:
        pretty = jsbeautifier.beautify(raw, {'indent_size': 2, 'max_preserve_newlines': 1})
    except Exception:
        pretty = raw
    return pretty[:9000]


def main(results, groups_path, outdir):
    pages = {json.loads(l)['page']: json.loads(l) for l in open(results)}
    groups = json.load(open(groups_path))
    os.makedirs(outdir, exist_ok=True)
    bodies_dir = os.path.join(outdir, 'bodies')
    for i, g in enumerate(groups):
        out = [f'# Group {i}: {g["key"]}', '',
               f'Pages: {g["pages"]}. Services: {g["svcs"]}. Constructor locales args: {g["args"]}. '
               f'Values read: {g["values"]}.', '']
        for ex in g['examples'][:3]:
            r = pages.get(ex['page'], {})
            out.append(f'## Example on {ex["page"]} ({ex["svc"]}, args {ex["args"]})')
            for f in ex['frames'][:3]:
                h = r.get('bodies', {}).get(f['url'])
                out.append(f'### frame {f["fn"] or "(anonymous)"} at {f["url"]}:{f["line"]}:{f["col"]}')
                p = os.path.join(bodies_dir, f'{h}.txt') if h else None
                if not p or not os.path.exists(p):
                    out.append('(body not captured)')
                    continue
                body = open(p, encoding='utf-8', errors='replace').read()
                if body.lstrip().startswith('<'):
                    out.append('(frame is in an HTML document; positions are relative to the document)')
                s = snippet(body, f['line'], f['col'])
                out += ['```js', s or '(position outside body)', '```']
            out.append('')
        open(os.path.join(outdir, f'group-{i:03d}.md'), 'w').write('\n'.join(out))
    print(f'{len(groups)} dossiers in {outdir}')


if __name__ == '__main__':
    main(*sys.argv[1:4])
