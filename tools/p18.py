import io,re
a=io.open("app/api.py",encoding="utf-8").read()
print("LEN",len(a),"| foods count",a.count("/foods"),"| import foods:", "import foods" in a or "from . import foods" in a)
for m in re.finditer(r'@router\.(get|post)\("(/foods[^"]*|/meals/from-food[^"]*)"\)', a):
    print("ROUTE",m.group(1).upper(),m.group(2),"@",m.start())
