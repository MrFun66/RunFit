import io,re
s=io.open("app/sync_api.py",encoding="utf-8").read()
print("=== _ingest_metrics ===")
i=s.find("def _ingest_metrics")
print(s[i:i+2200])
