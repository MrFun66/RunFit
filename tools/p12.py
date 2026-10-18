import io
a=io.open("app/api.py",encoding="utf-8").read()
for key in ['@router.post("/meals")','@router.get("/meals")','@router.delete("/meals/{mid:int}")','@router.post("/meals/photo")']:
    i=a.find(key)
    print("=== ",key,"idx",i," ===")
    print(a[i:i+2000])
    print()
