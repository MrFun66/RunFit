import io
p="app/sync_api.py"
s=io.open(p,encoding="utf-8").read()
orig=len(s)

old = '''    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "请求体不是合法 JSON")

    if not isinstance(body, dict):
        raise HTTPException(400, "请求体必须是 JSON 对象")

    # 兼容 Health Auto Export 的外层 data
    payload = body.get("data") if isinstance(body.get("data"), dict) else body
'''

new = '''    # 取原始字节（快捷指令「请求体=文件」会走 multipart，不是 JSON）
    raw = await request.body()
    ctype = (request.headers.get("content-type") or "").lower()

    body = None
    csv_text = None

    if "multipart/form-data" in ctype:
        # 从 multipart 里抠出文件内容
        import re as _re
        boundary = ""
        m = _re.search(r"boundary=([^;]+)", ctype)
        if m:
            boundary = m.group(1).strip().strip('"')
        if boundary:
            sep = ("--" + boundary).encode()
            parts = raw.split(sep)
            for part in parts:
                if b"\\r\\n\\r\\n" in part:
                    head, _, content = part.partition(b"\\r\\n\\r\\n")
                    if b"filename" in head or b"application/octet" in head or b"text/" in head:
                        csv_text = content.rstrip(b"\\r\\n-").decode("utf-8", "ignore")
                        break
        if csv_text is None:
            csv_text = raw.decode("utf-8", "ignore")
    else:
        text = raw.decode("utf-8", "ignore").strip()
        if text.startswith("{") or text.startswith("["):
            try:
                body = json.loads(text)
            except Exception:  # noqa: BLE001
                raise HTTPException(400, "请求体不是合法 JSON")
        elif text:
            csv_text = text

    # ---- 分支 1：CSV（快捷指令「请求体=文件」最常见） ----
    if csv_text is not None:
        try:
            stat = _ingest_csv_text(db, user, csv_text)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"CSV 解析失败：{exc}") from exc
        db.commit()
        n = stat.get("metrics", 0) + stat.get("runs", 0)
        _touch_last_sync(db, user, {"csv_metrics": stat.get("metrics", 0), "csv_runs": stat.get("runs", 0)})
        db.commit()
        return {
            "ok": True,
            "user": user.username,
            "format": "csv",
            "metrics_imported": stat.get("metrics", 0),
            "workouts_imported": stat.get("runs", 0),
            "rows": n,
            "at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
        }

    if not isinstance(body, dict):
        raise HTTPException(400, "请求体必须是 JSON 对象或 CSV 文本")

    # 兼容 Health Auto Export 的外层 data
    payload = body.get("data") if isinstance(body.get("data"), dict) else body
'''

assert old in s, "handler body not matched"
s = s.replace(old, new, 1)
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("patched", orig, "->", len(s))
import ast; ast.parse(s); print("AST_OK")
