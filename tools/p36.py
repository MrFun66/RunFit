import io,re
js=io.open("web/assets/app.js",encoding="utf-8").read()
print("js len",len(js))
i=js.find("function initModals")
print("initModals @",i)
print(js[i:i+1800] if i>0 else "NOT FOUND")
