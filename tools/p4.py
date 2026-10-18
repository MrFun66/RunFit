import io
s=io.open("app/parsers.py",encoding="utf-8").read()
i=s.find("def parse_apple_export")
print("len",len(s),"idx",i)
print(s[i-1500:i+4500])
