import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
# 看当前 handler 里 payload / workouts 的取法
i=s.find('payload = body.get("data")')
print(s[i-300:i+400])
print("---- workouts 处理 ----")
j=s.find('workouts = payload.get("workouts")')
print(s[j:j+300])
