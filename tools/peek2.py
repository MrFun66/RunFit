import io
p=r"D:\GRF\app\sync_api.py"
s=io.open(p,encoding="utf-8").read()
lines=s.split("\n")
print("total lines", len(lines))
for i in range(385, 460):
    if i-1 < len(lines):
        print(i, "|", lines[i-1])
