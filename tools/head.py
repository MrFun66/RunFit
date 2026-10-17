import io
s=io.open("web/assets/app.js",encoding="utf-8").read()
print("LEN", len(s))
print("=== head 3000 ===")
print(s[:3000])
