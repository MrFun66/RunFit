import io
p="app/sync_api.py"
s=io.open(p,encoding="utf-8").read()
if "from .config import settings" not in s:
    # 在第一个 from . 导入后插入
    import re
    m=re.search(r'^from \.\w+ import .*$', s, re.M)
    if m:
        s = s[:m.end()] + "\nfrom .config import settings" + s[m.end():]
        print("[1] inserted after:", m.group(0))
    else:
        # 退而在 fastapi 导入行后插入
        m=re.search(r'^from fastapi import .*$', s, re.M)
        s = s[:m.end()] + "\n\nfrom .config import settings" + s[m.end():]
        print("[2] inserted after fastapi")
    io.open(p,"w",encoding="utf-8",newline="\n").write(s)
    print("len", len(s))
else:
    print("already imported")
import ast; ast.parse(io.open(p,encoding="utf-8").read()); print("AST_OK")
