import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
print("csv_text refs:", s.count("csv_text"))
print("_ingest_csv_text refs:", s.count("_ingest_csv_text"))
print("_csv_store refs:", s.count("_csv_store"))
print("_csv_pick refs:", s.count("_csv_pick"))
