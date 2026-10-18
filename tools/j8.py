import io,re
s=io.open("web/assets/app.js",encoding="utf-8").read()
for k in ["openPortion","closePortion","initPortionPanel","_updatePortionPreview","_foodListCache","hasAny"]:
    print(k, s.count(k))
