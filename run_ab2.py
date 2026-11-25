"""Run Henri's A/B configurations for one browser in sequence (resumable; each runner skips done pages).

usage: .venv/bin/python run_ab2.py chrome|firefox out-ab-henri
"""
import subprocess, sys

RUNS = [('b3', 'en-US', 'B3'), ('b3', 'zh-TW', 'B3'), ('b3', 'pt-BR', 'B3'),
        ('collator', 'en-US', 'C1'), ('collator', 'zh-CN', 'C1'), ('collator', 'zh-TW', 'C2'),
        ('segmenter', 'en-US', 'SU'), ('segmenter', 'en-US', 'SL')]
browser, out = sys.argv[1], sys.argv[2]
for pages, locale, variant in RUNS:
    cmd = (['.venv/bin/python', 'ab.py', 'chrome', locale, variant] if browser == 'chrome' else
           ['.venv/bin/python', 'ab_fx.py', locale, variant]) + [f'ab/pages-{pages}.jsonl', out, '--concurrency', '4' if browser == 'chrome' else '5']
    print(' '.join(cmd), flush=True)
    with open(f'{out}/run-{browser}-{locale}-{variant}.log', 'a') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
