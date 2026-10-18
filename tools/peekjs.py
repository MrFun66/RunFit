import io, re
q=r"D:\GRF\web\assets\app.js"
t=io.open(q,encoding="utf-8").read()
i=t.find("async function loadSyncConfig")
print("idx",i)
print(t[i-1200:i+2600])
