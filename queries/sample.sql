-- Seeded sample of desktop root pages (2026-11-01 crawl) that hit any Blink Intl constructor counter
-- (Collator 2593 ... Segmenter 2600, DisplayNames 3172; V8 counts them at the start of each constructor).
-- 400 pages per rank stratum, with stratum sizes for extrapolation. `intl` lists the counter ids hit.
WITH p AS (
  SELECT page, rank,
    CASE WHEN rank <= 1000 THEN 'top1k' WHEN rank <= 10000 THEN 'top10k' WHEN rank <= 100000 THEN 'top100k'
         WHEN rank <= 1000000 THEN 'top1M' ELSE 'rest' END AS stratum,
    ARRAY(SELECT f.id FROM UNNEST(features) f
          WHERE f.type = 'default' AND f.id IN ('2593','2594','2595','2596','2597','2598','2599','2600','3172')
          ORDER BY f.id) AS intl
  FROM `httparchive.crawl.pages`
  WHERE date = '2026-11-01' AND client = 'desktop' AND is_root_page
), s AS (
  SELECT *, COUNT(*) OVER (PARTITION BY stratum) AS stratum_pages,
    COUNTIF(ARRAY_LENGTH(intl) > 0) OVER (PARTITION BY stratum) AS stratum_intl_pages
  FROM p
)
SELECT page, rank, stratum, ARRAY_TO_STRING(intl, ' ') AS intl, stratum_pages, stratum_intl_pages
FROM s WHERE ARRAY_LENGTH(intl) > 0
QUALIFY ROW_NUMBER() OVER (PARTITION BY stratum ORDER BY FARM_FINGERPRINT(CONCAT(page, 'intl-compat-1'))) <= 400
ORDER BY stratum, FARM_FINGERPRINT(CONCAT(page, 'intl-compat-1'))
