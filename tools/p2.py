import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
i=s.find('def _ingest_csv_text')
print(s[i:i+3000])
