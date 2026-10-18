import io
p="app/sync_api.py"
s=io.open(p,encoding="utf-8").read()
orig=len(s)

# /config 里改用固定公网地址
old = '''    user = current_user(request, db)
    token = ensure_sync_token(db, user)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:7788"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    endpoint = "%s://%s/api/sync/health" % (proto, host)'''
new = '''    user = current_user(request, db)
    token = ensure_sync_token(db, user)
    # 手机端必须访问公网地址；本地调试时 request 头会是 127.0.0.1，不能用
    base = (getattr(settings, "PUBLIC_BASE_URL", "") or "").strip()
    if not base:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:7788"
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        base = "%s://%s" % (proto, host)
    endpoint = base.rstrip("/") + "/api/sync/health"'''
assert old in s, "config endpoint block not found"
s = s.replace(old, new, 1)

io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("patched", orig, "->", len(s))
import ast; ast.parse(s); print("AST_OK")
