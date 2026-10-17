# -*- coding: utf-8 -*-
"""向 web/index.html 注入「我的」页面 + 底部导航按钮。幂等：已存在则跳过。"""
from pathlib import Path

p = Path(r"D:\GRF\web\index.html")
html = p.read_text(encoding="utf-8")

if 'id="tab-me"' in html:
    print("ALREADY PRESENT, skip")
    raise SystemExit(0)

ME_SECTION = '''
            <!-- 我的（个人资料 / 设置） -->
            <section id="tab-me" class="tab-content hidden space-y-4">
                <div class="bg-gradient-to-br from-slate-700 to-slate-900 rounded-2xl p-5 text-white shadow-lg">
                    <div class="flex items-center gap-3">
                        <div class="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center text-2xl font-bold" id="me-avatar">U</div>
                        <div class="min-w-0">
                            <div class="text-lg font-bold truncate" id="me-username">--</div>
                            <div class="text-xs opacity-70 truncate" id="me-sub">--</div>
                        </div>
                    </div>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                    <h3 class="text-sm font-bold text-slate-600 mb-3">基础资料</h3>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-xs text-slate-500">性别</label>
                            <select id="me-sex" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                                <option value="">未设置</option>
                                <option value="male">男</option>
                                <option value="female">女</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">出生年份</label>
                            <input type="number" id="me-birth" placeholder="1995" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">身高 (cm)</label>
                            <input type="number" step="0.1" id="me-height" placeholder="175" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">训练天数/周</label>
                            <input type="number" id="me-days" placeholder="4" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">目标</label>
                            <select id="me-goal" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                                <option value="">未设置</option>
                                <option value="cut">减脂</option>
                                <option value="recomp">增肌减脂</option>
                                <option value="bulk">增肌</option>
                                <option value="run">提升跑力</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">活动水平</label>
                            <select id="me-activity" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                                <option value="">未设置</option>
                                <option value="sedentary">久坐</option>
                                <option value="light">轻度</option>
                                <option value="moderate">中等</option>
                                <option value="active">活跃</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">目标体重 (kg)</label>
                            <input type="number" step="0.1" id="me-target-weight" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">目标体脂 (%)</label>
                            <input type="number" step="0.1" id="me-target-bf" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                    </div>
                    <div class="mt-3">
                        <label class="text-xs text-slate-500">饮食备注</label>
                        <input id="me-diet" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm" placeholder="如：乳糖不耐受">
                    </div>
                    <div class="mt-3">
                        <label class="text-xs text-slate-500">伤病备注</label>
                        <input id="me-injury" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm" placeholder="如：右膝旧伤">
                    </div>
                    <button id="btn-save-profile" class="w-full mt-4 bg-brand hover:bg-brand-dark text-white font-bold py-3 rounded-xl transition">保存资料</button>
                    <p id="me-profile-msg" class="text-center text-xs mt-2 hidden"></p>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                    <h3 class="text-sm font-bold text-slate-600 mb-3">记录今天</h3>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-xs text-slate-500">体重 (kg)</label>
                            <input type="number" step="0.1" id="me-body-weight" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">体脂 (%)</label>
                            <input type="number" step="0.1" id="me-body-bf" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">静息心率</label>
                            <input type="number" id="me-body-hr" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-slate-500">睡眠 (小时)</label>
                            <input type="number" step="0.1" id="me-body-sleep" class="w-full border border-slate-300 rounded-lg px-3 py-2 mt-1 text-sm">
                        </div>
                    </div>
                    <button id="btn-save-body" class="w-full mt-4 bg-slate-700 hover:bg-slate-800 text-white font-bold py-3 rounded-xl transition">记录</button>
                    <p id="me-body-msg" class="text-center text-xs mt-2 hidden"></p>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                    <h3 class="text-sm font-bold text-slate-600 mb-3">最近记录</h3>
                    <div id="me-body-history" class="space-y-2 text-sm text-slate-500">加载中...</div>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                    <h3 class="text-sm font-bold text-slate-600 mb-3">账号</h3>
                    <div class="flex justify-between items-center text-sm py-1">
                        <span class="text-slate-500">AI 服务</span>
                        <span id="me-llm" class="font-medium">--</span>
                    </div>
                    <div class="flex justify-between items-center text-sm py-1">
                        <span class="text-slate-500">数据归属</span>
                        <span class="font-medium text-slate-700">本机私有数据库</span>
                    </div>
                    <button id="btn-logout-2" class="w-full mt-4 bg-red-50 hover:bg-red-100 text-red-600 font-bold py-3 rounded-xl transition">退出登录</button>
                </div>
            </section>
'''

ME_NAV = '''                <button class="nav-btn flex flex-col items-center justify-center w-full h-full text-slate-400" data-target="me">
                    <svg class="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
                    <span class="text-[10px]">我的</span>
                </button>
'''

# 1) 在 </main> 前插入 section
anchor_main = "        </main>"
assert anchor_main in html, "找不到 </main>"
html = html.replace(anchor_main, ME_SECTION + anchor_main, 1)

# 2) 在教练按钮后、</div>\n        </nav> 前插入导航按钮
anchor_nav = '''                    <span class="text-[10px]">教练</span>
                </button>
            </div>'''
assert anchor_nav in html, "找不到导航锚点"
html = html.replace(
    anchor_nav,
    '''                    <span class="text-[10px]">教练</span>
                </button>
''' + ME_NAV + '''            </div>''',
    1,
)

p.write_text(html, encoding="utf-8")
print("OK, new size =", len(html.encode("utf-8")))
print("tab-me present:", 'id="tab-me"' in html)
print("nav me present:", 'data-target="me"' in html)