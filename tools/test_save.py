import json, random, urllib.request, urllib.error, http.cookiejar

BASE = "http://127.0.0.1:7788"
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def call(path, method="GET", body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with op.open(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")[:300]
    except Exception as e:
        return -1, str(e)

u = "save_%d" % random.randint(10000, 99999)
print("register      :", call("/api/auth/register", "POST", {"username": u, "password": "Passw0rd!123"}))
print()
print("PUT profile   :", call("/api/profile", "PUT", {"sex":"male","birth_year":1995,"height_cm":178,"goal":"cut"}))
print("GET profile   :", call("/api/profile"))
print()
print("PUT llm       :", call("/api/settings/llm", "PUT", {"api_key":"sk-test1234567890abcdef","base_url":"https://api.deepseek.com","model":"deepseek-chat","vision_model":"deepseek-chat"}))
print("GET llm       :", call("/api/settings/llm"))
print()
print("PUT llm only key:", call("/api/settings/llm", "PUT", {"api_key":"sk-onlykey9876543210"}))
print("GET llm       :", call("/api/settings/llm"))
