import io
s=io.open("app/config.py",encoding="utf-8").read() if __import__("os").path.exists("app/config.py") else ""
print("config.py len", len(s))
print(s[:2000])
