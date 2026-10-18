import io, re, ast
p = r"D:\GRF\app\sync_api.py"
s = io.open(p, encoding="utf-8").read()
orig = len(s)

def drop(s, deco):
    i = s.find(deco)
    if i < 0:
        return s, "not found"
    # find the next @router. after this decorator's block start
    j = s.find("\n@router.", i + len(deco))
    if j < 0:
        j = len(s)
    return s[:i] + s[j+1:], "removed %d chars" % (j - i)

for d in ('@router.post("/debug")', '@router.get("/shortcut")'):
    s, msg = drop(s, d)
    print(d, "->", msg)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
ast.parse(s)
print("AST_OK", orig, "->", len(s))
print("routes now:", re.findall(r'@router\.(get|post)\("([^"]+)"\)', s))
