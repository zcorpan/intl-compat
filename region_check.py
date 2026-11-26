"""Follow-ups to B3 and the `ar` case, from CLDR alone.

1. Region-keyed data: for each tag B3 drops (ab/cldr-table.json mainDrop), compare CLDR's region-keyed
   supplemental data (week, hour cycle, calendars, measurement, paper size, currency) for the tag's region
   and for the region the shorter tag maximizes to.
2. Likely-subtags traps: for each language (or language_Script) locale in common/main/, whether adding
   the likely-subtags region changes the data, as `ar` -> `ar-EG` does: the region's file has data, or its
   parent isn't the language.

usage: python3 region_check.py ~/git/unicode-org/cldr > region-report.txt   (writes region-pairs.json for
       region_browsers.py)
"""
import json, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REGION = re.compile(r'^([a-z]{2,3})(?:_([A-Z][a-z]{3}))?_([A-Z]{2}|\d{3})$')
BASE = re.compile(r'^([a-z]{2,3})(?:_([A-Z][a-z]{3}))?$')


def children(path):
    return [c.tag for c in ET.parse(path).getroot() if c.tag != 'identity']


def leaves(path):
    """'numbers/defaultNumberingSystem' etc.: the element paths a locale file sets."""
    out = set()
    def walk(e, p):
        kids = [c for c in e if c.tag != 'identity' and not c.tag.startswith('{')]
        if not kids and p:
            out.add(p)
        for c in kids:
            walk(c, f'{p}/{c.tag}' if p else c.tag)
    walk(ET.parse(path).getroot(), '')
    return out


def by_territory(root, tag, attr, terr_attr='territories', filt=None):
    out = {}
    for e in root.iter(tag):
        if filt and not filt(e):
            continue
        for t in e.get(terr_attr, '').split():
            out.setdefault(t, e.get(attr))
    return out


def main(cldr):
    sup = ET.parse(os.path.join(cldr, 'common/supplemental/supplementalData.xml')).getroot()
    parent = {}
    for pl in sup.iter('parentLocales'):
        if pl.get('component'):
            continue
        for p in pl.iter('parentLocale'):
            for l in p.get('locales').split():
                parent[l] = p.get('parent')
    likely = {e.get('from'): e.get('to') for e in
              ET.parse(os.path.join(cldr, 'common/supplemental/likelySubtags.xml')).getroot().iter('likelySubtag')}
    meta = open(os.path.join(cldr, 'common/supplemental/supplementalMetadata.xml')).read()
    default_content = set(re.search(r'<defaultContent locales="([^"]*)"', meta).group(1).split())
    main_dir = os.path.join(cldr, 'common/main')
    mains = {f[:-4] for f in os.listdir(main_dir) if f.endswith('.xml')}

    def region_of(loc):  # the region a locale ID resolves to: explicit, else from likely subtags
        p = loc.split('_')
        if len(p) > 1 and (re.fullmatch(r'[A-Z]{2}|\d{3}', p[-1])):
            return p[-1]
        m = likely.get(loc) or likely.get(p[0])
        return m.split('_')[-1] if m else None

    # Region-keyed supplemental data
    week = {k: by_territory(sup, k, 'day', filt=lambda e: not e.get('alt')) for k in ('firstDay', 'weekendStart', 'weekendEnd')}
    week['minDays'] = by_territory(sup, 'minDays', 'count')
    hours = {}
    for e in sup.iter('hours'):
        for r in e.get('regions').split():
            hours[r] = f"{e.get('preferred')} [{e.get('allowed')}]"
    cal = by_territory(sup, 'calendarPreference', 'ordering')
    meas = by_territory(sup, 'measurementSystem', 'type', filt=lambda e: not e.get('category'))
    temp = by_territory(sup, 'measurementSystem', 'type', filt=lambda e: e.get('category') == 'temperature')
    paper = by_territory(sup, 'paperSize', 'type')
    currency = {}
    for r in sup.iter('region'):
        cur = next((c.get('iso4217') for c in r.iter('currency') if not c.get('to') and c.get('tender') != 'false'), None)
        if cur:
            currency[r.get('iso3166')] = cur

    def regional(lang, region):
        def look(table, default_key='001'):
            return table.get(region, table.get(default_key))
        return {'firstDay': look(week['firstDay']), 'minDays': look(week['minDays']),
                'weekend': f"{look(week['weekendStart'])}-{look(week['weekendEnd'])}",
                'hours': hours.get(f'{lang}_{region}', hours.get(region, hours.get('001'))),
                'calendars': look(cal), 'measurement': look(meas), 'temperature': temp.get(region, look(meas)),
                'paper': look(paper), 'currency': currency.get(region)}

    # 1. B3's dropped tags
    table = json.load(open(os.path.join(HERE, 'ab', 'cldr-table.json')))['mainDrop']
    print('== 1. Region-keyed CLDR data, tag B3 drops vs the tag it reports ==')
    print(f'{len(table)} tag forms')
    diffs1 = []
    for tag, base in sorted(table.items()):
        lang = tag.split('-')[0]
        r, r0 = tag.split('-')[-1], region_of(base.replace('-', '_'))
        if r == r0:
            continue
        a, b = regional(lang, r), regional(lang, r0)
        d = {k: (a[k], b[k]) for k in a if a[k] != b[k]}
        diffs1.append((tag, base, r0, d))
    print(f'{len(diffs1)} tag forms whose region differs from the shorter tag\'s likely region '
          f'({sum(1 for x in diffs1 if x[3])} with region-keyed data that differs):')
    for tag, base, r0, d in diffs1:
        dc = 'default content' if tag.replace('-', '_') in default_content else 'not default content'
        print(f'  {tag} -> {base} (maximizes to {r0}; {dc}):', '; '.join(f'{k} {v[0]} vs {v[1]}' for k, v in d.items()) or 'same')
    counts = {}
    for *_, d in diffs1:
        for k in d:
            counts[k] = counts.get(k, 0) + 1
    print('  fields that differ (tag forms):', ', '.join(f'{k} {n}' for k, n in sorted(counts.items(), key=lambda x: -x[1])))

    # 2. Likely-subtags traps
    print()
    print('== 2. Languages whose likely-subtags region has its own data (like ar -> ar-EG) ==')
    traps, pairs2, plain = [], [], 0
    for base in sorted(mains):
        m = BASE.match(base)
        if not m or base == 'root':
            continue
        lang, script = m.groups()
        full = likely.get(base) or likely.get(lang)
        if not full:
            continue
        flang, fscript, region = full.split('_')
        if script and fscript != script and base in likely:
            fscript = likely[base].split('_')[1]
        withr = f'{base}_{region}'
        # Tag forms a browser reports for base+region: with the script, and without it when the
        # language alone maximizes to that script (zh-TW for zh_Hant_TW, but zh_Hans_CN -> zh-CN).
        tags = [withr.replace('_', '-')]
        if script and (likely.get(f'{lang}_{region}') or '').split('_')[1:2] == [script]:
            tags.append(f'{lang}-{region}')
        reasons = []
        if withr in mains:
            got = leaves(os.path.join(main_dir, withr + '.xml'))
            if got:
                reasons.append('main data: ' + ', '.join(sorted(got))[:300])
        if parent.get(withr) and parent[withr] != base:
            reasons.append(f'parent locale is {parent[withr]}')
        dc = sorted(l for l in default_content if re.fullmatch(re.escape(base) + r'_([A-Z]{2}|\d{3})', l))
        if dc and dc != [withr]:
            reasons.append(f"{base}'s default content is {', '.join(dc)}")
        for t in tags:
            pairs2.append({'tag': t, 'base': base.replace('_', '-'), 'trap': bool(reasons)})
        if reasons:
            traps.append((base, full, tags, reasons))
        else:
            plain += 1
    print(f'{len(traps)} of {len(traps) + plain} language locales:')
    for base, full, tags, reasons in traps:
        print(f'  {base} -> {full} ({" / ".join(tags)}):', '; '.join(reasons))

    pairs1 = [{'tag': t, 'base': b, 'regionDiffers': any(t == x[0] for x in diffs1)} for t, b in sorted(table.items())]
    json.dump({'drop': pairs1, 'likely': pairs2}, open(os.path.join(HERE, 'region-pairs.json'), 'w'), indent=0)


if __name__ == '__main__':
    main(os.path.expanduser(sys.argv[1]))
