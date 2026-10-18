import io, ast
p = r"D:\GRF\app\sync_api.py"
s = io.open(p, encoding="utf-8").read()
if '"/alive"' in s:
    print("already exists")
else:
    anchor = '@router.get("/ping")'
    idx = s.find(anchor)
    assert idx > 0, "anchor not found"
    block = '''@router.get("/alive")
def alive():
    """无鉴权连通性检查：手机 Safari 打开这个地址，能返回 JSON 说明网络通。"""
    return {"ok": True, "app": "GRF", "msg": "network ok"}


'''
    s = s[:idx] + block + s[idx:]
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("inserted len", len(s))
ast.parse(io.open(p, encoding="utf-8").read())
print("AST_OK")
