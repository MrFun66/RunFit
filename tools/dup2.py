import io
s=io.open("web/assets/app.js",encoding="utf-8").read()
i=s.find("function renderStrengthChart")
print(s[i:i+300])
print("---- occurrence2 ----")
i2=s.find("function renderStrengthChart", i+10)
print("second at", i2)
