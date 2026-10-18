import io,re
p="app/api.py"
a=io.open(p,encoding="utf-8").read()
orig=len(a)

# 1) 删除第二处重复的 GET /foods（docstring "搜索内置食物库"）
dup2 = '''@router.get("/foods")
def list_foods(q: str = Query(""), limit: int = Query(80, ge=1, le=300)):
    """搜索内置食物库。空 q 返回常用前 N 条。"""
    items = foods.search(q, limit)
    return {"count": len(items), "items": items}


'''
if dup2 in a:
    a = a.replace(dup2, "", 1)
    print("[1] removed dup /foods (count version)")

io.open(p,"w",encoding="utf-8",newline="\n").write(a)
print("len", orig, "->", len(a))
