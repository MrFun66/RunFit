import io,re
a=io.open("app/api.py",encoding="utf-8").read()
print("=== routes now ===")
for m in re.finditer(r'@router\.(get|post|delete)\("(/foods[^"]*|/meals[^"]*)"\)\ndef (\w+)', a):
    print(" ", m.group(1).upper(), m.group(2), "->", m.group(3))
print("len", len(a))
