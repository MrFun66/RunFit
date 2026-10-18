import io
p=r"D:\GRF\app\sync_api.py"
s=io.open(p,encoding="utf-8").read()
i=s.find('def get_config')
print("idx",i)
print(s[i-200:i+1800] if i>0 else "NOT FOUND")
