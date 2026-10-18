import io,re
a=io.open("app/api.py",encoding="utf-8").read()
for m in re.finditer(r'@router\.(get|post)\("(/foods[^"]*|/meals/from-foods?)"\)\ndef (\w+)', a):
    print(m.start(), m.group(1).upper(), m.group(2), "->", m.group(3))
