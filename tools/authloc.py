import io,re
s=io.open("web/assets/app.js",encoding="utf-8").read()
for k in ["登录失败","注册失败","A request","auth/login","auth/register","passkey","Passkey","navigator.credentials","api/auth"]:
    for m in re.finditer(re.escape(k), s):
        print(k, m.start())
