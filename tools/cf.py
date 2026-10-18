import io
# 查看 cloudflared 隧道日志（如果有）
import os, glob
cands = glob.glob(r"D:\GRF\logs\*") + glob.glob(r"D:\GRF\*.log") + glob.glob(r"C:\Users\Administrator\.cloudflared\*.log")
for c in cands[:20]:
    print(c, os.path.getsize(c))
