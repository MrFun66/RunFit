import io,re
a=io.open("app/api.py",encoding="utf-8").read()
i=a.find("def _user_profile")
print(a[i:i+1600])
