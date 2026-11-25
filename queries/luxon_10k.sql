-- Root pages in the 10k sample (desktop) with a response body carrying Luxon's signature strings,
-- with the script URL, to measure how much Luxon the URL query misses.
SELECT page, rank, url, type, FARM_FINGERPRINT(response_body) AS h,
  REGEXP_CONTAINS(url, r'(?i)luxon|elfsight\.com/apps/google-reviews|apps\.mews\.com/distributor|cdn\.botpress\.cloud/webchat') AS url_marked
FROM `httparchive.sample_data.requests_10k`
WHERE client = 'desktop' AND is_root_page
  AND STRPOS(response_body, 'Invalid DateTime') > 0 AND STRPOS(response_body, 'Invalid Interval') > 0
  AND STRPOS(response_body, 'resolvedOptions().locale') > 0
