"""Derive the region-drop tables for ab/rewrite.js from a CLDR checkout, and report the checks behind them.

usage: python3 cldr_table.py ~/git/unicode-org/cldr > cldr-report.txt   (writes ab/cldr-table.json)
mainDrop: locales whose common/main/<lang>[_<Script>]_<REGION>.xml has nothing but <identity> and whose
parent is the same locale without the region (no parentLocale override), keyed by the tag forms a browser
reports (zh-Hant-TW and zh-TW) and mapped to the tag without the region (keeping the script when the
language alone would maximize to another script: zh-TW -> zh-Hant, zh-CN -> zh).
collatorDrop / collatorHant: Henri's Collator tags, each checked against common/collation/.
"""
import json, os, re, sys
import xml.etree.ElementTree as ET

COLLATOR_DROP = {'en-US': 'en', 'en-GB': 'en', 'ar-SA': 'ar', 'zh-CN': 'zh', 'zh-Hans-CN': 'zh-Hans'}
COLLATOR_HANT = ['zh-TW', 'zh-HK', 'zh-Hant-TW', 'zh-Hant-HK']
REGION = re.compile(r'^([a-z]{2,3})(?:_([A-Z][a-z]{3}))?_([A-Z]{2}|\d{3})$')


def children(path):
    root = ET.parse(path).getroot()
    return [c.tag for c in root if c.tag != 'identity']


def main(cldr):
    sup = open(os.path.join(cldr, 'common/supplemental/supplementalData.xml')).read()
    block = re.search(r'<parentLocales>(.*?)</parentLocales>', sup, re.S).group(1)
    parent = {}
    for p, locs in re.findall(r'parent="([^"]+)"[^>]*locales="([^"]+)"', block):
        for l in locs.split():
            parent[l] = p
    cblock = re.search(r'<parentLocales component="collations">(.*?)</parentLocales>', sup, re.S).group(1)
    cparent = {l: p for p, locs in re.findall(r'parent="([^"]+)"[^>]*locales="([^"]+)"', cblock) for l in locs.split()}
    likely = dict(re.findall(r'<likelySubtag from="([^"]+)" to="([^"]+)"',
                             open(os.path.join(cldr, 'common/supplemental/likelySubtags.xml')).read()))
    meta = open(os.path.join(cldr, 'common/supplemental/supplementalMetadata.xml')).read()
    default_content = set(re.search(r'<defaultContent locales="([^"]*)"', meta).group(1).split())
    main_dir = os.path.join(cldr, 'common/main')
    coll_dir = os.path.join(cldr, 'common/collation')
    colls = {f[:-4] for f in os.listdir(coll_dir) if f.endswith('.xml')}

    drop, flagged, not_dc, files = {}, [], [], 0
    for f in sorted(os.listdir(main_dir)):
        loc = f[:-4]
        m = REGION.match(loc)
        if not m or children(os.path.join(main_dir, f)):
            continue
        lang, script, region = m.groups()
        base = lang + ('_' + script if script else '')
        if parent.get(loc, base) != base:
            flagged.append(f'{loc}: empty but parent is {parent[loc]}')
            continue
        files += 1
        if loc not in default_content:
            not_dc.append(loc)
        lang_script = likely.get(lang, '').split('_')[1:2]
        to = base.replace('_', '-')
        if script and lang_script == [script]:
            to = lang  # zh_Hans_CN -> zh for the short form below
        drop[loc.replace('_', '-')] = base.replace('_', '-')
        if script:  # the form without the script, as Chrome reports it (zh-TW)
            short = f'{lang}_{region}'
            if likely.get(short, likely.get(lang, '')).split('_')[1:2] == [script]:
                drop[f'{lang}-{region}'] = to

    # Collation: a region "does nothing" if no collation file applies to it beyond its base's (en_US.xml is empty).
    def coll_chain(loc):
        out = []
        while loc and loc != 'root':
            if loc in colls:
                out.append(loc)
            loc = cparent.get(loc) or ('_'.join(loc.split('_')[:-1]) if '_' in loc else 'root')
        return out
    def effective(tag):  # first collation file with data on the lookup chain (empty files inherit)
        loc = tag.replace('-', '_')
        parts = loc.split('_')
        if len(parts) == 2 and re.fullmatch(r'[A-Z]{2}|\d{3}', parts[1]):  # zh_TW -> zh_Hant_TW, as ICU does
            s = likely.get(loc, likely.get(parts[0], '')).split('_')[1:2]
            if s and s != likely.get(parts[0], '').split('_')[1:2]:
                loc = f'{parts[0]}_{s[0]}_{parts[1]}'
        for c in coll_chain(loc):
            if c != 'en_US_POSIX' and children(os.path.join(coll_dir, c + '.xml')):
                return c
        return 'root'
    def coll_differs(tag, base):
        return effective(tag) != effective(base), effective(tag), effective(base)

    checks = {}
    for tag, base in COLLATOR_DROP.items():
        checks[tag] = coll_differs(tag, base)
    for tag in COLLATOR_HANT:
        checks[tag] = coll_differs(tag, 'zh-Hant')
    hidden = [(t, b, coll_differs(t, b)) for t, b in drop.items() if coll_differs(t, b)[0]]

    json.dump({'mainDrop': drop, 'collatorDrop': COLLATOR_DROP, 'collatorHant': COLLATOR_HANT},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ab', 'cldr-table.json'), 'w'),
              indent=0, sort_keys=True)
    print(f'mainDrop: {files} empty region files ({len(drop)} tag forms); '
          f'{len(not_dc)} of the empty files are not default content locales: {" ".join(not_dc)}')
    print('empty region files with a non-truncation parent (not dropped):', '; '.join(flagged) or 'none')
    for t in ['en-US', 'en-GB', 'en-FI', 'ar-EG', 'ar-SA', 'pt-BR', 'pt-PT', 'zh-CN', 'zh-TW', 'zh-HK', 'zh-Hant-TW',
              'zh-Hant-HK', 'is-IS', 'sv-SE', 'de-DE', 'fr-FR', 'ja-JP']:
        print(f'  {t} -> {drop.get(t, "(kept)")}')
    print('collator checks (differs, effective collation for tag, for base):')
    for t, c in checks.items():
        print(f'  {t}: {c}')
    print('regions that do nothing in main/ but change collation:', hidden or 'none')
    print('ar: likely subtags', likely.get('ar'), '; default content', sorted(x for x in default_content if x.startswith('ar_')),
          '; ar_EG.xml has', children(os.path.join(main_dir, 'ar_EG.xml')))


if __name__ == '__main__':
    main(os.path.expanduser(sys.argv[1]))
