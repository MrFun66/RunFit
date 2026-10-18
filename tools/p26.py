import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('<section id="tab-nutrition"')
j=h.find('</section>', i)+10
print(h[i:j])
