"""Run env/passback.js in Firefox Nightly (see passback.py).

usage: .venv/bin/python passback_fx.py > env/passback-firefox.jsonl
"""
import json
from selenium import webdriver
from harness import here

FIREFOX = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
JS = open(here('env', 'passback.js')).read()

o = webdriver.FirefoxOptions()
o.binary_location = FIREFOX
o.add_argument('-headless')
d = webdriver.Firefox(options=o)
try:
    d.get('about:blank')
    rows = d.execute_script(JS + '; return window.__passback()')
    for r in rows:
        print(json.dumps({'browser': 'firefox', 'version': d.capabilities['browserVersion'], **r}, ensure_ascii=False))
finally:
    d.quit()
