import io
p="app/sync_api.py"
s=io.open(p,encoding="utf-8").read()
orig=len(s)

old = '''    if not isinstance(body, dict):
        raise HTTPException(400, "请求体必须是 JSON 对象或 CSV 文本")

    # 兼容 Health Auto Export 的外层 data
    payload = body.get("data") if isinstance(body.get("data"), dict) else body
'''

new = '''    if not isinstance(body, dict):
        raise HTTPException(400, "请求体必须是 JSON 对象或 CSV 文本")

    # 兼容快捷指令「JSON 请求体 + 单字段包 CSV」的写法：
    #   {"导出锻炼": "Date,Metric,Value,Unit\\n..."}
    #   {"anything": "..."} 只要值里像 CSV（有换行且含逗号）就转去 CSV 解析
    if "data" not in body and "metrics" not in body and "workouts" not in body:
        for _k, _v in body.items():
            if isinstance(_v, str) and "\\n" in _v and "," in _v:
                try:
                    st = _ingest_csv_text(db, user, _v)
                except Exception:  # noqa: BLE001
                    break
                db.commit()
                _touch_last_sync(db, user, {"csv_metrics": st.get("metrics", 0)})
                db.commit()
                return {
                    "ok": True,
                    "user": user.username,
                    "format": "json-wrapped-csv",
                    "metrics_imported": st.get("metrics", 0),
                    "workouts_imported": st.get("runs", 0),
                    "at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
                }

    # 兼容 Health Auto Export 的外层 data
    payload = body.get("data") if isinstance(body.get("data"), dict) else body
'''

assert old in s, "handler anchor not found"
s = s.replace(old, new, 1)
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("patched", orig, "->", len(s))
import ast; ast.parse(s); print("AST_OK")
