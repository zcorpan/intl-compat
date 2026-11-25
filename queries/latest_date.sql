SELECT MAX(date) AS latest FROM `httparchive.crawl.pages` WHERE date >= '2026-08-01' AND client = 'desktop' AND is_root_page AND rank = 1000
