# Does the web care what `resolvedOptions().locale` returns?

<!-- Fill in or delete every comment and placeholder. Take each number from a committed file and
     say which. No billing project, account, job IDs, or costs; bytes processed only, in TiB. -->

Options under discussion (unicode-org/icu4x#8736, unicode-org/icu4x#5868, tc39/ecma402#947): ICU4X-based "best fit" locale resolution in engines, which would make ECMA-402 `Intl.*.prototype.resolvedOptions().locale` report less than today's ICU4C-shaped lookup: e.g. `en` instead of `en-US`, `zh-Hant` instead of `zh-TW` or `zh-HK`, and possibly something else for `Intl.Segmenter` and `Intl.Collator`. Formatting output would not change; only the reported locale would.

## Summary

Status: detection and code review done; the A/B comparison waits on the variant definitions below.

- 22.1% (18.1–26.5%) of desktop root pages that construct an Intl object read `resolvedOptions().locale` during load, about 6.8% of all desktop root pages ([class-summary.md](out-detect/class-summary.md)). Almost all reads follow construction without a locales argument; explicit-argument reads came from a few news sites and the fallback probes.
- What the value is used for, by page (most significant use): bot-challenge or fraud signal 8.6% of Intl pages (Cloudflare Turnstile alone on 142 of 354 reading pages, plus hCaptcha, Kasada, Riskified, Signifyd, Adyen, TikTok); passed back to Intl as a library default locale 6.7% (Luxon, intl-messageformat via react-intl/i18next on Wix and VTEX, LiquidJS); hashed visitor or ad ID 4.6% (FingerprintJS); telemetry 1.9% (Sentry, Framer, Vimeo); language subtag only 0.2%.
- Only 3 sampled pages compare full tags: a Shopify IP-block app checks `zh-HK`/`zh-TW` exactly (already never matching in Firefox, which reports `zh-Hant-TW`; navigator.language and the time zone cover it), and an Austrian news site checks `startsWith("de-AT")` for ad targeting.
- `Intl.Segmenter`'s locale is read on 8 sampled pages, all by one obfuscated bot-defense VM on banking, retail and streaming sign-in pages, which constructs Segmenter, Collator, DisplayNames and DateTimeFormat with `"ZZ"` and `[]` and reads the fallback.
- Passing the reported locale back to Intl is the visible risk: in Chrome Canary 160 and Firefox Nightly 163 alike, `en-US`→`en`, `pt-BR`→`pt`, `zh-CN`→`zh`, `zh-TW`→`zh-Hant`, `sv-SE`→`sv` format identically, but `en-GB`→`en` (US date order), `pt-PT`→`pt`, `ar-EG`/`ar-SA`→`ar` (Latin instead of Arabic-Indic digits), `zh-HK`→`zh-Hant`, `de-AT`, `es-MX`, `fr-CA` don't ([passback-chrome.jsonl](env/passback-chrome.jsonl), [passback-firefox.jsonl](env/passback-firefox.jsonl); dates, numbers, currency, relative time, hour cycle and week info compared). So dropping every region would visibly change dates and numbers on Luxon-style pages, while dropping only data-identical regions shouldn't.
- Shipped browsers already differ: Chrome's default locale is its UI language, so an Arabic (Saudi Arabia or Egypt) Mac gets `ar`, an Icelandic Mac `en-US`, English with a non-US/UK region `en-GB`, and Chinese (Hong Kong) `zh-TW`; Firefox reports `zh-Hans-CN`/`zh-Hant-TW` where Chrome reports `zh-CN`/`zh-TW`; Chrome's PluralRules already reports `en` for `en-US` and `zh` for `zh-TW` when requested explicitly ([env/](env/)).

## Scope

- Questions: which pages read `resolvedOptions().locale`, from which service, after constructing with no locales argument or an explicit one; what they do with the value; whether pages break if the region is dropped (and `zh-TW`/`zh-HK` become `zh-Hant`); whether anything reads Segmenter's locale.
- Locale environments: Firefox Nightly and Chrome Canary on macOS, configured per process with real launch arguments where they reproduce a real setup; the per-page locale override (CDP/BiDi) only where they can't. Test locales: `en-US`, `en-GB`, `ar-SA`, `ar-EG`, `pt-BR`, `pt-PT`, `zh-CN`, `zh-TW`, `zh-HK`, `is-IS`, plus a mixed language/region setup (e.g. English UI with a non-English region). No VPN.
- Pages: 2000 desktop root pages from the latest HTTP Archive crawl that hit a Blink Intl constructor counter, seeded, stratified by rank. Detection in Chrome with a preload script that logs every read of `locale` on a `resolvedOptions()` result.
- Recall check: static scan of `httparchive.sample_data.requests_10k` bodies.
- Then: classify the uses by code review; stop for the variant definitions to be checked before the A/B comparison (A, A2 = locale L; B = same with `resolvedOptions().locale` rewritten per variant), Chrome first, then Firefox.
- Budget: 0.5 TiB of queries.

## What breaks and why

Not measured yet. Variants proposed for the A/B comparison, to check with Henri:

- B1 (stress test): every `resolvedOptions().locale` reports the language only; `zh-TW`/`zh-HK` (and Firefox's `zh-Hant-TW`/`zh-Hant-HK`) report `zh-Hant`; `zh-CN`/`zh-Hans-CN` report `zh`. Formatting is unchanged; only the reported string changes.
- B2 (likely-subtags dedup, my approximation of the ICU4X "best fit" model): report the first of language, language-Script that maximizes to the same tag as the resolved one: `en-US`→`en`, `pt-BR`→`pt`, `zh-CN`/`zh-Hans-CN`→`zh`, `zh-TW`→`zh-Hant`, `sv-SE`→`sv`, `is-IS`→`is`, `ar-EG`→`ar`; `en-GB`, `pt-PT`, `ar-SA`, `zh-HK` kept. Of the tags tested, only `ar-EG`→`ar` formats differently when passed back ([passback](env/passback.js)), so a model that drops only data-identical regions would keep `ar-EG`.
- Fallback for invalid or unsupported requests (`"ZZ"`, `[]`) unchanged in both, unless the model changes it.

Open questions:

- Is B2 what the ICU4X model would report for each test locale, including `ar-EG` (its data differs from `ar` in Chrome) and `zh-HK` (`zh-Hant-HK`?), and for Collator (`en`/root-valid languages) and Segmenter (language only? something else)?
- Does the model's deduplication consider region-derived preferences a library gets by passing the tag back (week info, hour cycle, default calendar and numbering system), not only the locale's own data?
- Does it change `supportedLocalesOf()` results or the fallback for `"ZZ"`/`[]`?

## 1. HTTP Archive

[queries/sample.sql](queries/sample.sql) (0.189 TiB): desktop root pages of the 2026-11-01 crawl ([latest_date.sql](queries/latest_date.sql)) that hit a Blink Intl constructor counter (Collator 2593 to Segmenter 2600, DisplayNames 3172). V8 counts these at the start of each constructor, so they say nothing about `resolvedOptions()`, and no counter covers it or `.locale`. 400 pages per rank stratum, seed `intl-compat-1` ([sample.csv](queries/sample.csv); 1885 pages, since only 285 top-1k pages qualify).

| | desktop |
|---|---|
| Root pages crawled | 11,388,038 |
| With an Intl constructor counter | 3,514,922 (30.9%) |

Chrome's field rate for DateTimeFormat alone is about 37% of page loads (chromestatus, November 2026).

## 2. Live comparison on a sample

Locale environments ([env_test.py](env_test.py), [env/](env/)): in Chrome Canary 160, `-AppleLanguages (<tag>)` sets the UI language, the JS default locale, workers and Accept-Language as for a real Mac user; `-AppleLocale` (Formats region) has no effect, and headless Chrome ignored every switch. In Firefox Nightly 163, langpacks plus `intl.locale.requested` reproduce a localized build, but `-AppleLanguages` doesn't reach Firefox's OS locale lookup (the path that gives English UI + Finnish region `en-FI`); WebDriver BiDi `emulation.setLocaleOverride` reproduces those values. Chrome's CDP locale override can produce states real Chrome users can't (`is-IS` reported with root formatting), so Chrome runs use launch arguments.

With the macOS region set to Finland and English (US) kept as the language (`AppleLocale` `en_US@rg=fizzzz`), Chrome Canary and Firefox Nightly still report `en-US` everywhere ([firefox-os-region-fi.jsonl](env/firefox-os-region-fi.jsonl), [chrome-os-region-fi.jsonl](env/chrome-os-region-fi.jsonl)). On macOS, Gecko's "regional prefs" locales are the preferred-language list (`CFLocaleCopyPreferredLanguages`, [OSPreferences_mac.cpp](https://github.com/mozilla-firefox/firefox/blob/47f2a88cbab9072c8f8f156494b92d6891e488fb/intl/locale/mac/OSPreferences_mac.cpp#L59-L62)), not the region, so an `en-FI` default needs `en-FI` in that list. `-AppleLanguages (en-FI)` does give `en-FI` in Firefox's parent process, but content processes don't get the arguments and keep the system list's `en-US` ([env_fx_locales.py](env_fx_locales.py)).

With `en-FI` at the top of the system list (`defaults write -g AppleLanguages`, restored after the test), Firefox Nightly reports `en-FI` in every Intl service and in workers, with Finnish-English formatting (`31/01/2026`, `16.04.00`, `h23`), also with the en-GB langpack, while `navigator.language` stays `en-US` (or `en-GB`) ([firefox-os-lang-en-FI.jsonl](env/firefox-os-lang-en-FI.jsonl)). Chrome Canary gives `en-GB`, its nearest UI language, everywhere ([chrome-os-lang-en-FI.jsonl](env/chrome-os-lang-en-FI.jsonl)), as with `-AppleLanguages (en-FI)`. The BiDi override gives Firefox the same Intl values, but also sets `navigator.language` and Accept-Language to `en-FI`, which the real setup doesn't.

Detection ([detect.py](detect.py), [detect/trace.js](detect/trace.js)): Chrome Canary, headless, 1366x768, default `en-US`, a preload script in all frames making `locale` on every `resolvedOptions()` result a logging accessor (service, constructor locales argument, value, stack), checked on [detect/test.html](detect/test.html) for property reads, destructuring, spread, `JSON.stringify` and `Object.assign`, with page-visible results unchanged. Not traced: workers. Results in [out-detect/results.jsonl](out-detect/results.jsonl), 1885 pages, 35 load errors.

Grouping and review: reads grouped by calling script ([group.py](group.py), [groups.json](out-detect/groups.json), 138 groups), dossiers of beautified code around each frame (not committed: third-party code), each group classified by read-only reviewers, with the tag-sensitive and Luxon groups checked by hand ([classes.csv](out-detect/classes.csv)).

[class-summary.md](out-detect/class-summary.md):

| Class | top1k (n=281) | top10k (n=390) | top100k (n=387) | top1M (n=395) | rest (n=397) | Extrapolated % of Intl pages | % of all root pages |
|---|---|---|---|---|---|---|---|
| any read | 52 | 67 | 76 | 70 | 89 | 22.1 (18.1–26.5) | 6.82 |
| tag-sensitive | 0 | 0 | 3 | 0 | 0 | 0.0 (0.0–0.9) | 0.00 |
| fallback-probe | 1 | 2 | 3 | 2 | 0 | 0.0 (0.0–1.0) | 0.01 |
| passthrough | 4 | 5 | 9 | 9 | 28 | 6.7 (4.5–9.6) | 2.07 |
| bot-or-fraud | 35 | 40 | 49 | 36 | 34 | 8.6 (6.1–11.8) | 2.66 |
| fingerprint-id | 9 | 17 | 9 | 20 | 18 | 4.6 (2.7–7.1) | 1.40 |
| analytics | 3 | 1 | 1 | 2 | 8 | 1.9 (0.8–3.8) | 0.59 |
| language-only | 0 | 0 | 0 | 0 | 1 | 0.2 (0.0–1.4) | 0.07 |
| unclear | 0 | 2 | 2 | 1 | 0 | 0.0 (0.0–1.0) | 0.01 |

Stratum sizes (root pages / with an Intl counter): top1k 568/285, top10k 5370/2696, top100k 53731/23479, top1M 587034/217810, rest 10741335/3270652. Intervals: per-stratum Clopper–Pearson bounds summed (conservative).


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

## Not covered

- Workers (not traced), code that runs after interaction (see Recall), logged-in pages.
- Whether bot challenges and fraud scoring react to a changed locale: challenges don't complete during load-only visits (see Pilot).
- Server-side use of values sent by bot-defense and fraud scripts: a changed locale only shows in challenge or checkout outcomes, which the A/B comparison will look at.
- Safari.

## Query bytes

All on the 2026-11-01 crawl, run on 2026-11-25:

| Query | Bytes processed (TiB) |
|---|---|
| [latest_date.sql](queries/latest_date.sql) | 0.005 |
| [sample.sql](queries/sample.sql) | 0.189 |

## Reproduce

This run was done with version 0.35.0 (a87e8bc) of the [`httparchive` skill](https://github.com/zcorpan/web-platform-skills/blob/main/docs/httparchive.md). The steps below are standalone and rerun the same analysis without the skill.

```sh
bq query --use_legacy_sql=false --format=csv --max_rows=1000000 < queries/hits.sql > queries/hits.csv
python3 sample.py queries/hits.csv sample.jsonl <seed> <n> <stratum-columns...>
python3 -m venv .venv && .venv/bin/pip install playwright pillow nudenet pyobjc-framework-Vision  # Vision for ocr_check.py on macOS; elsewhere install tesseract. No `playwright install`: the scripts drive an installed Chrome
.venv/bin/python compare.py "$CHROME" sample.jsonl out
.venv/bin/python nsfw_check.py out
.venv/bin/python analyze.py out
# review out/review/*.png by hand and fill in the empty ratings in out/review.csv
python3 extrapolate.py out/review.csv sample.jsonl > out/summary.md
.venv/bin/python recheck.py "$CHROME" <url> <desktop|mobile> <out.png>
```

<!-- Browser, Playwright, and Pillow versions; anything that changed during the run (run.log);
     that live pages change, so a rerun won't match exactly; that screenshots (out*/shots/)
     aren't committed and compare.py regenerates them. -->

## License

MIT, see [LICENSE](LICENSE), for the scripts, analysis and text written for this research. Content from the crawl and the live web (`queries/`, `crawl/`, screenshots, page snippets) and third-party code (`vendor/`) belongs to its owners and isn't covered.

<!-- If the repo has patches to a browser (changes to an engine's code), add the line: Patches are under the license of the code they modify. -->
