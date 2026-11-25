"""Update status.html: python3 status.py <emoji> <status line> <now> <findings>"""
import html, re, sys
emoji, status, now, findings = sys.argv[1:5]
p = 'status.html'
s = open(p, encoding='utf-8').read()
s = s.replace('REPO', 'intl-compat')
s = re.sub(r'<title>.*?</title>', f'<title>{html.escape(status)} · intl-compat</title>', s)
s = re.sub(r"font-size='90'>.*?</text>", f"font-size='90'>{emoji}</text>", s)
s = re.sub(r'<p><b>[^<]*</b>\n<p><a', f'<p><b>{emoji} {html.escape(status)}</b>\n<p><a', s)
s = re.sub(r'<p><b>Now:</b>.*', f'<p><b>Now:</b> {html.escape(now)}', s)
s = re.sub(r'<p><b>Findings so far:</b>.*', f'<p><b>Findings so far:</b> {html.escape(findings)}', s)
open(p, 'w', encoding='utf-8').write(s)
