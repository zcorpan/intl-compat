# Does the web care what `resolvedOptions().locale` returns?

<!-- Fill in or delete every comment and placeholder. Take each number from a committed file and
     say which. No billing project, account, job IDs, or costs; bytes processed only, in TiB. -->

Options under discussion (unicode-org/icu4x#8736, unicode-org/icu4x#5868, tc39/ecma402#947): ICU4X-based "best fit" locale resolution in engines, which would make ECMA-402 `Intl.*.prototype.resolvedOptions().locale` report less than today's ICU4C-shaped lookup: e.g. `en` instead of `en-US`, `zh-Hant` instead of `zh-TW` or `zh-HK`, and possibly something else for `Intl.Segmenter` and `Intl.Collator`. Formatting output would not change; only the reported locale would.

## Summary

<!-- Real cases, not argument structure. Typically: exposure (pages using the feature, % of the
     denominator); sample results by rating; extrapolated broken/worse with the denominator;
     what's behind broken and worse (sites, libraries, patterns, and fixes shipped upstream);
     how the field rate (use counters) compares with the crawl rate; anything the crawl can't size. -->

## Scope

- Questions: which pages read `resolvedOptions().locale`, from which service, after constructing with no locales argument or an explicit one; what they do with the value; whether pages break if the region is dropped (and `zh-TW`/`zh-HK` become `zh-Hant`); whether anything reads Segmenter's locale.
- Locale environments: Firefox Nightly and Chrome Canary on macOS, configured per process with real launch arguments where they reproduce a real setup; the per-page locale override (CDP/BiDi) only where they can't. Test locales: `en-US`, `en-GB`, `ar-SA`, `ar-EG`, `pt-BR`, `pt-PT`, `zh-CN`, `zh-TW`, `zh-HK`, `is-IS`, plus a mixed language/region setup (e.g. English UI with a non-English region). No VPN.
- Pages: 2000 desktop root pages from the latest HTTP Archive crawl that hit a Blink Intl constructor counter, seeded, stratified by rank. Detection in Chrome with a preload script that logs every read of `locale` on a `resolvedOptions()` result.
- Recall check: static scan of `httparchive.sample_data.requests_10k` bodies.
- Then: classify the uses by code review; stop for the variant definitions to be checked before the A/B comparison (A, A2 = locale L; B = same with `resolvedOptions().locale` rewritten per variant), Chrome first, then Firefox.
- Budget: 0.5 TiB of queries.

## What breaks and why

<!-- Only if something breaks: the cause, traced to the spec or engine code, and each variant
     measured against the change's goal, with the one you'd recommend. The sections below hold
     the data; don't repeat it here. -->

## 1. HTTP Archive

<!-- If a Common Crawl corpus was used too: crawl, seed, WARC count, HTML responses, and which
     numbers come from it (cc.py pick/download). Its pages aren't only root pages. -->

<!-- Crawl date, table, clients, root and/or non-root pages. Each query file, what it selects
     (use counters with where they're incremented, or custom metric fields with a link to the
     metric's source at a commit), and its output file. -->

| | desktop | mobile |
|---|---|---|
| Pages crawled | | |
| <condition> | | |

## 2. Live comparison on a sample

<!-- sample.py's strata, seed, and size (sample.jsonl). The browser and version; the before and
     after setups (flags, build, or emulation, from change.py); the sanity check. compare.py's
     visits: A and A2 before, B after, crawl-like viewports, waits, what's recorded (scrubbed at capture); output
     in out/results.jsonl. Adult pages flagged by nsfw_check.py (out/nsfw.csv). analyze.py's
     auto-ratings and how many pages were reviewed by hand (out/review/, out/review.csv);
     rechecks with recheck.py. -->

<!-- extrapolate.py output (out/summary.md): -->

| Stratum | Pages | Sampled | Broken | Worse | No visible change | Not assessable |
|---|---|---|---|---|---|---|

| Group | Broken | Worse | No visible change | Not assessable |
|---|---|---|---|---|

What's behind the ratings:

<!-- One bullet per stratum group and rating that matters: the pattern, named sites or
     libraries, the cause, and the review image (out/review/NNN.png) for the clearest case.
     Mark pages in out/nsfw.csv "(nsfw)" and link a repro test instead of an image. -->

## 3. Top-ranked pages

<!-- If the sample has few or no pages in the top rank buckets, run every top-ranked hit through
     the same steps (out-top<N>/) and report the results here. Otherwise delete this section. -->

## Not covered

<!-- What the crawl and this method can't see: pages the crawl doesn't visit, interaction,
     logged-in state, special cases in the change, other engines. -->

## Query bytes

All on the <crawl date> crawl, run on <date>:

| Query | Bytes processed (TiB) |
|---|---|

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
