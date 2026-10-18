import io
p="app/api.py"
a=io.open(p,encoding="utf-8").read()
orig=len(a)
start=a.find('class FoodPick(BaseModel):')
photo=a.find('@router.post("/meals/photo")')
print("FoodPick @",start,"photo @",photo)
assert start>0 and photo>start
# 删除 FoodPick 到 photo 之前这一整段（旧食物库三件套）
a = a[:start] + a[photo:]
io.open(p,"w",encoding="utf-8",newline="\n").write(a)
print("len",orig,"->",len(a))
