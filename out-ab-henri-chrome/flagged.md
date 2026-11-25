Each page was loaded three times per run: A and A2 as a user with that locale, B the same with the option
applied to `resolvedOptions().locale` (see the README). Listed: pages where B differs from A by more than A2 does.
Flags: `text x→y` is the page-text similarity A↔A2 → A↔B (1 = identical); `pixels x→y` the share of differing
screenshot pixels A↔A2 → A↔B; `new errors` JS errors only in B; `rewrites` the reads B changed. Classes as in the
README, plus `locale-unsettled` (an `Intl.Locale` use reviewers couldn't settle) and `luxon-static` (Luxon found in
the response bodies). Flagged doesn't mean broken: each was checked by hand, and the README lists what B changed.

## chrome en-US B3: 189 pages, B rewrote a read on 133, 3 failed in all visits, 29 flagged

| idx | class | rewrites | flags |
|---|---|---|---|
| 54 | language-only | 1 | text 1.0→0.94; pixels 0.0→0.1942 |
| 393 | passthrough | 2 | pixels 0.105→0.1617 |
| 1138 | unclear | 2 | pixels 0.0002→0.222 |
| 1307 | tag-sensitive | 0 | pixels 0.0→0.0471 |
| 2033 | passthrough | 2 | text 1.0→0.94; pixels 0.0→0.3264 |
| 2230 | locale-unsettled | 21 | pixels 0.001→0.0772 |
| 4096 | passthrough | 1 | pixels 0.0→0.1921 |
| 4857 | locale-unsettled | 4 | 1 new errors |
| 5291 | tag-sensitive | 3 | pixels 0.0→0.1785 |
| 5803 | tag-sensitive | 0 | 1 new errors |
| 6101 | tag-sensitive | 0 | text 0.687→0.628 |
| 6219 | unclear | None | B load error |
| 6618 | tag-sensitive | 12 | 2 new errors |
| 6886 | passthrough | 2 | text 0.723→0.664; pixels 0.0222→0.1098 |
| 7338 | tag-sensitive | 2 | text 1.0→0.972; 2 new errors |
| 7738 | passthrough | 1 | pixels 0.1923→0.2126 |
| 7920 | tag-sensitive | 2 | pixels 0.0229→0.099 |
| 8328 | tag-sensitive | 2 | text 0.97→0.911 |
| 8896 | tag-sensitive | 0 | 1 new errors |
| 9499 | tag-sensitive | 3 | pixels 0.0566→0.1022 |
| 10222 | passthrough | 3 | pixels 0.0005→0.0333 |
| 10415 | locale-unsettled | 0 | pixels 0.0→0.1483 |
| 11081 | passthrough | 1 | pixels 0.0228→0.0706 |
| 11555 | tag-sensitive | 2 | pixels 0.0099→0.1922 |
| 100007 | luxon-static | 0 | 1 new errors |
| 100008 | luxon-static | 2 | pixels 0.036→0.074 |
| 100016 | luxon-static | 0 | 2 new errors |
| 100020 | luxon-static | 0 | text 1.0→0.641; pixels 0.0001→0.1066 |
| 100022 | luxon-static | 5 | 1 new errors |

## chrome en-US C1: 95 pages, B rewrote a read on 34, 2 failed in all visits, 21 flagged

| idx | class | rewrites | flags |
|---|---|---|---|
| 309 | bot-or-fraud | 0 | text 0.872→0.835; pixels 0.2259→0.267; 1 new errors |
| 1084 | bot-or-fraud | 0 | pixels 0.0→0.4464 |
| 2155 | fallback-probe | 1 | pixels 0.0→0.0662 |
| 3923 | bot-or-fraud | 0 | text 1.0→0.0 |
| 4742 | bot-or-fraud | 0 | text 1.0→0.922; 1 new errors |
| 5667 | bot-or-fraud | 0 | pixels 0.0001→0.1188 |
| 5951 | fallback-probe | 1 | pixels 0.0019→0.0545 |
| 6536 | bot-or-fraud | 0 | pixels 0.0658→0.0882 |
| 6835 | bot-or-fraud | 0 | 1 new errors |
| 6891 | bot-or-fraud | 0 | pixels 0.0→0.0831 |
| 7148 | bot-or-fraud | 0 | pixels 0.0→0.0233 |
| 7302 | bot-or-fraud | 0 | 2 new errors |
| 7896 | bot-or-fraud | 0 | 1 new errors |
| 8926 | fallback-probe | 1 | pixels 0.0024→0.1735 |
| 9893 | fallback-probe | 1 | text 1.0→0.734 |
| 10053 | bot-or-fraud | 0 | pixels 0.0→0.1417 |
| 10195 | fallback-probe | 1 | text 1.0→0.899 |
| 11460 | bot-or-fraud | 0 | 1 new errors |
| 11598 | fallback-probe | 1 | pixels 0.1338→0.1553 |
| 12269 | bot-or-fraud | 0 | text 0.84→0.779 |
| 12377 | bot-or-fraud | 0 | 1 new errors |

## chrome en-US SL: 30 pages, B rewrote a read on 27, 1 failed in all visits, 3 flagged

| idx | class | rewrites | flags |
|---|---|---|---|
| 4626 | fallback-probe | 1 | 1 new errors |
| 7728 | fallback-probe | 1 | pixels 0.1767→0.2228 |
| 9893 | fallback-probe | 1 | pixels 0.1422→0.1784 |

## chrome en-US SU: 30 pages, B rewrote a read on 26, 1 failed in all visits, 5 flagged

| idx | class | rewrites | flags |
|---|---|---|---|
| 4626 | fallback-probe | 1 | 1 new errors |
| 5272 | fallback-probe | 1 | text 0.963→0.084; pixels 0.346→0.9346; 1 new errors |
| 5951 | fallback-probe | 1 | pixels 0.0649→0.091 |
| 6411 | fallback-probe | 0 | text 0.988→0.573; 1 new errors |
| 9893 | fallback-probe | 1 | text 1.0→0.782; pixels 0.0965→0.2898 |

## chrome pt-BR B3: 189 pages, B rewrote a read on 132, 5 failed in all visits, 34 flagged

| idx | class | rewrites | flags |
|---|---|---|---|
| 958 | tag-sensitive | 4 | 1 new errors |
| 1725 | passthrough | 2 | text 1.0→0.064; pixels 0.0→0.0221; 1 new errors |
| 1822 | passthrough | 2 | 1 new errors |
| 2230 | locale-unsettled | 24 | pixels 0.0007→0.0762 |
| 2836 | language-only | 30 | text 1.0→0.972 |
| 3252 | tag-sensitive | 2 | pixels 0.0036→0.0465 |
| 3886 | passthrough | 0 | text 1.0→0.972 |
| 4092 | passthrough | 0 | 1 new errors |
| 4096 | passthrough | 1 | 1 new errors |
| 4398 | passthrough | 2 | pixels 0.0031→0.2934 |
| 4516 | unclear | 5 | pixels 0.0→0.8084 |
| 4711 | tag-sensitive | 3 | pixels 0.0029→0.2208 |
| 4857 | locale-unsettled | 4 | 1 new errors |
| 5291 | tag-sensitive | 3 | pixels 0.0→0.1779 |
| 5311 | unclear | 2 | text 0.958→0.011; pixels 0.0006→0.9917; 1 new errors |
| 5369 | tag-sensitive | 0 | pixels 0.1414→0.1674 |
| 6101 | tag-sensitive | 0 | text 0.693→0.668 |
| 6140 | locale-unsettled | 2 | text 1.0→0.002; pixels 0.0→0.4791; 1 new errors |
| 6360 | locale-unsettled | 2 | pixels 0.0694→0.2265 |
| 6618 | tag-sensitive | 12 | 2 new errors |
| 6886 | passthrough | 2 | text 0.746→0.38 |
| 7738 | passthrough | 1 | text 0.726→0.666 |
| 8328 | tag-sensitive | 2 | text 0.984→0.932 |
| 10246 | unclear | 0 | pixels 0.0→0.3273 |
| 11081 | passthrough | 1 | pixels 0.0133→0.2639 |
| 11341 | tag-sensitive | 6 | 1 new errors |
| 11514 | passthrough | 3 | text 1.0→0.444 |
| 11555 | tag-sensitive | 2 | pixels 0.0013→0.0599; 1 new errors |
| 12071 | passthrough | 3 | pixels 0.044→0.1907 |
| 100010 | luxon-static | 1 | 1 new errors |
| 100011 | luxon-static | 1 | text 0.931→0.906; pixels 0.0322→0.0658 |
| 100022 | luxon-static | 5 | text 1.0→0.813; pixels 0.1887→0.5088 |
| 100030 | luxon-static | 0 | pixels 0.0→0.0211 |
| 100035 | luxon-static | 3 | text 0.805→0.774; pixels 0.0053→0.1189 |

## chrome zh-CN C1: 95 pages, B rewrote a read on 33, 4 failed in all visits, 19 flagged

| idx | class | rewrites | flags |
|---|---|---|---|
| 309 | bot-or-fraud | 0 | pixels 0.0481→0.2875 |
| 1084 | bot-or-fraud | 0 | pixels 0.0→0.0322 |
| 1420 | bot-or-fraud | 0 | pixels 0.0002→0.276 |
| 3033 | bot-or-fraud | 0 | 2 new errors |
| 3595 | bot-or-fraud | 0 | 4 new errors |
| 3801 | fallback-probe | 1 | 1 new errors |
| 4742 | bot-or-fraud | 0 | 1 new errors |
| 5272 | fallback-probe | 1 | 2 new errors |
| 5617 | bot-or-fraud | 0 | pixels 0.0031→0.0892 |
| 5649 | fallback-probe | 1 | 1 new errors |
| 6536 | bot-or-fraud | 0 | text 1.0→0.826; pixels 0.0→0.4245; 2 new errors |
| 6675 | bot-or-fraud | 0 | pixels 0.0→0.0366 |
| 7126 | bot-or-fraud | 0 | 1 new errors |
| 7728 | fallback-probe | 1 | pixels 0.1907→0.2194 |
| 7896 | bot-or-fraud | 0 | 1 new errors |
| 8476 | fallback-probe | 1 | pixels 0.0001→0.0311 |
| 11291 | fallback-probe | 1 | 2 new errors |
| 11559 | bot-or-fraud | 0 | text 1.0→0.974 |
| 11598 | fallback-probe | 1 | pixels 0.0267→0.167 |

## chrome zh-TW B3: 189 pages, B rewrote a read on 131, 3 failed in all visits, 30 flagged

| idx | class | rewrites | flags |
|---|---|---|---|
| 430 | passthrough | 0 | 1 new errors |
| 1138 | unclear | 2 | pixels 0.0046→0.0431 |
| 1985 | passthrough | 2 | pixels 0.22→0.2985 |
| 2655 | tag-sensitive | 2 | pixels 0.0817→0.1079 |
| 2836 | language-only | 30 | pixels 0.0026→0.035 |
| 3595 | passthrough | 0 | pixels 0.0056→0.0337 |
| 4857 | locale-unsettled | 4 | 1 new errors |
| 5369 | tag-sensitive | 0 | 1 new errors |
| 7920 | tag-sensitive | 2 | pixels 0.0414→0.1151 |
| 8896 | tag-sensitive | None | B load error; text 0.993→0.0; status 200→None |
| 9499 | tag-sensitive | 3 | pixels 0.1418→0.2224 |
| 9826 | unclear | 0 | text 1.0→0.889 |
| 9854 | unclear | 2 | pixels 0.0041→0.0801 |
| 9876 | tag-sensitive | None | B load error; text 1.0→0.0; status 200→None |
| 9959 | unclear | None | B load error; text 1.0→0.0 |
| 10460 | tag-sensitive | 2 | 2 new errors |
| 10552 | tag-sensitive | 3 | pixels 0.0301→0.1021 |
| 10767 | tag-sensitive | 5 | 1 new errors |
| 10792 | passthrough | 2 | pixels 0.0149→0.1171 |
| 11513 | tag-sensitive | 0 | pixels 0.0→0.2569 |
| 11914 | passthrough | 0 | pixels 0.0156→0.0503 |
| 100004 | luxon-static | 1 | text 1.0→0.89 |
| 100008 | luxon-static | 3 | 4 new errors |
| 100010 | luxon-static | 1 | text 0.985→0.89 |
| 100011 | luxon-static | 1 | text 0.941→0.904; pixels 0.0265→0.0591 |
| 100019 | luxon-static | 0 | pixels 0.0→0.0513 |
| 100023 | luxon-static | 0 | 1 new errors |
| 100024 | luxon-static | 0 | text 1.0→0.944 |
| 100035 | luxon-static | 2 | text 0.961→0.938 |
| 100038 | luxon-static | 0 | pixels 0.0011→0.1973 |

## chrome zh-TW C2: 95 pages, B rewrote a read on 31, 3 failed in all visits, 20 flagged

| idx | class | rewrites | flags |
|---|---|---|---|
| 1420 | bot-or-fraud | 0 | pixels 0.0→0.2761 |
| 3033 | bot-or-fraud | 0 | 1 new errors |
| 3595 | bot-or-fraud | 0 | pixels 0.0033→0.0286 |
| 4626 | fallback-probe | 1 | text 1.0→0.589; pixels 0.1255→0.1862 |
| 4742 | bot-or-fraud | 0 | text 1.0→0.922; pixels 0.0→0.2365 |
| 5649 | fallback-probe | 1 | text 1.0→0.199; pixels 0.0107→0.651 |
| 6128 | bot-or-fraud | 0 | 16 new errors |
| 6411 | fallback-probe | 0 | text 0.988→0.955; pixels 0.0239→0.0781; 1 new errors |
| 7126 | bot-or-fraud | 0 | 1 new errors |
| 7896 | bot-or-fraud | 0 | 2 new errors |
| 8813 | bot-or-fraud | 0 | text 0.944→0.846 |
| 9105 | fallback-probe | 1 | 1 new errors |
| 9804 | bot-or-fraud | 0 | text 1.0→0.454; pixels 0.0→0.2617 |
| 10053 | bot-or-fraud | 0 | pixels 0.0006→0.1542 |
| 11461 | bot-or-fraud | 0 | pixels 0.0→0.0785 |
| 11559 | bot-or-fraud | 0 | 2 new errors |
| 11701 | bot-or-fraud | 0 | pixels 0.1048→0.2328 |
| 12269 | bot-or-fraud | 0 | text 0.775→0.685; 1 new errors |
| 12336 | bot-or-fraud | 0 | text 0.652→0.617 |
| 12377 | bot-or-fraud | 0 | pixels 0.0→0.4013 |

