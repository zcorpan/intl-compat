"""Run env/passback.js in Chrome: does passing the reported locale back to Intl format the same?
(passback_fx.py does the same in Firefox; separate so a staged Firefox update doesn't block this.)

usage: .venv/bin/python passback.py > env/passback-chrome.jsonl
"""
import asyncio, json
from playwright.async_api import async_playwright
from harness import here

CHROME = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
JS = open(here('env', 'passback.js')).read()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME)
        pg = await b.new_page()
        await pg.goto('about:blank')
        await pg.add_script_tag(content=JS)
        rows = await pg.evaluate('window.__passback()')
        for r in rows:
            print(json.dumps({'browser': 'chrome', 'version': b.version, **r}, ensure_ascii=False))
        await b.close()


asyncio.run(main())
