# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(r"D:\GRF\web\index.html")
html = p.read_text(encoding="utf-8")
if 'id="tab-me"' in html:
    print("already present")
    raise SystemExit(0)

SEC = Path(r"D:\GRF\tools\_me_section.html").read_text(encoding="utf-8")
anchor = "        </main>"
if anchor not in html:
    raise SystemExit("no </main>")
html = html.replace(anchor, SEC + anchor, 1)
p.write_text(html, encoding="utf-8")
print("OK", len(html.encode("utf-8")))
print("tab-me:", 'id="tab-me"' in html)