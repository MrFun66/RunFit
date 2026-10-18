import io,re
js=io.open("web/assets/app.js",encoding="utf-8").read()
i=js.find("const API")
print("=== API helper ===")
print(js[i:i+900])
print()
i=js.find("async function initSyncCard")
print("=== initSyncCard idx",i,"===")
print(js[i:i+2600])
