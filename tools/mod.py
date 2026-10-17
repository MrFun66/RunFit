import io
s=io.open("app/models.py",encoding="utf-8").read() if __import__("os").path.exists("app/models.py") else ""
print(len(s))
print(s[:1500])
