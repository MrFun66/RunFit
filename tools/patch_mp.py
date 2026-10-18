import io, re
p = r"D:\GRF\app\sync_api.py"
s = io.open(p, encoding="utf-8").read()
orig = s

old = '''            for part in parts:
                if b"\\r\\n\\r\\n" in part:
                    head, _, content = part.partition(b"\\r\\n\\r\\n")
                    if b"filename" in head or b"application/octet" in head or b"text/" in head:
                        csv_text = content.rstrip(b"\\r\\n-").decode("utf-8", "ignore")
                        break
        if csv_text is None:
            csv_text = raw.decode("utf-8", "ignore")'''

new = '''            best = ""
            for part in parts:
                if b"\\r\\n\\r\\n" not in part:
                    continue
                head, _, content = part.partition(b"\\r\\n\\r\\n")
                txt = content.rstrip(b"\\r\\n-").decode("utf-8", "ignore").strip()
                # 优先带 filename 的文件片段；其次取最长的文本片段（兼容「表单」提交）
                if not txt:
                    continue
                if b"filename" in head and txt:
                    best = txt
                    break
                if len(txt) > len(best):
                    best = txt
            if best:
                csv_text = best
        if csv_text is None:
            csv_text = raw.decode("utf-8", "ignore")'''

if old not in s:
    raise SystemExit("anchor not found")
s = s.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched", orig.__len__(), "->", len(s))
