import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
i=s.find('def _ingest_csv_text')
j=s.find('@router.post("/health")')
print("helper @",i,"handler @",j)
print("=== helper 尾部 ===")
print(s[j-900:j])
