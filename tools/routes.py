import re
p = r"D:\GRF\app\sync_api.py"
s = open(p, encoding="utf-8").read()
for m in re.finditer(r'@router\.(get|post|delete)\("([^"]+)"', s):
    print(m.group(1).upper(), m.group(2))
print("has debug:", "/debug" in s)
print("len:", len(s))
