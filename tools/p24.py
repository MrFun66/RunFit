import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('<section id="tab-nutrition"')
j=h.find('</section>', i)
print("len",len(h),"start",i,"end",j)
print(h[i:j+10])
