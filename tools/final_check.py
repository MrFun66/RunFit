import urllib.request
j=urllib.request.urlopen("http://127.0.0.1:7788/assets/app.js").read().decode("utf-8")
h=urllib.request.urlopen("http://127.0.0.1:7788/").read().decode("utf-8")
checks={
 "今日仅当天过滤": "w.date || '').slice(0, 10) === today",
 "卡片编辑按钮": "editWorkout(' + w.id",
 "下拉刷新": "pull-indicator",
 "健康导入按钮": 'id="btn-import-health2"',
 "Apple导入面板": "export.xml",
}
for k,v in checks.items():
    src = h if ("id=" in v and "btn-import" in v) else j
    print(k, ("OK" if v in src else "MISSING"))
print("设置页导入说明:", "导出所有健康数据" in h)
