# Does the web care what `resolvedOptions().locale` returns?

An engine that resolves locales with ICU4X's "best fit" (unicode-org/icu4x#8736, unicode-org/icu4x#5868, tc39/ecma402#947) would make `Intl.*.prototype.resolvedOptions().locale` report less than today's ICU4C-shaped lookup, e.g. `en` instead of `en-US`, or `zh-Hant` instead of `zh-TW`. Formatting doesn't change, only the reported string. This measures what breaks on the web if a browser ships that. Desktop pages, Chrome Canary 160 and Firefox Nightly 163 on macOS.

## The options tested

Henri Sivonen (Mozilla) defined these as candidate behaviors (rules in [ab/rewrite.js](ab/rewrite.js), tables from CLDR by [cldr_table.py](cldr_table.py)). `·` = reported as today.

| Option | Applies to | `en-US` | `en-GB` | `pt-BR` | `ar-EG` | `ar-SA` | `zh-CN` | `zh-TW` | `zh-HK` |
|---|---|---|---|---|---|---|---|---|---|
| B3: drop the region where CLDR has no data for it | all services except Collator, constructed without a locales argument | `en` | · | `pt` | · | · | `zh` | `zh-Hant` | · |
| C1: drop regions that don't change collation, `zh-Hant` for Traditional | Collator, any construction | `en` | `en` | · | · | `ar` | `zh` | `zh-Hant` | `zh-Hant` |
| C2: as C1, but `zh-u-co-stroke` for Traditional | Collator, any construction | `en` | `en` | · | · | `ar` | `zh` | `zh-u-co-stroke` | `zh-u-co-stroke` |
| SU: `und` | Segmenter | `und` | `und` | `und` | `und` | `und` | `und` | `und` | `und` |
| SL: language only | Segmenter | `en` | `en` | `pt` | `ar` | `ar` | `zh` | `zh` | `zh` |
| B1 (pilot only): language only, script kept for Chinese | everything | `en` | `en` | `pt` | `ar` | `ar` | `zh` | `zh-Hant` | `zh-Hant` |

B3 is "no data" in the strict sense: CLDR's `common/main/` file for the region holds nothing but its identity, so formatting with the shorter tag is identical. It also drops `is-IS`, `sv-SE`, `de-DE`, `fr-FR`, `ja-JP` and so on (429 region files), and keeps `en-FI`, `pt-PT`, `de-AT`. C1 and C2 cover only Henri's Collator tags (`en-US`, `en-GB`, `ar-SA`, `zh-CN` and Traditional Chinese), each checked against CLDR's collation data. B1 (Henri's first question taken literally, as a stress test) and B2 (my approximation of the ICU4X model, likely-subtags dedup, which wrongly drops `ar-EG`, see [CLDR checks](#cldr-checks)) came first; Henri replaced both with the rules above. B1 ran as the pilot, so it shows what dropping regions that do carry data does; B2 never ran. Not tested, as Henri suggested: `supportedLocalesOf()` and the fallback for unsupported requests (`"ZZ"`, `[]`).

Each A/B loads a page three times as a user with a given locale: A and A2 unchanged (A2 shows how much the page varies by itself) and B with the option applied. A page is flagged when B differs from A more than A2 does, and flagged pages were checked by hand.

## What would break if a browser shipped it

Rates are of desktop root pages in the 2026-11-01 HTTP Archive crawl (11.4M), with 95% bounds.

- **B3**: one visible change on load, in 189 pages picked as the likeliest to react: MapQuest's map scale shows `300 m` instead of `1000 ft` for `en-US` users (it checks `=== "en-US"`). Code review finds five more that show only later in the page flow: a vaccination booking site and an ad stack that read the region from the tag (US users get metric; ads lose country targeting), v-calendar date pickers that fall back to their `zh-CN` table for `zh-Hant` (wrong first day of week for `zh-TW` users), a Brazilian billing site that loads its `pt-BR` data only for an exact `pt-BR` (English otherwise), and a sign-up form losing its default phone country. Formatted output never changed. Code that depends on the full tag is on 0.12% (0.05–0.24%) of pages; that's an upper bound, as most of it didn't change behavior. Affects users whose locale has a data-less region (`en-US`, `pt-BR`, `zh-CN`, `zh-TW`, `de-DE`, `fr-FR`, `ja-JP`, …).
- **C1, C2**: nothing changed on 95 pages. Collator's locale is read almost only by bot-defense and fraud scripts (Cloudflare Turnstile on most), on 3.1% (2.7–3.5%) of pages, which send it to their servers. Whether a changed value worsens challenge or fraud scores can't be seen from page loads; the vendors would know.
- **SU, SL**: nothing changed on 30 pages. Only one obfuscated bot-defense script reads Segmenter's locale, on 0.034% (0.005–0.117%) of pages; same server-side caveat.
- **Dropping regions that carry data** (B1, or likely-subtags for `ar-EG`): not safe. Pages pass the reported locale back to Intl as their default (1.6% of pages), so `en-GB` users get `November 19, 2026` instead of `19 November 2026`, and `ar-EG` users Latin digits instead of Arabic-Indic ones (pilot A/B).

Shipped browsers already differ: Chrome's default locale is its UI language, so an Arabic (Saudi Arabia or Egypt) Mac gets `ar`, an Icelandic Mac `en-US`, and English with a non-US/UK region `en-GB`; Firefox reports `zh-Hant-TW` where Chrome reports `zh-TW`, so exact `zh-TW`/`zh-HK` checks already miss in Firefox; and Chrome's PluralRules already reports `en` for `en-US` ([env/](env/)).

## How much the data can tell

The page rates come from 12,397 pages loaded with a trace of every `locale` read: random pages with an Intl constructor counter in 5 rank strata, which covers the top 10k almost entirely (2,867 of its 2,981 such pages) and samples 2,000–3,000 pages from each lower stratum. The first pass (400 per stratum) only bounded full-tag-dependent code to 0–0.28% of pages; the extension, sized by the time and query budget rather than a target precision, narrowed that to 0.05–0.24%. The bound is dominated by the long tail beyond the top 1M (94% of pages), where the sample is 2,000 pages. Bounds are exact per-stratum intervals, summed, so they're conservative.

What this can't see:

- Code that runs after interaction, in workers, or on logged-in pages; mobile; Safari. A recall check found that what load-only tracing misses is the same libraries running later.
- Page loads, as opposed to pages: popular pages count once, like any other.
- What servers do with the values (challenges never complete in load-only visits).
- Locales other than those tested, in particular the 64 regions B3 drops that aren't CLDR default content (e.g. `de_BE`, `fr_MC`), where region-keyed data such as week start, hour cycle or currency can differ from the language's.

A Chrome use counter would give the traffic-weighted rate, including later code and mobile: `resolvedOptions()` on an object constructed without locales whose result is passed to an Intl constructor, `toLocale*()` or `Intl.Locale` (or, simpler, `Intl.Locale.prototype.region` read on a Locale built from the default locale).

## Why these locales

Henri's list, each probing one way a rule could go wrong, plus one mixed setup:

- `en-US` / `en-GB`: a region without data next to one with data, for the same language.
- `pt-BR` / `pt-PT`: the same, where the region without data (Brazil) is the language's default.
- `ar-SA` / `ar-EG`: both carry data (`ar-EG` its own default numbering system), although likely subtags make Egypt `ar`'s default region.
- `zh-CN` / `zh-TW` / `zh-HK`: for Chinese the script matters, not the region; `zh-TW` would become `zh-Hant`, and `zh-HK` carries data.
- `is-IS`: a language spoken in one country.
- `en-FI`, English with a Finnish region (not Henri's): with `en-FI` at the top of the macOS language list, Firefox's JS default locale is `en-FI` while `navigator.language` stays `en-US`.

The A/B runs used the locales where each option changes something: B3 as `en-US`, `pt-BR` (region dropped) and `zh-TW` (region replaced by script); C1 as `en-US` and `zh-CN`; C2 as `zh-TW`, the only place it differs from C1; SU and SL as `en-US`. The pilot ran B1 as `en-GB`, `en-FI` and `ar-EG`, regions that carry data.

## Method

### Sample

[queries/sample.sql](queries/sample.sql) (first pass, 1,885 pages) and [queries/sample2.sql](queries/sample2.sql) (extension, same seed and ordering, 12,397 pages): desktop root pages of the 2026-11-01 crawl ([latest_date.sql](queries/latest_date.sql)) that hit a Blink Intl constructor counter (Collator 2593 to Segmenter 2600, DisplayNames 3172), seeded and stratified by rank, plus 1,500 pages each with the `Intl.Locale` counter (2598) and the LocaleInfoFunctions WebDX counter (244, `Intl.Locale` `get*()` methods, which depend on the region). V8 counts these at the start of each constructor; no counter covers `resolvedOptions()` or `.locale`. Of 11,388,038 desktop root pages, 3,514,922 (30.9%) have an Intl counter; Chrome's field rate for DateTimeFormat alone is about 37% of page loads (chromestatus, November 2026). Pages without a counter in the crawl count as non-readers.

Luxon reads the default locale lazily, often after load, so [luxon_10k.sql](queries/luxon_10k.sql) finds pages in the 10k sample whose bodies carry Luxon's signature, and a seeded 40 of them went into the B3 A/B ([luxon_urls.sql](queries/luxon_urls.sql), by script URL, recalls few: Luxon is mostly bundled).

### Locale setups

[env_test.py](env_test.py), results in [env/](env/). In Chrome Canary, `-AppleLanguages (<tag>)` sets the UI language, the JS default locale, workers and Accept-Language as for a real Mac user; `-AppleLocale` (Formats region) has no effect. Chrome's CDP locale override can produce states real users can't (`is-IS` with root formatting), so the pilot used launch arguments; the later runs set the locale per headless browser context, which gave the same Intl, `navigator.language` and Accept-Language values as launch arguments for the 4 locales compared. In Firefox Nightly, langpacks plus `intl.locale.requested` reproduce a localized build, and WebDriver BiDi `emulation.setLocaleOverride` gives the same Intl values.

The macOS region alone (`AppleLocale` `en_US@rg=fizzzz`) reaches neither browser's JS locale ([firefox-os-region-fi.jsonl](env/firefox-os-region-fi.jsonl), [chrome-os-region-fi.jsonl](env/chrome-os-region-fi.jsonl)): Gecko's "regional prefs" on macOS are the preferred-language list ([OSPreferences_mac.cpp](https://github.com/mozilla-firefox/firefox/blob/47f2a88cbab9072c8f8f156494b92d6891e488fb/intl/locale/mac/OSPreferences_mac.cpp#L59-L62)). With `en-FI` at the top of that list, Firefox reports `en-FI` in every Intl service and in workers, with Finnish-English formatting (`31/01/2026`, `16.04.00`, `h23`), while `navigator.language` stays `en-US`; Chrome gives `en-GB`, its nearest UI language ([firefox-os-lang-en-FI.jsonl](env/firefox-os-lang-en-FI.jsonl), [chrome-os-lang-en-FI.jsonl](env/chrome-os-lang-en-FI.jsonl)). `-AppleLanguages (en-FI)` doesn't reach Firefox's content processes ([env_fx_locales.py](env_fx_locales.py)), and the BiDi override also sets `navigator.language`, which the real setup doesn't.

### Detection and classification

[detect.py](detect.py) loads each page in headless Chrome Canary (1366x768, `en-US`) with a preload script in all frames ([detect/trace.js](detect/trace.js)) that makes `locale` on every `resolvedOptions()` result a logging accessor (service, constructor locales argument, value, stack), checked on [detect/test.html](detect/test.html) for property reads, destructuring, spread, `JSON.stringify` and `Object.assign`. Results: out-detect2/results.jsonl.gz (12,397 pages, 308 load errors; [out-detect](out-detect/) has the first pass). Reads are grouped by calling script ([group.py](group.py), [groups.json](out-detect2/groups.json), 692 groups), new groups matched to classified ones by the code around the read ([fingerprint.py](fingerprint.py)), and the rest classified by read-only reviewers from beautified code ([dossier.py](dossier.py); not committed: third-party code), with the tag-sensitive, unclear and Luxon groups checked by hand ([classes.csv](out-detect2/classes.csv)).

Each page gets its most significant use ([classify2.py](classify2.py), per stratum and for the targeted picks in [class-summary.md](out-detect2/class-summary.md)):

| Class | What the page does with the value | % of desktop root pages (95% bounds) |
|---|---|---|
| any read | | 7.41 (6.83–8.01) |
| tag-sensitive | compares the full tag, looks it up in a table keyed by full tags, or extracts the region | 0.12 (0.05–0.24) |
| fallback-probe | constructs with an unsupported request (`"ZZ"`, `[]`) to see what comes back | 0.034 (0.005–0.117) |
| passthrough | keeps it as a default and passes it back to Intl or `toLocale*()` (Luxon, intl-messageformat, date libraries) | 1.65 (1.35–1.98) |
| bot-or-fraud | sends it as one signal in a bot challenge or fraud score | 3.36 (2.95–3.81) |
| fingerprint-id | hashes it into a visitor or ad ID | 1.66 (1.37–2.00) |
| analytics | sends it to telemetry or error reporting | 0.51 (0.35–0.72) |
| language-only | uses only the language subtag | 0.031 (0.004–0.113) |
| unclear | can't tell from the code | 0.045 (0.009–0.134) |

Pages with the `Intl.Locale` or LocaleInfoFunctions counters read the locale at the same rate (25.9%, 24.1% of those pages). Bot and fraud scripts read every service except Segmenter and DurationFormat, always after construction without locales ([bot-noarg.md](out-detect2/bot-noarg.md)).

Tag-sensitive uses, by script (most on one page each): exact `zh-HK`/`zh-TW` or `zh-Hant` checks choosing a store area or language (a Shopify app, Cafe24, both also checking `navigator.language`), `Intl.Locale` region as a country (analytics, phone input default, GDPR/CCPA gating, imperial units, a locale rollout gate), `=== "en-US"` or `includes("us")` picking imperial units (MapQuest, a vaccination booking site), full-tag table lookups falling back to the language (v-calendar and similar date pickers), "is English" full-tag checks that only change a listing path, and `startsWith("de-AT")` ad targeting on Austrian news sites (kept by B3: `de_AT.xml` has data).

Recall: a seeded 250 of the first pass's pages without detected reads were loaded again and their script bodies searched for `resolvedOptions()` near `.locale` ([static_check.py](static_check.py)); 47 matched, mostly code that runs only later: intl-messageformat's lazy default-locale getter, Sentry's culture context (on error events), Luxon, plus 7 regex false positives ([static-summary.txt](out-detect/static-summary.txt)).

### CLDR checks

CLDR 1cfc52b, [cldr-report.txt](cldr-report.txt).

- B3 drops a region when `common/main/<lang>[_<Script>]_<REGION>.xml` has nothing but `<identity>` and its parent is the same locale without the region: 429 of 750 region files. 64 of them aren't default content locales (e.g. `de_BE`, `en_AS`, `fr_MC`), so for those the region still changes region-keyed supplemental data; 4 empty `en_*` files whose parent is `en_001` aren't dropped.
- `ar` vs `ar-EG`: `ar_EG.xml` sets `defaultNumberingSystem` `arab`, so `ar-EG` formats with Arabic-Indic digits and `ar` with Latin ones. That's documented, not a CLDR bug: likely subtags map `ar` to `ar_Arab_EG`, but `ar`'s default content locale is `ar_001`, and TR35 says default content "Should not be used for locale matching or likely subtags" ([tr35.md, Inheritance vs Related Information](https://github.com/unicode-org/cldr/blob/1cfc52bc791ae3058bcc113c6c87e141cf5941f5/docs/ldml/tr35.md#inheritance-vs-related-information)). So a likely-subtags rule (B2) would change formatting for `ar-EG`.
- Collation: none of C1's regions changes the collation used (`en_US.xml` is empty, `en_US_POSIX` ignored, `zh_TW`/`zh_HK` resolve to `zh_Hant`), and no region that is empty in `common/main/` changes collation (all 429 checked), so a no-argument DateTimeFormat locale passed into Collator can't lose a distinction under B3.
- Formatting with a region that carries data differs in both browsers: `en-GB`→`en` (US date order), `pt-PT`→`pt`, `ar-EG`/`ar-SA`→`ar`, `zh-HK`→`zh-Hant`, `de-AT`, `es-MX`, `fr-CA` ([passback-chrome.jsonl](env/passback-chrome.jsonl), [passback-firefox.jsonl](env/passback-firefox.jsonl)).

### A/B setup

[ab.py](ab.py) for Chrome, [ab_fx.py](ab_fx.py) for Firefox, [run_ab2.py](run_ab2.py) for the option runs. [ab/rewrite.js](ab/rewrite.js) wraps every `resolvedOptions()` in A, A2 and B alike, so pages checking for tampered natives see no difference; A and A2 only count the reads the option would change, B applies it. In B, [ab/passback.js](ab/passback.js) records every Intl call made with a rewritten tag (constructors, `toLocale*()`, `localeCompare`, `Intl.Locale` and its `get*()` methods), formats the same input with the original tag, and counts outputs that differ and whether they appear in the page text. Checked on [ab/sanity.html](ab/sanity.html) in both browsers. Live runs keep Chrome's sandbox and Safe Browsing on in both browsers and make known malware hosts unresolvable ([blocklist.py](blocklist.py)); pages on a listed host are left out. Not covered: workers, and in Firefox, console messages (only JS errors) and frames other than the top one.

### Pilot A/B (B1)

B1 on 101 pages ([ab_pages.py](ab_pages.py): all passthrough, tag-sensitive, fallback-probe and unclear pages of the first pass, plus a seeded 30 bot-or-fraud ones).

| Setup | Pages with a rewritten read | Pass a rewritten tag back during load | Output differs | Examples |
|---|---|---|---|---|
| Chrome `en-GB` | 76 of 101 | 8 | 4 | `19 November 2026` → `November 19, 2026`, `23 Nov 2026` → `Nov 23, 2026`, `Sept` → `Sep` |
| Firefox `ar-EG` | 77 of 101 | 3 | 3 | `قبل ٥ أيام` → `قبل 5 أيام` in a reviews widget, visible in the page text |
| Firefox `en-FI` | 75 of 101 | (run before the recorder) | | |

The other 47 passthrough pages didn't pass the value back during load: their libraries format later, or with the site's own locale. Pixel diffs were mostly lazy loading, which is why the recorder above was added. A sign-in page that showed only a spinner in Chrome's B rendered normally in Firefox's. Challenge tokens (`cf-turnstile-response`, `h-captcha-response`, `g-recaptcha-response`) were empty in every visit, so load-only visits can't tell whether a changed locale fails a challenge.

### A/B of the options

Pages ([ab_pages2.py](ab_pages2.py)): for B3, every tag-sensitive (59), unclear (16) and language-only (5) page, 9 pages with an `Intl.Locale` use the reviewers couldn't settle, a seeded 60 passthrough pages and a seeded 40 Luxon pages (189); for C1 and C2, the 65 pages reading a Collator's locale other than through Turnstile plus a seeded 30 Turnstile pages (95); for SU and SL, all 30 pages reading Segmenter's locale.

| Run | Pages | B rewrote a read | Passed a rewritten tag back to Intl | Result differs | Flagged, B rewrote a read | Confirmed change visible on load |
|---|---|---|---|---|---|---|
| B3 `en-US` | 189 | 133 / 137 | 19 / 20 | 6 / 5 | 20 / 20 | MapQuest scale `1000 ft` → `300 m` |
| B3 `pt-BR` | 189 | 132 / 137 | 9 / 10 | 5 / 6 | 28 / 16 | none |
| B3 `zh-TW` | 189 | 131 / 137 | 5 / 5 | 3 / 3 | 17 / 18 | none |
| C1 `en-US` | 95 | 34 / 33 | 5 / 5 | 0 / 0 | 6 / 3 | none |
| C1 `zh-CN` | 95 | 33 / 34 | 0 / 0 | 0 / 0 | 7 / 4 | none |
| C2 `zh-TW` | 95 | 31 / 34 | 0 / 0 | 0 / 0 | 3 / 2 | none |
| SU `en-US` | 30 | 26 / 28 | 0 / 0 | 0 / 0 | 4 / 2 | none |
| SL `en-US` | 30 | 27 / 28 | 1 / 1 | 0 / 0 | 3 / 4 | none |

Counts are pages, Chrome / Firefox. "Result differs" is in all cases an `Intl.Locale(locale).region` read becoming `undefined`; no formatted output differed. Flags per run: [chrome](out-ab-henri-chrome/flagged.md), [firefox](out-ab-henri-firefox/flagged.md) ([ab_analyze.py](ab_analyze.py), [ab_passback.py](ab_passback.py)).

Flagged pages were looked at one by one: text diffs ([ab_diff.py](ab_diff.py), not committed: page text), errors, and for a consistent pixel-only difference, crops rated by a read-only reviewer. Almost all are page noise: rotating banners and products, carousels on another slide, a header that sometimes doesn't render in A or A2 either, server errors in one visit, ad and analytics network errors. Pages whose B difference looked consistent were repeated three times (`out-ab-recheck-firefox-*`, `out-ab-recheck2-firefox-*`, and for the bot-defense script's pages under C1, C2, SU and SL, `out-ab-recheck4-*`, `out-ab-recheck5-chrome-*`); A or A2 showed the same difference in the repeats. The exception: a police site whose loads failed in A, A2 and B alike (also with nothing rewritten), but in Chrome somewhat more often in B, the third load in a row.

Besides MapQuest, B3 made `new Intl.Locale(locale).region` `undefined` instead of `US`/`BR`/`TW` on 9 pages, none visibly on load: a video widget, a retailer sending it to analytics as the country (falling back to `US`), a shop language switcher (which tries `navigator.languages` first), two chat or UI widgets, and a Shopify store script the trace didn't pin down (rerun with a recorder fix: `out-ab-pbcheck-*`, `out-ab-recheck3-chrome`). An Amazon careers page logs `Provided Locale is invalid: locale=null` in every Chrome B visit and continues with the reported locale; it looked the same.

## Query bytes

All on the 2026-11-01 crawl (or the 10k sample tables), run on 2026-11-25; 0.568 TiB in total, of a 5.5 TiB budget:

| Query | Bytes processed (TiB) |
|---|---|
| [latest_date.sql](queries/latest_date.sql) | <0.001 |
| [sample.sql](queries/sample.sql) | 0.045 |
| [sample2.sql](queries/sample2.sql) | 0.189 |
| [luxon_urls.sql](queries/luxon_urls.sql) | 0.073 |
| [luxon_10k.sql](queries/luxon_10k.sql) | 0.038 |
| counter exploration on the 10k sample (not kept) | <0.001 |
| a host lookup for the security check (not published) | 0.223 |

## Reproduce

This run started with version 0.35.0 (a87e8bc) of the [`httparchive` skill](https://github.com/zcorpan/web-platform-skills/blob/main/docs/httparchive.md) and moved to 0.36.0 (9aa552c) partway, for the sandbox and Safe Browsing defaults. The steps below are standalone and rerun the same analysis without the skill. Chrome Canary 160.0.8180.1, Firefox Nightly 163.0a1 (updated once during the Firefox A/B; the run that straddled the update was redone), Playwright 1.65.2, Selenium 4.54.0, Pillow 13.0.0. Live pages change, so a rerun won't match exactly; screenshots and text diffs aren't committed.

```sh
python3 -m venv .venv && .venv/bin/pip install playwright selenium pillow  # drives the installed Chrome Canary and Firefox Nightly
for q in latest_date sample2 luxon_urls luxon_10k; do bq query --use_legacy_sql=false --format=csv --max_rows=1000000 < queries/$q.sql > queries/$q.csv; done
.venv/bin/python env_test.py chrome all > env/chrome.jsonl; .venv/bin/python env_test.py firefox all > env/firefox.jsonl
.venv/bin/python detect.py "$CHROME" queries/sample2.csv out-detect2/results.jsonl  # or reuse the committed run: gunzip -k out-detect2/results.jsonl.gz
python3 group.py out-detect2/results.jsonl out-detect2/groups.json
.venv/bin/python dossier.py out-detect2/results.jsonl out-detect2/groups.json dossiers2/  # then classify groups into out-detect2/classes.csv (fingerprint.py matches known code)
python3 classify2.py out-detect2/results.jsonl out-detect2/groups.json out-detect2/classes.csv queries/sample2.csv > out-detect2/class-summary.md
python3 bot_noarg.py out-detect2/results.jsonl out-detect2/groups.json out-detect2/classes.csv queries/sample2.csv > out-detect2/bot-noarg.md
python3 cldr_table.py ~/git/unicode-org/cldr > cldr-report.txt  # CLDR at 1cfc52b; writes ab/cldr-table.json
python3 ab_pages2.py
AB_HEADLESS=1 .venv/bin/python run_ab2.py chrome out-ab-henri-chrome; .venv/bin/python run_ab2.py firefox out-ab-henri-firefox
python3 ab_analyze.py out-ab-henri-chrome/results.jsonl > out-ab-henri-chrome/flagged.md; python3 ab_analyze.py out-ab-henri-firefox/results.jsonl > out-ab-henri-firefox/flagged.md
python3 ab_passback.py out-ab-henri-*/results.jsonl
```

## License

MIT, see [LICENSE](LICENSE), for the scripts, analysis and text written for this research. Content from the crawl and the live web (`queries/`, `crawl/`, screenshots, page snippets) and third-party code (`vendor/`) belongs to its owners and isn't covered.
