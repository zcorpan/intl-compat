Desktop root pages, 2026-11-01 crawl; sample = pages hitting a Blink Intl constructor counter, loaded without errors. Class = most significant use on the page.

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
