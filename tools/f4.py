import io,re
s=io.open("app/sync_api.py",encoding="utf-8").read()
print("settings imported:", "from .config import settings" in s or "import settings" in s)
m=re.search(r'^(from|import).*settings.*$', s, re.M)
print("import line:", m.group(0) if m else "NOT FOUND")
