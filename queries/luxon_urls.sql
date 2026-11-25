-- Root pages (desktop, 2026-11-01) loading a script whose URL marks a known Luxon carrier or the
-- tag-sensitive Shopify IP blocker. Bundled Luxon (first-party chunks) isn't findable this way.
SELECT page, ANY_VALUE(rank) AS rank,
  STRING_AGG(DISTINCT CASE
    WHEN REGEXP_CONTAINS(url, r'(?i)luxon') THEN 'luxon-url'
    WHEN REGEXP_CONTAINS(url, r'elfsight\.com/apps/google-reviews') THEN 'elfsight-reviews'
    WHEN REGEXP_CONTAINS(url, r'apps\.mews\.com/distributor') THEN 'mews'
    WHEN REGEXP_CONTAINS(url, r'cdn\.botpress\.cloud/webchat') THEN 'botpress'
    WHEN REGEXP_CONTAINS(url, r'cdn\.shopify\.com/extensions/.*ip-blocke') THEN 'blockify'
  END) AS marks,
  ANY_VALUE(url) AS example_url
FROM `httparchive.crawl.requests`
WHERE date = '2026-11-01' AND client = 'desktop' AND is_root_page AND type = 'script'
  AND REGEXP_CONTAINS(url, r'(?i)luxon|elfsight\.com/apps/google-reviews|apps\.mews\.com/distributor|cdn\.botpress\.cloud/webchat|cdn\.shopify\.com/extensions/.*ip-blocke')
GROUP BY page
