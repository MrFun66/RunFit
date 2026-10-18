import io
p="app/sync_api.py"
s=io.open(p,encoding="utf-8").read()
orig=len(s)

anchor = '@router.get("/ping")'
assert anchor in s, "ping not found"

debug = '''@router.post("/debug")
async def sync_debug(
    request: Request,
    authorization: str | None = Header(default=None),
):
    """诊断端点：原样回显服务器收到的请求，不做任何解析。"""
    raw = await request.body()
    return {
        "ok": True,
        "method": request.method,
        "content_type": request.headers.get("content-type"),
        "content_length": request.headers.get("content-length"),
        "auth_header": (authorization[:24] + "...") if authorization else None,
        "body_bytes": len(raw),
        "body_head": raw[:300].decode("utf-8", "ignore"),
    }


'''
s = s.replace(anchor, debug + anchor, 1)
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("patched", orig, "->", len(s))
import ast; ast.parse(s); print("AST_OK")
