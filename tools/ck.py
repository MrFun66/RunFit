import io
h=io.open("web/index.html",encoding="utf-8").read()
print("len",len(h))
print("ends with </html>:", h.rstrip().endswith("</html>"))
for k in ["iPhone 健康同步","路线 A","路线 B","All Health Metrics","btn-sync-config","cfg-header","</body>"]:
    print("  ",k, k in h)
print("tab-nutrition:", 'id="tab-nutrition"' in h)
print("macro-body:", 'id="macro-body"' in h)
print("food-portion:", 'id="food-portion"' in h)
