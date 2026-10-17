import io,re
s=io.open("app/api.py",encoding="utf-8").read()
i=s.find("@router.get(\"/strength/trend\")")
j=s.find("@router.put(\"/workouts/{wid:int}\")")
print("start",i,"end",j)
print(s[i:i+200])
print("...")
print(s[j-200:j+80])
