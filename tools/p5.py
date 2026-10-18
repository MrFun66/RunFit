import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
for key in ["def _save_sample","def _upsert_body","_METRIC_MAP ="]:
    i=s.find(key)
    print("=== ",key,i," ===")
    print(s[i:i+1800] if i>=0 else "NOT FOUND")
    print()
