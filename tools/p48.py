import io,re
p="app/api.py"
a=io.open(p,encoding="utf-8").read()
orig=len(a)

# 删掉第二处重复 GET /foods（docstring "食物库搜索。返回每 100g 的营养值 + 常见一份的克数。"）
dup = '''@router.get("/foods")
def list_foods(q: str = Query(""), limit: int = Query(80, ge=1, le=300)):
    """食物库搜索。返回每 100g 的营养值 + 常见一份的克数。"""
    return {"items": foods.search(q, limit=limit)}


'''
if dup in a:
    a=a.replace(dup,"",1); print("[1] removed dup /foods (items-only)")

# 删掉第三处重复 GET /foods（search_foods）
m=re.search(r'@router\.get\("/foods"\)\ndef search_foods\([^)]*\):\n(?:.*?\n)*?    return [^\n]*\n\n\n', a)
if m:
    print("[2] removing search_foods block:", m.start(), m.group(0)[:80].replace("\n"," "))
    a = a[:m.start()] + a[m.end():]
else:
    print("[2] search_foods block not matched")

io.open(p,"w",encoding="utf-8",newline="\n").write(a)
print("len",orig,"->",len(a))
