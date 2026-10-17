import io,re
s=io.open("app/api.py",encoding="utf-8").read()
for m in re.finditer(r'^from .*import .*$|^import .*$', s[:4000], re.M):
    print(m.group(0))
print("---- models used ----")
print("Exercise" in s, "WorkoutSet" in s, "select(" in s)
i=s.find("class Exercise")
print(s[i:i+500] if i>=0 else "no class Exercise in api.py")
