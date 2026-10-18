import io,re
a=io.open("app/api.py",encoding="utf-8").read()
for m in re.finditer(r'@router\.(get|post)\("(/foods[^"]*)"\)\n(?:async )?def (\w+)', a):
    print(m.start(), m.group(1).upper(), m.group(2), "->", m.group(3))
    print("   ", repr(a[m.start():m.start()+260]))
print()
i=a.find('@router.get("/foods")')
print(a[i-900:i+900])
