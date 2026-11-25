"""Firefox's locale lists in the parent process vs the JS default locale in web content.

usage: .venv/bin/python env_fx_locales.py [-AppleLanguages '(en-FI)']
"""
import sys
from selenium import webdriver
o = webdriver.FirefoxOptions(); o.binary_location = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
o.add_argument('-headless')
for a in sys.argv[1:]: o.add_argument(a)
from selenium.webdriver.firefox.service import Service
d = webdriver.Firefox(options=o, service=Service(service_args=['--allow-system-access']))
try:
    d.get('about:blank')
    content = d.execute_script('return new Intl.DateTimeFormat().resolvedOptions().locale')
    with d.context(d.CONTEXT_CHROME):
        print(sys.argv[1:], d.execute_script('return [Services.locale.regionalPrefsLocales, Services.locale.appLocalesAsBCP47, Services.locale.requestedLocales, Cc["@mozilla.org/intl/ospreferences;1"].getService(Ci.mozIOSPreferences).systemLocales, Cc["@mozilla.org/intl/ospreferences;1"].getService(Ci.mozIOSPreferences).regionalPrefsLocales, new Intl.DateTimeFormat().resolvedOptions().locale]'), 'content:', content)
finally:
    d.quit()
