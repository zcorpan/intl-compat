-- Extension of sample.sql (same crawl, seed and ordering, so its pages come first): more pages per
-- rank stratum, plus two targeted strata among Intl pages: WebDX LocaleInfoFunctions (id 244;
-- Intl.Locale getWeekInfo(), getHourCycles() etc., which depend on the region) and Intl.Locale (2598).
-- `pick` says which selections a page is in; counts give each stratum's size for extrapolation.
WITH p AS (
  SELECT page, rank,
    CASE WHEN rank <= 1000 THEN 'top1k' WHEN rank <= 10000 THEN 'top10k' WHEN rank <= 100000 THEN 'top100k'
         WHEN rank <= 1000000 THEN 'top1M' ELSE 'rest' END AS stratum,
    ARRAY(SELECT f.id FROM UNNEST(features) f
          WHERE f.type = 'default' AND f.id IN ('2593','2594','2595','2596','2597','2598','2599','2600','3172')
          ORDER BY f.id) AS intl,
    EXISTS(SELECT 1 FROM UNNEST(features) f WHERE f.type = 'webdx' AND f.id = '244') AS locale_info
  FROM `httparchive.crawl.pages`
  WHERE date = '2026-11-01' AND client = 'desktop' AND is_root_page
), counts AS (
  SELECT stratum, COUNT(*) AS stratum_pages, COUNTIF(ARRAY_LENGTH(intl) > 0) AS stratum_intl_pages,
    COUNTIF(ARRAY_LENGTH(intl) > 0 AND locale_info) AS stratum_locale_info_pages,
    COUNTIF('2598' IN UNNEST(intl)) AS stratum_intl_locale_pages
  FROM p GROUP BY stratum
), i AS (
  SELECT page, rank, stratum, intl, ARRAY_TO_STRING(intl, ' ') AS intl_s, locale_info, FARM_FINGERPRINT(CONCAT(page, 'intl-compat-1')) AS h
  FROM p WHERE ARRAY_LENGTH(intl) > 0
), r AS (
  SELECT page, 'random' AS pick FROM i
  QUALIFY ROW_NUMBER() OVER (PARTITION BY stratum ORDER BY h) <=
    CASE stratum WHEN 'top1k' THEN 1000 WHEN 'top10k' THEN 10000 WHEN 'top100k' THEN 3000 ELSE 2000 END
  UNION ALL
  SELECT page, 'locale_info' FROM i WHERE locale_info QUALIFY ROW_NUMBER() OVER (ORDER BY h) <= 1500
  UNION ALL
  SELECT page, 'intl_locale' FROM i WHERE '2598' IN UNNEST(intl) QUALIFY ROW_NUMBER() OVER (ORDER BY h) <= 1500
)
SELECT i.page, i.rank, i.stratum, i.intl_s AS intl, i.locale_info,
  STRING_AGG(r.pick, ' ' ORDER BY r.pick) AS pick, ANY_VALUE(c.stratum_pages) AS stratum_pages,
  ANY_VALUE(c.stratum_intl_pages) AS stratum_intl_pages, ANY_VALUE(c.stratum_locale_info_pages) AS stratum_locale_info_pages,
  ANY_VALUE(c.stratum_intl_locale_pages) AS stratum_intl_locale_pages, ANY_VALUE(i.h) AS h
FROM r JOIN i USING (page) JOIN counts c ON c.stratum = i.stratum
GROUP BY i.page, i.rank, i.stratum, i.intl_s, i.locale_info
ORDER BY i.stratum, h
