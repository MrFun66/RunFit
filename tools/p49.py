import io,re,ast
a=io.open("app/api.py",encoding="utf-8").read()
print("=== routes ===")
for m in re.finditer(r'@router\.(get|post)\("(/foods[^"]*|/meals/from-food[s]?)"\)\ndef (\w+)', a):
    print(" ", m.group(1).upper(), m.group(2), "->", m.group(3))
ast.parse(a); print("AST_OK len", len(a))
