# Does the web care what `resolvedOptions().locale` returns?

Options under discussion (unicode-org/icu4x#8736, unicode-org/icu4x#5868, tc39/ecma402#947): ICU4X-based "best fit" locale resolution in engines, which would make ECMA-402 `Intl.*.prototype.resolvedOptions().locale` report less than today's ICU4C-shaped lookup: e.g. `en` instead of `en-US`, `zh-Hant` instead of `zh-TW` or `zh-HK`, and possibly something else for `Intl.Segmenter` and `Intl.Collator`. Formatting output would not change; only the reported locale would.

## Summary

Status: done. Desktop pages, Chrome Canary 160 and Firefox Nightly 163 on macOS; variants defined by Henri (below).

- 24.0% (22.1–26.0%) of desktop root pages that construct an Intl object read `resolvedOptions().locale` during load, about 7.4% of all desktop root pages ([class-summary.md](out-detect2/class-summary.md), 12,397 pages). Pages with the `Intl.Locale` or LocaleInfoFunctions counters read it at the same rate (25.9%, 24.1%).
- What the value is used for, by page (most significant use, % of Intl pages): bot-challenge or fraud signal 10.9%; hashed visitor or ad ID 5.4%; passed back to Intl as a library default 5.3%; telemetry 1.7%; tag- or region-sensitive 0.39% (0.17–0.77%); fallback probe 0.11%; language subtag only 0.10%; unclear 0.15%.
- B3 (region dropped where CLDR has no data for it, objects other than Collator constructed without locales) on 189 pages as `en-US`, `pt-BR` and `zh-TW` users, in both browsers: one visible change on load, MapQuest's map scale switching US users from `1000 ft` to `300 m` (it checks `=== "en-US"`). When pages passed the value back to Intl, no formatted output changed; the only changed results were `new Intl.Locale(locale).region` reads becoming `undefined` (a video widget, a retailer's analytics country, which falls back to US, a shop language switcher, two chat widgets), none visible on load. Code review finds more that only shows later in the page flow: a vaccination booking site switching US users to metric, v-calendar date pickers using their `zh-CN` table (first day of week, masks) for `zh-Hant`, a Brazilian billing site loading English locale data for `pt`, an ad stack losing country targeting, a sign-up form losing its default phone country.
- Collator (C1, C2) is read almost only by bot-defense and fraud scripts (10.0% of Intl pages, always after construction without locales; Cloudflare Turnstile on most). C1 and C2 on 95 pages changed nothing visible in either browser.
- Segmenter's locale is read only by one obfuscated bot-defense VM (0.11% of Intl pages), on a Segmenter constructed with `[]`; SU (`und`) and SL (language only, mismatching DateTimeFormat) on its 30 pages changed nothing visible. What a changed value does to challenge or fraud scores (server side) can't be seen from load-only visits.
- Bot and fraud scripts read every service except Segmenter and DurationFormat after construction without locales: DateTimeFormat on 11.0% of Intl pages, the others on 10.0–10.2% ([bot-noarg.md](out-detect2/bot-noarg.md)).
- `ar` vs `ar-EG` differing in CLDR is documented behavior, not a bug, and no region that is empty in CLDR's `main/` changes collation, so a no-argument DateTimeFormat locale passed into Collator can't lose a distinction under B3 (see CLDR checks).
- Dropping regions that do carry data would be visible: in both browsers `en-GB`→`en` (US date order), `pt-PT`→`pt`, `ar-EG`/`ar-SA`→`ar` (Latin instead of Arabic-Indic digits), `zh-HK`→`zh-Hant`, `de-AT`, `es-MX`, `fr-CA` format differently ([passback-chrome.jsonl](env/passback-chrome.jsonl), [passback-firefox.jsonl](env/passback-firefox.jsonl)), and the pilot A/B saw such changes on pages (`19 November 2026` → `November 19, 2026`).
- Shipped browsers already differ: Chrome's default locale is its UI language, so an Arabic (Saudi Arabia or Egypt) Mac gets `ar`, an Icelandic Mac `en-US`, English with a non-US/UK region `en-GB`, and Chinese (Hong Kong) `zh-TW`; Firefox reports `zh-Hans-CN`, `zh-Hant-TW` and `zh-Hant-HK` where Chrome reports `zh-CN`, `zh-TW` and `zh-HK`, so exact `zh-TW`/`zh-HK` checks (a Shopify IP-block app, a Cafe24 language switcher, both also checking navigator.language) already miss in Firefox; Chrome's PluralRules already reports `en` for `en-US` and `zh` for `zh-TW` when requested explicitly ([env/](env/)).
- A Chrome use counter would give a field rate for what matters here: `resolvedOptions()` on an object constructed without locales whose result is passed to an Intl constructor, `toLocale*()` or `Intl.Locale` (or, simpler, `Intl.Locale.prototype.region` read on a Locale built from the default locale).

## Scope

- Questions: which pages read `resolvedOptions().locale`, from which service, after constructing with no locales argument or an explicit one; what they do with the value; whether pages break if the region is dropped (and `zh-TW`/`zh-HK` become `zh-Hant`); whether anything reads Segmenter's locale.
- Locale environments: Firefox Nightly and Chrome Canary on macOS, configured per process with real launch arguments where they reproduce a real setup; the per-page locale override (CDP/BiDi) only where they can't. Test locales: `en-US`, `en-GB`, `ar-SA`, `ar-EG`, `pt-BR`, `pt-PT`, `zh-CN`, `zh-TW`, `zh-HK`, `is-IS`, plus a mixed language/region setup (e.g. English UI with a non-English region). No VPN.
- Pages: 2000 desktop root pages from the latest HTTP Archive crawl that hit a Blink Intl constructor counter, seeded, stratified by rank, later extended to 12,397 (same seed) with targeted picks for `Intl.Locale` and LocaleInfoFunctions. Detection in Chrome with a preload script that logs every read of `locale` on a `resolvedOptions()` result.
- Recall check: static scan of `httparchive.sample_data.requests_10k` bodies.
- Then: classify the uses by code review; stop for the variant definitions to be checked before the A/B comparison (A, A2 = locale L; B = same with `resolvedOptions().locale` rewritten per variant), Chrome first, then Firefox.
- Budget: 0.5 TiB of queries, raised to 5.5 TiB on 2026-11-25.

## What breaks and why

Variants (Henri's, replacing the earlier B1/B2 proposals; [ab/rewrite.js](ab/rewrite.js), tables from CLDR 1cfc52b by [cldr_table.py](cldr_table.py), [cldr-report.txt](cldr-report.txt)):

- B3: objects other than Collator constructed without a locales argument report the default locale without its region when CLDR's `common/main/<lang>[_<Script>]_<REGION>.xml` has nothing but `<identity>` and its parent is the same locale without the region: `en-US`→`en`, `pt-BR`→`pt`, `zh-CN`→`zh`, `zh-TW` and `zh-Hant-TW`→`zh-Hant`, `is-IS`, `sv-SE`, `de-DE`, `fr-FR`, `ja-JP` likewise; `en-GB`, `en-FI`, `ar-EG`, `ar-SA`, `pt-PT`, `zh-HK` kept. Of the 429 such files (of 750 region files), 64 aren't CLDR default content locales (e.g. `de_BE`, `en_AS`, `fr_MC`), so for those the region still changes region-keyed supplemental data (week, hour cycle, currency); 4 empty `en_*` files whose parent is `en_001` aren't dropped.
- C1: Collator (with or without a locales argument) reports `en-US`, `en-GB`→`en`, `ar-SA`→`ar`, `zh-CN`→`zh`, and `zh-TW`/`zh-HK`→`zh-Hant`; C2 the same but `zh-TW`/`zh-HK`→`zh-u-co-stroke`. In `common/collation/`, none of these regions changes the collation used (`en_US.xml` is empty, `en_US_POSIX` ignored, `zh_TW`/`zh_HK` resolve to `zh_Hant`).
- SU: Segmenter reports `und`; SL: Segmenter reports the language only, so it differs from DateTimeFormat.
- Not tested, as Henri suggested: `supportedLocalesOf()` and the `"ZZ"`/`[]` fallback.

CLDR checks:

- `ar` vs `ar-EG`: `ar_EG.xml` sets `defaultNumberingSystem` `arab` (and a display name), so `ar-EG` formats with Arabic-Indic digits and `ar` with Latin ones. That's documented behavior, not a CLDR bug: likely subtags map `ar` to `ar_Arab_EG`, but `ar`'s default content locale is `ar_001`, and TR35 says default content "Should not be used for locale matching or likely subtags" ([tr35.md, Inheritance vs Related Information](https://github.com/unicode-org/cldr/blob/1cfc52bc791ae3058bcc113c6c87e141cf5941f5/docs/ldml/tr35.md#inheritance-vs-related-information)). Default content locales are empty by definition; likely-subtags regions needn't be.
- No region that is empty in `common/main/` changes collation (checked over all 429 files with `common/collation/` and its collation parent locales), so a no-argument DateTimeFormat locale passed into Collator can't lose a collation distinction under B3.

## 1. HTTP Archive

[queries/sample.sql](queries/sample.sql) (0.189 TiB): desktop root pages of the 2026-11-01 crawl ([latest_date.sql](queries/latest_date.sql)) that hit a Blink Intl constructor counter (Collator 2593 to Segmenter 2600, DisplayNames 3172). V8 counts these at the start of each constructor, so they say nothing about `resolvedOptions()`, and no counter covers it or `.locale`. 400 pages per rank stratum, seed `intl-compat-1` ([sample.csv](queries/sample.csv); 1885 pages, since only 285 top-1k pages qualify). [queries/sample2.sql](queries/sample2.sql) extends it with the same seed and ordering (so the first sample's pages come first) to 9,981 random pages, plus 1,500 pages each with the `Intl.Locale` counter (2598) and the LocaleInfoFunctions WebDX counter (244, `Intl.Locale` `get*()` methods, which depend on the region) ([sample2.csv](queries/sample2.csv), 12,397 pages).

Luxon recall: [luxon_urls.sql](queries/luxon_urls.sql) lists 2026-11-01 desktop root pages loading a script whose URL names a known Luxon carrier, and [luxon_10k.sql](queries/luxon_10k.sql) the 10k sample's pages with a body carrying Luxon's signature; a seeded 40 of the latter went into the B3 A/B, since Luxon reads the default locale lazily, often after load.

| | desktop |
|---|---|
| Root pages crawled | 11,388,038 |
| With an Intl constructor counter | 3,514,922 (30.9%) |

Chrome's field rate for DateTimeFormat alone is about 37% of page loads (chromestatus, November 2026).

## 2. Live comparison on a sample

Locale environments ([env_test.py](env_test.py), [env/](env/)): in Chrome Canary 160, `-AppleLanguages (<tag>)` sets the UI language, the JS default locale, workers and Accept-Language as for a real Mac user; `-AppleLocale` (Formats region) has no effect, and headless Chrome ignored every switch. In Firefox Nightly 163, langpacks plus `intl.locale.requested` reproduce a localized build, but `-AppleLanguages` doesn't reach Firefox's OS locale lookup (the path that gives English UI + Finnish region `en-FI`); WebDriver BiDi `emulation.setLocaleOverride` reproduces those values. Chrome's CDP locale override can produce states real Chrome users can't (`is-IS` reported with root formatting), so Chrome runs use launch arguments.

With the macOS region set to Finland and English (US) kept as the language (`AppleLocale` `en_US@rg=fizzzz`), Chrome Canary and Firefox Nightly still report `en-US` everywhere ([firefox-os-region-fi.jsonl](env/firefox-os-region-fi.jsonl), [chrome-os-region-fi.jsonl](env/chrome-os-region-fi.jsonl)). On macOS, Gecko's "regional prefs" locales are the preferred-language list (`CFLocaleCopyPreferredLanguages`, [OSPreferences_mac.cpp](https://github.com/mozilla-firefox/firefox/blob/47f2a88cbab9072c8f8f156494b92d6891e488fb/intl/locale/mac/OSPreferences_mac.cpp#L59-L62)), not the region, so an `en-FI` default needs `en-FI` in that list. `-AppleLanguages (en-FI)` does give `en-FI` in Firefox's parent process, but content processes don't get the arguments and keep the system list's `en-US` ([env_fx_locales.py](env_fx_locales.py)).

With `en-FI` at the top of the system list (`defaults write -g AppleLanguages`, restored after the test), Firefox Nightly reports `en-FI` in every Intl service and in workers, with Finnish-English formatting (`31/01/2026`, `16.04.00`, `h23`), also with the en-GB langpack, while `navigator.language` stays `en-US` (or `en-GB`) ([firefox-os-lang-en-FI.jsonl](env/firefox-os-lang-en-FI.jsonl)). Chrome Canary gives `en-GB`, its nearest UI language, everywhere ([chrome-os-lang-en-FI.jsonl](env/chrome-os-lang-en-FI.jsonl)), as with `-AppleLanguages (en-FI)`. The BiDi override gives Firefox the same Intl values, but also sets `navigator.language` and Accept-Language to `en-FI`, which the real setup doesn't.

Detection ([detect.py](detect.py), [detect/trace.js](detect/trace.js)): Chrome Canary, headless, 1366x768, default `en-US`, a preload script in all frames making `locale` on every `resolvedOptions()` result a logging accessor (service, constructor locales argument, value, stack), checked on [detect/test.html](detect/test.html) for property reads, destructuring, spread, `JSON.stringify` and `Object.assign`, with page-visible results unchanged. Not traced: workers. Results in [out-detect/results.jsonl](out-detect/results.jsonl) (1885 pages) and, for the extension, out-detect2/results.jsonl.gz (12,397 pages, 308 load errors; it also traces tags passed into `Intl.Locale` and its info methods).

Grouping and review: reads grouped by calling script ([group.py](group.py), [out-detect2/groups.json](out-detect2/groups.json), 692 groups), dossiers of beautified code around each frame ([dossier.py](dossier.py); not committed: third-party code), new groups matched to already classified ones by the normalized code around the read ([fingerprint.py](fingerprint.py)), the rest classified by read-only reviewers, with the tag-sensitive, unclear and Luxon groups checked by hand ([classes.csv](out-detect2/classes.csv)).

[class-summary.md](out-detect2/class-summary.md) ([classify2.py](classify2.py)), random picks:

| Class | top1k (n=279) | top10k (n=2588) | top100k (n=2906) | top1M (n=1961) | rest (n=1967) | Extrapolated % of Intl pages (95% bounds) |
|---|---|---|---|---|---|---|
| any read | 52 | 458 | 528 | 368 | 480 | 24.01 (22.14–25.95) |
| tag-sensitive | 0 | 8 | 16 | 17 | 7 | 0.39 (0.17–0.77) |
| fallback-probe | 1 | 11 | 10 | 4 | 2 | 0.11 (0.02–0.38) |
| passthrough | 4 | 32 | 62 | 51 | 109 | 5.33 (4.39–6.42) |
| bot-or-fraud | 35 | 299 | 327 | 200 | 215 | 10.89 (9.55–12.35) |
| fingerprint-id | 9 | 86 | 86 | 79 | 108 | 5.38 (4.43–6.47) |
| analytics | 3 | 16 | 22 | 14 | 34 | 1.66 (1.14–2.32) |
| language-only | 0 | 0 | 0 | 2 | 2 | 0.10 (0.01–0.37) |
| unclear | 0 | 6 | 5 | 1 | 3 | 0.15 (0.03–0.43) |

Population: 3,514,922 desktop root pages with an Intl counter (top1k 285, top10k 2,696, top100k 23,479, top1M 217,810, rest 3,270,652) of 11,388,038. Intervals: per-stratum Clopper–Pearson bounds summed (conservative). The targeted picks, as rates within their own populations, are in the same file.

Tag-sensitive uses, by script (most on one page each): exact `zh-HK`/`zh-TW` or `zh-Hant` checks choosing a store area or language (a Shopify app, Cafe24), `Intl.Locale` region as a country (analytics, phone input default, GDPR/CCPA gating, imperial units, a locale rollout gate), `=== "en-US"` or `includes("us")` picking imperial units (MapQuest, a vaccination booking site), full-tag table lookups falling back to the language (v-calendar and similar date pickers), "is English" full-tag checks that only change a listing path, and `startsWith("de-AT")` ad targeting on Austrian news sites (kept by B3: `de_AT.xml` has data).

Recall: a seeded 250 of the pages without detected reads were loaded again and their script bodies searched for `resolvedOptions()` near `.locale` ([static_check.py](static_check.py)); 47 matched, mostly code that runs only later: intl-messageformat's lazy default-locale getter, Sentry's culture context (on error events), Luxon, plus 7 regex false positives ([static-summary.txt](out-detect/static-summary.txt)). So load-only detection undercounts readers, but what it misses is the same libraries.

A/B setup ([ab.py](ab.py) for Chrome, [ab_fx.py](ab_fx.py) for Firefox; pages from [ab_pages.py](ab_pages.py): all 71 passthrough, tag-sensitive, fallback-probe and unclear pages, plus a seeded 30 of the 194 bot-or-fraud pages). A and A2 load the page as a user with locale L gets it (Chrome: a headed Canary launched with `-AppleLanguages (L)`; Firefox: BiDi locale override plus `intl.accept_languages`), with [ab/rewrite.js](ab/rewrite.js) wrapping every `resolvedOptions()` and only counting the reads the variant would change; B is the same with the variant applied. Since the same wrapper is in A and B, pages checking for tampered natives see no difference between them. Checked on [ab/sanity.html](ab/sanity.html) in both browsers: default and explicit-locale reads are rewritten in B only, the wrapper's `toString()` looks native, and passing the B value back to Intl gives `en`'s formatting for `en-GB` under B1. Not covered: workers, and in Firefox, frames other than the top one in the measurements.

### Pilot A/B (B1)

B1 on the 101 A/B pages, Chrome Canary as an `en-GB` user and Firefox Nightly as `en-FI` and `ar-EG` users. What it changed about the setup:

- Pixel diffs are mostly lazy loading (an image or a social widget that's in B's screenshot but not A's), and the first 3000 characters of text miss most dates. So [ab/passback.js](ab/passback.js) now records, in B, every Intl call made with a rewritten tag (constructors, `toLocale*()`, `localeCompare`, `Intl.Locale` and its `get*()` methods), formats the same input with the original tag, and counts the outputs that differ and whether they appear in the page text; runs keep the full page text (up to 50,000 characters).
- Challenge tokens (`cf-turnstile-response`, `h-captcha-response`, `g-recaptcha-response`) were empty in every A, A2 and B visit, so load-only visits can't tell whether a changed locale fails a challenge.

Results so far:

| Setup | Pages with a rewritten read | Pass a rewritten tag back during load | Output differs | Examples |
|---|---|---|---|---|
| Chrome `en-GB` | 76 of 101 | 8 | 4 | `19 November 2026` → `November 19, 2026`, `23 Nov 2026` → `Nov 23, 2026`, `Sept` → `Sep` |
| Firefox `ar-EG` | not counted | 3 | 3 | Arabic-Indic digits become Latin: `قبل ٥ أيام` → `قبل 5 أيام` in a reviews widget, visible in the page text |
| Firefox `en-FI` | 75 of 101 | (run before the recorder) | | |

The other 47 passthrough pages didn't pass the value back during load: their libraries format later, or with the site's own locale. One page that changed output in Chrome showed none of the changed strings in its text (tooltips, attributes or widgets not yet opened). No B-only failure reproduced in the other browser: a sign-in page that showed only a spinner in Chrome's B rendered normally in Firefox's.

## 3. A/B of Henri's variants

Pages ([ab_pages2.py](ab_pages2.py), from the extended detection): for B3, every tag-sensitive (59), unclear (16) and language-only (5) page, 9 pages with an `Intl.Locale` use the reviewers couldn't settle, a seeded 60 passthrough pages and a seeded 40 of the Luxon pages from the 10k body scan (189); for Collator, the 65 pages reading a Collator's locale other than through Turnstile plus a seeded 30 Turnstile pages (95); for Segmenter, all 30 pages reading its locale. Runs ([run_ab2.py](run_ab2.py)): B3 as `en-US`, `zh-TW` and `pt-BR` users, C1 as `en-US` and `zh-CN`, C2 as `zh-TW`, SU and SL as `en-US`. Chrome Canary ran headless with the locale and a regular user agent set per browser context, which gave the same Intl, `navigator.language` and Accept-Language values as headed Canary launched with `-AppleLanguages` for the 4 locales compared; Firefox Nightly used the BiDi locale override as before. Live runs keep Chrome's sandbox and Safe Browsing on in both browsers, and make a list of known malware hosts unresolvable ([blocklist.py](blocklist.py)); pages on a listed host are left out.

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

Counts are pages, Chrome / Firefox. "Result differs" is in all cases an `Intl.Locale(locale).region` read; no formatted output differed. Per-run flags: [chrome](out-ab-henri-chrome/flagged.md), [firefox](out-ab-henri-firefox/flagged.md) ([ab_analyze.py](ab_analyze.py), [ab_passback.py](ab_passback.py)).

Flagged pages (B differs from A by more than A2 does in text or pixels, or has an error A and A2 don't) were looked at one by one: text diffs ([ab_diff.py](ab_diff.py), not committed: page text), errors, and for a consistent pixel-only difference, crops rated by a read-only reviewer. Three pages whose B difference looked consistent were repeated three times (out-ab-recheck-firefox-*, out-ab-recheck2-firefox-*); A or A2 showed the same difference in the repeats. Almost all are page noise: rotating banners and products, carousels on another slide, a header or page that sometimes doesn't render in A or A2 either, server errors in one visit, ad and analytics network errors.

What B3 changed:

- MapQuest (`en-US`, both browsers): the map scale shows `300 m` instead of `1000 ft`; its code picks imperial units only for `=== "en-US"`.
- `new Intl.Locale(locale).region` is `undefined` instead of `US`/`BR`/`TW` on 9 pages: a video widget (hundreds of reads per page), a retailer sending it to analytics as the country (falling back to `US`), a shop language switcher (navigator.languages first), two chat or UI widgets that also read the language, and one read on a Shopify store from a script the trace didn't pin down. Nothing visible on load. (The recorder dropped these samples in the main runs, since `undefined` didn't serialize; rerun with the fix: out-ab-pbcheck-*, out-ab-recheck3-chrome.)
- An Amazon careers page logs `Provided Locale is invalid: locale=null` and continues with the reported locale (`en`, `pt`, `zh-Hant`) in every Chrome B visit; the page looked the same.
- No formatted output changed when pages passed the value back to Intl (dates, numbers, relative time, plural rules): B3 only drops regions whose CLDR data is the language's.
- Not reached on load, from code review: a vaccination booking site that picks imperial units when the lowercased tag includes `us` (US users get metric under B3); v-calendar and similar date pickers, whose full-tag tables have `zh-TW` but not `zh-Hant`, so `zh-TW` users get the `zh-CN` first day of week and masks; a Brazilian billing site that registers its `pt-BR` locale data only for an exact `pt-BR` and otherwise uses English; an ad stack using the lowercased full tag as country targeting; a sign-up form using the region as the default phone country.

What C1, C2, SU and SL changed: nothing seen. The bot-defense VM's pages were the most likely to react, so its three flagged pages were repeated three times per variant in both browsers (out-ab-recheck4-*): a police site's loads failed in A, A2 and B alike (also with nothing rewritten, out-ab-recheck5-chrome-*; in Chrome B failed somewhat more often, being the third load in a row), and a bank's login text and a cookie banner varied between A and A2 too. Collator readers are bot-defense, fraud and fingerprinting scripts that send the value to a server, so the effect, if any, is on challenge or fraud outcomes, which load-only visits don't show (see Not covered).

## Not covered

- Workers (not traced), code that runs after interaction (see Recall), logged-in pages, mobile.
- Whether bot challenges and fraud scoring react to a changed locale: challenges don't complete during load-only visits (see Pilot), and the values these scripts send are judged server side.
- Locales other than those tested, in particular regions B3 drops that aren't CLDR default content (64 of the 429, e.g. `de_BE`, `fr_MC`), where region-keyed supplemental data (week, hour cycle, currency) can differ from the language's.
- In Firefox, console messages (only JS errors are compared) and frames other than the top one.
- Safari.

## Query bytes

All on the 2026-11-01 crawl (or the 10k sample tables), run on 2026-11-25; 0.568 TiB in total:

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
python3 ab_analyze.py out-ab-henri-*/results.jsonl; python3 ab_passback.py out-ab-henri-*/results.jsonl
```

## License

MIT, see [LICENSE](LICENSE), for the scripts, analysis and text written for this research. Content from the crawl and the live web (`queries/`, `crawl/`, screenshots, page snippets) and third-party code (`vendor/`) belongs to its owners and isn't covered.

