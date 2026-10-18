import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('<div id="modal-foods"')
j=h.find('<div id="modal-food"')
print("modal-foods @",i,"modal-food @",j)
# 找 modal-foods 块的结束：从 i 开始统计 div 深度
depth=0; k=i; end=None
import re
for m in re.finditer(r'<div\b|</div>', h[i:j+50]):
    if m.group(0).startswith('<div'): depth+=1
    else:
        depth-=1
        if depth==0:
            end=i+m.end(); break
print("block end",end)
print(repr(h[end-120:end+80]))
