"""Text spans that change from A to B but not from A to A2 (page noise), for review. Written to a
gitignored file next to results.jsonl: page text can carry geo-targeted content."""
import difflib, json


def spans(x, y):
    out = set()
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes():
        if op != 'equal':
            out.add((x[max(0, i1 - 20):i2 + 20][:120], y[max(0, j1 - 20):j2 + 20][:120]))
    return out


def write(path, r, a, a2, b):
    ta, ta2, tb = a.get('text', ''), a2.get('text', ''), b.get('text', '')
    noise = {s for s, _ in spans(ta, ta2)}
    d = [list(p) for p in spans(ta, tb) if p[0] not in noise][:30]
    if d:
        with open(path, 'a') as f:
            f.write(json.dumps({'idx': r['idx'], 'locale': r.get('locale'), 'variant': r.get('variant'),
                                'browser': r.get('browser'), 'diff': d}, ensure_ascii=False) + '\n')
