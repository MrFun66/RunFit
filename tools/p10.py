import io,re
a=io.open("app/api.py",encoding="utf-8").read()
for kw in ["nutrition","food","macro","calorie"]:
    print("=== keyword:",kw,"count",a.lower().count(kw),"===")
for m in re.finditer(r'@router\.(get|post|put|delete)\("(/[^"]*(?:nutrition|food|meal|diet)[^"]*)"', a):
    print("ROUTE:",m.group(1).upper(),m.group(2), "@", m.start())
