import io
s=io.open("web/assets/app.js",encoding="utf-8").read()
print("LEN", len(s))
print("=== 1840-2100 region ===")
print(s[75000:79000])
