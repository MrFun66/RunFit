import re
s = open("web/index.html", encoding="utf-8").read()
print("size:", len(s))
print()
print("=== form tags ===")
for m in re.finditer(r"<form|</form>", s):
    print(" ", m.group(0), "at", m.start(), "line", s[:m.start()].count("\n")+1)
print()
print("=== sections ===")
for m in re.finditer(r'<section id="(tab-[a-z]+)"', s):
    print(" ", m.group(1), "line", s[:m.start()].count("\n")+1)
print()
print("=== nav buttons ===")
for m in re.finditer(r'data-target="([a-z]+)"', s):
    print(" ", m.group(1), "line", s[:m.start()].count("\n")+1)
print()
print("=== duplicate ids ===")
ids = re.findall(r'id="([^"]+)"', s)
from collections import Counter
for k, v in Counter(ids).items():
    if v > 1:
        print("  DUP:", k, v)
print()
print("=== save buttons ===")
for m in re.finditer(r'id="(btn-save-[a-z-]+|btn-ai-[a-z-]+|btn-pk-[a-z-]+)"', s):
    print(" ", m.group(1), "line", s[:m.start()].count("\n")+1)
