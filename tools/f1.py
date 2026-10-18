import io
p="app/config.py"
s=io.open(p,encoding="utf-8").read()
if "PUBLIC_BASE_URL" not in s:
    old = '    SESSION_TTL_HOURS: int = int(os.getenv("GRF_SESSION_TTL_HOURS", "720"))  # 30 天'
    new = old + '\n    # 公网访问地址（手机端同步必须用这个，不能用 127.0.0.1）\n    PUBLIC_BASE_URL: str = os.getenv("GRF_PUBLIC_BASE_URL", "https://runfit.wenhh.top").rstrip("/")'
    assert old in s
    s = s.replace(old, new, 1)
    io.open(p,"w",encoding="utf-8",newline="\n").write(s)
    print("[config] PUBLIC_BASE_URL added")
else:
    print("[config] already present")
