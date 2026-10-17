/**
 * GRF Coach - 前端核心逻辑
 */

const API = {
    async request(path, options = {}) {
        const res = await fetch(`/api${path}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        if (res.status === 401) {
            showAuth();
            throw new Error('未登录');
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `请求失败: ${res.status}`);
        }
        return res.json();
    },
    get(path) { return this.request(path); },
    post(path, body) { return this.request(path, { method: 'POST', body: JSON.stringify(body) }); },
    put(path, body) { return this.request(path, { method: 'PUT', body: JSON.stringify(body) }); },
    delete(path) { return this.request(path, { method: 'DELETE' }); },
};

// --- 状态 ---
let isRegisterMode = false;
let currentTab = 'dashboard';
let templatesData = [];
let currentTemplateToLog = null;
let currentMealResult = null;
let strengthChartInstance = null;

// --- 初始化 ---
document.addEventListener('DOMContentLoaded', async () => {
    setTimeout(() => {
        document.getElementById('splash').style.opacity = '0';
        setTimeout(() => document.getElementById('splash').style.display = 'none', 300);
    }, 500);

    initAuth();
    initNav();
    initFileUploads();
    initChat();
    initModals();
});

// --- 认证 ---
function initAuth() {
    const form = document.getElementById('auth-form');
    const toggle = document.getElementById('auth-toggle');
    
    toggle.addEventListener('click', () => {
        isRegisterMode = !isRegisterMode;
        document.getElementById('auth-btn').textContent = isRegisterMode ? '注册' : '登录';
        toggle.textContent = isRegisterMode ? '已有账号？去登录' : '没有账号？注册一个';
        document.getElementById('auth-error').classList.add('hidden');
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const user = document.getElementById('auth-user').value;
        const pass = document.getElementById('auth-pass').value;
        const btn = document.getElementById('auth-btn');
        const errEl = document.getElementById('auth-error');
        
        btn.disabled = true;
        btn.innerHTML = '<span class="loader"></span>';
        errEl.classList.add('hidden');

        try {
            const endpoint = isRegisterMode ? '/auth/register' : '/auth/login';
            await API.post(endpoint, { username: user, password: pass });
            showApp();
        } catch (err) {
            errEl.textContent = friendlyError(err);
            errEl.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = isRegisterMode ? '注册' : '登录';
        }
    });

    document.getElementById('btn-logout').addEventListener('click', async () => {
        try { await API.post('/auth/logout'); } catch(e) {}
        showAuth();
    });

    checkAuth();
}

async function checkAuth() {
    try {
        const status = await API.get('/auth/status');
        if (status.logged_in) {
            showApp();
        } else {
            showAuth();
        }
    } catch (e) {
        showAuth();
    }
}

function showAuth() {
    document.getElementById('view-auth').classList.remove('hidden');
    document.getElementById('app').classList.add('hidden');
}

function showApp() {
    document.getElementById('view-auth').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    switchTab('dashboard');
}

// --- 导航 ---
function initNav() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-target');
            switchTab(target);
        });
    });
}

function switchTab(tabId) {
    currentTab = tabId;
    // 更新底部导航高亮
    document.querySelectorAll('.nav-btn').forEach(btn => {
        const isTarget = btn.getAttribute('data-target') === tabId;
        btn.classList.toggle('text-brand', isTarget);
        btn.classList.toggle('text-slate-400', !isTarget);
    });
    // 显示对应内容
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.toggle('hidden', el.id !== `tab-${tabId}`);
    });
    // 加载数据
    if (tabId === 'dashboard') { loadDashboard(); loadTrends(); loadReportList(); }
    if (tabId === 'run') loadRuns();
    if (tabId === 'strength') loadStrength();
    if (tabId === 'nutrition') loadNutrition();
    if (tabId === 'settings') loadSettings();
    if (tabId === 'profile') loadMe();
    if (tabId === 'me') loadMe();
}

// --- Dashboard ---
async function loadDashboard() {
    try {
        const data = await API.get('/dashboard');
        const p = data.profile;
        document.getElementById('dash-greeting').textContent = `你好，${p.username}`;
        document.getElementById('dash-goal').textContent = `目标：${translateGoal(p.goal)}`;
        document.getElementById('dash-run-km').innerHTML = `${data.week.run_km} <span class="text-xs font-normal">km</span>`;
        document.getElementById('dash-strength').innerHTML = `${data.week.strength_sessions} <span class="text-xs font-normal">次</span>`;
        document.getElementById('dash-weight').innerHTML = `${data.latest.weight_kg || '--'} <span class="text-sm font-normal text-slate-400">kg</span>`;
        document.getElementById('dash-bodyfat').innerHTML = `${data.latest.bodyfat_pct || '--'} <span class="text-sm font-normal text-slate-400">%</span>`;
    } catch (e) { console.error(e); }
    try { await refreshAiStatus(); } catch (e) {}
}

function translateGoal(g) {
    const map = { 'recomp': '减脂增肌', 'cut': '减脂', 'bulk': '增肌', 'run': '跑步耐力' };
    return map[g] || g || '未设置';
}

// --- 跑步 ---
async function loadRuns() {
    const list = document.getElementById('run-list');
    list.innerHTML = '<div class="text-center py-4"><span class="loader"></span></div>';
    try {
        const data = await API.get('/runs');
        if (!data.items.length) {
            list.innerHTML = '<div class="text-center text-slate-400 text-sm py-8">还没有跑步数据，点击右上角上传 WorkOutDoors 导出的 TCX 文件。</div>';
            return;
        }
        list.innerHTML = data.items.map(r => `
            <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 flex justify-between items-center">
                <div>
                    <div class="font-bold text-slate-700">${r.name || '跑步'}</div>
                    <div class="text-xs text-slate-400 mt-1">${r.start_time.split('T')[0]}</div>
                </div>
                <div class="text-right">
                    <div class="text-brand font-bold text-lg">${(r.distance_m/1000).toFixed(2)} <span class="text-xs">km</span></div>
                    <div class="text-xs text-slate-500 mt-1">${r.pace} /km</div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = `<div class="text-red-500 text-sm">${e.message}</div>`;
    }
}

function initFileUploads() {
    document.getElementById('run-upload').addEventListener('change', async (e) => {
        const files = e.target.files;
        if (!files.length) return;
        const formData = new FormData();
        for (let f of files) formData.append('files', f);
        
        try {
            const res = await fetch('/api/runs/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.errors.length) alert('部分文件失败：\n' + data.errors.join('\n'));
            alert(`成功导入 ${data.imported} 条记录，跳过重复 ${data.skipped_duplicates} 条`);
            loadRuns();
        } catch (err) {
            alert('上传失败：' + err.message);
        }
        e.target.value = '';
    });
}

// --- 力量训练 ---
var _strengthGrain = 'day';

async function loadStrength() {
    await Promise.all([loadTodayWorkouts(), loadStrengthTrend()]);
    loadPlanPreview();
}

// 今日记录（只显示当天）
async function loadTodayWorkouts() {
    var list = document.getElementById('workout-list');
    if (!list) return;
    var today = new Date().toISOString().slice(0, 10);
    try {
        var data = await API.get('/workouts?limit=30');
        var todays = (data.items || []).filter(function (w) {
            return String(w.date || '').slice(0, 10) === today;
        });
        if (!todays.length) {
            list.innerHTML = '<div class="bg-white p-6 rounded-xl border border-dashed border-slate-200 text-center text-slate-400 text-sm">今天还没有记录。点右上角「记录今日训练」开始。</div>';
            return;
        }
        list.innerHTML = todays.map(function (w) {
            var sets = w.sets || [];
            var vol = 0;
            sets.forEach(function (st) { vol += (st.weight_kg || 0) * (st.reps || 0); });
            var names = {};
            sets.forEach(function (st) { if (st.exercise_name) names[st.exercise_name] = 1; });
            var exList = Object.keys(names).slice(0, 4).join('、');
            return '<div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100">' +
                '<div class="flex justify-between items-start">' +
                    '<div class="min-w-0">' +
                        '<div class="font-bold text-slate-700 truncate">' + (w.name || '自由训练') + '</div>' +
                        '<div class="text-xs text-slate-400 mt-0.5">' + sets.length + ' 组 · 容量 ' + Math.round(vol) + ' kg' + (exList ? ' · ' + exList : '') + '</div>' +
                    '</div>' +
                    '<button class="text-xs text-brand font-medium shrink-0 ml-2" onclick="editWorkout(' + w.id + ')">编辑</button>' +
                '</div>' +
            '</div>';
        }).join('');
    } catch (e) {
        list.innerHTML = '<div class="text-xs text-rose-500">加载失败：' + e.message + '</div>';
    }
}

// 容量柱状图（日/周/月/年）
async function loadStrengthTrend() {
    var canvas = document.getElementById('strength-chart');
    if (!canvas) return;
    try {
        var d = await API.get('/strength/trend?grain=' + _strengthGrain);
        var totalEl = document.getElementById('trend-total');
        if (totalEl) {
            var head = { day: '\u4eca\u5929', week: '\u672c\u5468', month: '\u672c\u6708', year: '\u672c\u5e74' }[_strengthGrain] || '';
            totalEl.textContent = d.total_volume > 0
                ? head + ' \u603b\u5bb9\u91cf ' + Number(d.total_volume).toLocaleString() + ' kg'
                : head + '\u8fd8\u6ca1\u6709\u8bad\u7ec3\u8bb0\u5f55';
        }
        renderStrengthChart(d);
    } catch (e) { console.error('trend', e); }
}

function renderStrengthChart(d) {
    var canvas = document.getElementById('strength-chart');
    if (!canvas) return;
    if (strengthChartInstance) { strengthChartInstance.destroy(); strengthChartInstance = null; }
    var buckets = d.buckets || [];
    var series = d.series || [];
    var labels = buckets.map(function (b) { return b.label; });

    var legend = document.getElementById('trend-legend');
    if (legend) {
        if (d.mode === 'by_part') {
            legend.innerHTML = buckets.map(function (b, n) {
                var c = (series[0] && series[0].colors && series[0].colors[n]) || '#94a3b8';
                return '<span class="inline-flex items-center gap-1 mr-2.5 mb-1"><i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:' + c + '"></i>' + b.label + '</span>';
            }).join('');
        } else {
            legend.innerHTML = series.map(function (s) {
                return '<span class="inline-flex items-center gap-1 mr-2.5 mb-1"><i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:' + s.color + '"></i>' + s.label + '</span>';
            }).join('');
        }
    }
    if (!series.length || !buckets.length) {
        var cv = document.getElementById('strength-chart');
        if (cv) {
            var ctx2 = cv.getContext('2d');
            ctx2.clearRect(0, 0, cv.width, cv.height);
            ctx2.fillStyle = '#94a3b8';
            ctx2.font = '13px sans-serif';
            ctx2.textAlign = 'center';
            ctx2.fillText('还没有训练记录，先去记一笔吧', cv.width / 2, cv.height / 2);
        }
        return;
    }

    var datasets;
    if (d.mode === 'by_part') {
        datasets = [{
            label: '\u5bb9\u91cf',
            data: series[0].data,
            backgroundColor: series[0].colors,
            borderRadius: 4,
            maxBarThickness: 34
        }];
    } else {
        datasets = series.map(function (s) {
            return {
                label: s.label, data: s.data, backgroundColor: s.color,
                borderRadius: 3, stack: 'vol', maxBarThickness: 26
            };
        });
    }

    strengthChartInstance = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (c) {
                            var nm = d.mode === 'by_part' ? c.label : c.dataset.label;
                            return nm + ': ' + Number(c.parsed.y || 0).toLocaleString() + ' kg';
                        }
                    }
                }
            },
            scales: {
                x: { stacked: d.mode !== 'by_part', grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 0, autoSkip: true } },
                y: { stacked: d.mode !== 'by_part', beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { size: 10 } } }
            }
        }
    });
}

async function editWorkout(wid) {
    try {
        var d = await API.get('/workouts?limit=50');
        var w = (d.items || []).find(function (x) { return x.id === wid; });
        if (!w) { alert('记录不存在'); return; }
        var lines = (w.sets || []).map(function (st, i) {
            var nm = st.exercise_name || ('动作' + (st.exercise_id || ''));
            return (i + 1) + '. ' + nm + '  ' + (st.reps || 0) + ' 次  ' + (st.weight_kg || 0) + ' kg';
        }).join('\n');
        var tip = '当前记录：\n' + lines + '\n\n确认要重新编辑吗？（将覆盖这条记录）';
        if (!confirm(tip)) return;
        // 打开记录弹窗并回填
        if (typeof openTemplateSelector === 'function') {
            window._editingWorkoutId = wid;
            await openTemplateSelector();
        }
    } catch (e) {
        alert('加载失败：' + e.message);
    }
}

// 模板选择
async function openTemplateSelector() {
    const modal = document.getElementById('modal-template');
    const list = document.getElementById('template-list');
    list.innerHTML = '<div class="text-center py-4"><span class="loader"></span></div>';
    modal.classList.remove('hidden');
    
    try {
        const data = await API.get('/templates');
        templatesData = data.items;
        list.innerHTML = data.items.map(t => `
            <div class="bg-slate-50 border border-slate-200 p-4 rounded-xl cursor-pointer hover:border-brand transition" onclick="selectTemplate(${t.id})">
                <div class="font-bold text-slate-700">${t.name}</div>
                <div class="text-xs text-slate-500 mt-1">${t.note || ''}</div>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = `<div class="text-red-500">${e.message}</div>`;
    }
}

function selectTemplate(id) {
    const t = templatesData.find(x => x.id === id);
    if (!t) return;
    currentTemplateToLog = t;
    
    document.getElementById('modal-template').classList.add('hidden');
    document.getElementById('log-title').textContent = t.name;
    document.getElementById('modal-log').classList.remove('hidden');
    
    const itemsHtml = t.items.map(it => `
        <div class="flex items-center gap-3 bg-slate-50 p-3 rounded-xl">
            <div class="flex-1">
                <div class="font-bold text-sm text-slate-700">${it.exercise_name}</div>
                <div class="text-xs text-slate-400">${it.sets}组 x ${it.reps} | 上次: ${it.last_weight_kg ? it.last_weight_kg+'kg' : '无'}</div>
            </div>
            <div class="w-20">
                <input type="number" step="0.5" placeholder="重量" value="${it.target_weight_kg ?? it.last_weight_kg ?? ''}" class="w-full text-center border border-slate-300 rounded p-1 text-sm bg-white" id="weight-${it.exercise_id}">
            </div>
            <div class="w-16">
                <input type="number" step="0.5" placeholder="RPE" value="${it.last_rpe || ''}" class="w-full text-center border border-slate-300 rounded p-1 text-sm bg-white" id="rpe-${it.exercise_id}">
            </div>
        </div>
    `).join('');
    document.getElementById('log-items').innerHTML = itemsHtml;
}

function initModals() {
    // 保存训练记录
    document.getElementById('btn-save-log').addEventListener('click', async () => {
        // 编辑模式：保存修改（整体替换）
        if (typeof _editingWorkout !== 'undefined' && _editingWorkout) {
            await saveWorkoutEdit();
            return;
        }
        if (!currentTemplateToLog) return;
        const btn = document.getElementById('btn-save-log');
        const weights = {};
        const rpes = {};
        
        currentTemplateToLog.items.forEach(it => {
            const w = document.getElementById(`weight-${it.exercise_id}`).value;
            const r = document.getElementById(`rpe-${it.exercise_id}`).value;
            if (w) weights[it.exercise_id] = parseFloat(w);
            if (r) rpes[it.exercise_id] = parseFloat(r);
        });
        
        btn.disabled = true;
        btn.innerHTML = '<span class="loader"></span>';
        try {
            await API.post(`/templates/${currentTemplateToLog.id}/log`, {
                date: new Date().toISOString().split('T')[0],
                weights,
                rpes
            });
            document.getElementById('modal-log').classList.add('hidden');
            loadStrength();
            alert('记录已保存！');
        } catch (e) {
            alert('保存失败：' + e.message);
        } finally {
            btn.disabled = false;
            btn.textContent = '保存并生成记录';
        }
    });
}

// --- 营养 ---
async function loadNutrition() {
    // 目标
    try {
        const plan = await API.get('/nutrition/plan');
        if (plan.complete) {
            const t = plan.plan.training;
            document.getElementById('mac-kcal').textContent = t.kcal;
            document.getElementById('mac-p').textContent = t.protein_g + 'g';
            document.getElementById('mac-c').textContent = t.carb_g + 'g';
            document.getElementById('mac-f').textContent = t.fat_g + 'g';
        }
    } catch (e) { console.error(e); }

    // 餐食列表
    const list = document.getElementById('meal-list');
    try {
        const data = await API.get('/meals');
        if (!data.items.length) {
            list.innerHTML = '<div class="text-center text-slate-400 text-sm py-4">今天还没有记录饮食。</div>';
        } else {
            var SLOTS = [
                ['breakfast', '早餐'],
                ['lunch', '午餐'],
                ['dinner', '晚餐'],
                ['snack', '加餐']
            ];
            var groups = {};
            data.items.forEach(function (m) {
                var k = m.slot || 'snack';
                if (!groups[k]) groups[k] = [];
                groups[k].push(m);
            });
            var html = '';
            SLOTS.forEach(function (pair) {
                var key = pair[0], label = pair[1];
                var rows = groups[key] || [];
                var kcal = 0;
                rows.forEach(function (b) { kcal += (b.kcal || 0); });
                html += '<div class="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">';
                html += '<div class="px-4 py-2 bg-slate-50 flex justify-between items-center border-b border-slate-100">';
                html += '<span class="text-sm font-bold text-slate-700">' + label + '</span>';
                html += '<span class="text-xs text-slate-400">' + (rows.length ? Math.round(kcal) + ' kcal' : '未记录') + '</span>';
                html += '</div>';
                if (rows.length) {
                    rows.forEach(function (m) {
                        html += '<div class="px-4 py-2 flex justify-between items-start border-b border-slate-50 last:border-0">';
                        html += '<div class="min-w-0 pr-2">';
                        html += '<div class="text-sm text-slate-700 truncate">' + (m.description || '一餐') + '</div>';
                        html += '<div class="text-xs text-slate-400 mt-0.5">P ' + (m.protein_g || 0) + ' / C ' + (m.carb_g || 0) + ' / F ' + (m.fat_g || 0) + '</div>';
                        html += '</div>';
                        html += '<div class="text-brand font-bold text-sm shrink-0">' + Math.round(m.kcal || 0) + '</div>';
                        html += '</div>';
                    });
                } else {
                    html += '<div class="px-4 py-3 text-xs text-slate-300">还没记录</div>';
                }
                html += '</div>';
            });
            list.innerHTML = html;
        }
    } catch (e) {
        list.innerHTML = '';
    }
}

// 拍照 / 选图 识餐
var _mealImageUrl = null;

document.getElementById('meal-upload')?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const modal = document.getElementById('modal-meal');
    const container = document.getElementById('meal-result-items');
    modal.classList.remove('hidden');
    container.innerHTML = '<div class="text-center py-8 text-slate-500"><span class="loader"></span> 正在识别食物，请稍候（通常 5-15 秒）...</div>';

    // 本地预览图片
    try {
        if (_mealImageUrl) URL.revokeObjectURL(_mealImageUrl);
        _mealImageUrl = URL.createObjectURL(file);
    } catch (_) {}

    if (file.size > 12 * 1024 * 1024) {
        container.innerHTML = '<div class="text-red-500 text-center py-8">图片太大（' + (file.size / 1048576).toFixed(1) + 'MB），请换一张 12MB 以内的照片</div>';
        e.target.value = '';
        return;
    }

    var small = await compressImage(file);
    const formData = new FormData();
    formData.append('file', small, 'meal.jpg');

    try {
        const res = await fetch('/api/meals/photo', { method: 'POST', body: formData, credentials: 'same-origin' });
        let data = null;
        try { data = await res.json(); } catch (_) {}
        if (!res.ok) {
            const d = (data && (data.detail || data.message)) || ('服务器返回 ' + res.status);
            throw new Error(typeof d === 'string' ? d : JSON.stringify(d));
        }
        if (!data || !Array.isArray(data.items) || !data.items.length) {
            container.innerHTML = '<div class="text-amber-600 text-center py-8">没能识别出食物，请换一张更清晰、更接近食物的照片重试</div>';
            e.target.value = '';
            return;
        }

        currentMealResult = data;
        const confMap = { high: '高', medium: '中', low: '低' };
        let html = '';
        if (_mealImageUrl) {
            html += '<img src="' + _mealImageUrl + '" class="w-full max-h-40 object-cover rounded-xl mb-3 border border-slate-200">';
        }
        html += '<div class="text-xs text-slate-500 mb-2">识别置信度：' + (confMap[data.confidence] || '中') + '</div>';
        html += data.items.map(function (it) {
            return '<div class="bg-slate-50 p-3 rounded-xl mb-2">' +
                '<div class="flex justify-between items-center mb-1">' +
                '<span class="font-bold text-slate-700 text-sm">' + (it.name || '食物') + '</span>' +
                '<span class="text-xs text-slate-500">' + (it.grams || 0) + 'g</span></div>' +
                '<div class="flex gap-3 text-xs text-slate-500">' +
                '<span class="text-brand font-bold">' + (it.kcal || 0) + ' kcal</span>' +
                '<span>P ' + (it.protein_g || 0) + '</span>' +
                '<span>C ' + (it.carb_g || 0) + '</span>' +
                '<span>F ' + (it.fat_g || 0) + '</span>' +
                '</div></div>';
        }).join('');
        const t = data.total || {};
        html += '<div class="mt-4 pt-3 border-t border-slate-200 flex justify-between font-bold text-slate-800">' +
            '<span>合计</span><span>' + (t.kcal || 0) + ' kcal</span></div>';
        if (data.note) html += '<div class="text-xs text-slate-400 mt-2">' + data.note + '</div>';
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = '<div class="text-red-500 text-center py-8 px-4">识别失败：' + friendlyError(err) + '</div>';
    }
    e.target.value = '';
});

document.getElementById('btn-save-meal')?.addEventListener('click', async () => {
    if (!currentMealResult) return;
    const btn = document.getElementById('btn-save-meal');
    btn.disabled = true;
    btn.innerHTML = '<span class="loader"></span>';
    
    try {
        const items = currentMealResult.items;
        const desc = items.map(i => i.name).join('、');
        var slot = _currentMealSlot();
        await API.post('/meals', {
            date: new Date().toISOString().split('T')[0],
            slot: slot,
            description: desc,
            kcal: currentMealResult.total.kcal,
            protein_g: currentMealResult.total.protein_g,
            carb_g: currentMealResult.total.carb_g,
            fat_g: currentMealResult.total.fat_g
        });
        document.getElementById('modal-meal').classList.add('hidden');
        loadNutrition();
    } catch (e) {
        alert('保存失败：' + friendlyError(e));
    } finally {
        btn.disabled = false;
        btn.textContent = '确认并记录';
    }
});

// --- AI 教练 ---
function initChat() {
    const input = document.getElementById('chat-input');
    const send = document.getElementById('chat-send');
    if (!input || !send) { if (typeof initReports === 'function') initReports(); return; }
    
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;
        
        input.value = '';
        appendChatMsg('user', text);
        const aiMsgEl = appendChatMsg('assistant', '<span class="loader"></span>');
        
        try {
            const res = await fetch('/api/coach/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, module: 'general' })
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail);
            }
            
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let fullText = '';
            aiMsgEl.innerHTML = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                fullText += decoder.decode(value, { stream: true });
                // 简单 markdown 渲染
                aiMsgEl.innerHTML = formatMarkdown(fullText);
                scrollToBottom();
            }
        } catch (e) {
            aiMsgEl.innerHTML = `<span class="text-red-500">出错：${e.message}</span>`;
        }
    }
    
    send.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    
}

/**
 * 流式请求 /api/coach/stream 并把内容渲染到指定元素。
 * sendMessage 与快捷按钮共用。
 */
async function streamCoachReply(text, aiMsgEl, module = 'general') {
    const res = await fetch('/api/coach/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, module }),
    });
    if (!res.ok) {
        let detail = '请求失败';
        try { detail = (await res.json()).detail; } catch (e) {}
        throw new Error(detail);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    aiMsgEl.innerHTML = '';
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        fullText += decoder.decode(value, { stream: true });
        aiMsgEl.innerHTML = formatMarkdown(fullText);
        scrollToBottom();
    }
    return fullText;
}

async function loadChatHistory() {
    const box = document.getElementById('chat-box');
    if (!box) return;
    try {
        const data = await API.get('/coach/history');
        if (data.items.length) {
            box.innerHTML = '<div class="text-center text-xs text-slate-400 my-4">最近对话</div>';
            data.items.forEach(m => appendChatMsg(m.role, formatMarkdown(m.content), false));
            scrollToBottom();
        }
    } catch (e) {}
}

function appendChatMsg(role, html, scroll = true) {
    const box = document.getElementById('chat-box');
    if (!box) return null;
    const div = document.createElement('div');
    div.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} w-full`;
    div.innerHTML = `<div class="${role === 'user' ? 'bg-brand text-white' : 'bg-white border border-slate-100 shadow-sm'} rounded-2xl ${role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'} px-4 py-2 max-w-[85%] text-sm chat-content">${html}</div>`;
    box.appendChild(div);
    if (scroll) scrollToBottom();
    return div.querySelector('.chat-content');
}

function scrollToBottom() {
    const box = document.getElementById('chat-box');
    if (!box) return;
    box.scrollTop = box.scrollHeight;
}

function formatMarkdown(text) {
    if (!text) return '';
    let html = text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    return `<p>${html}</p>`;
}
// ============================================================
// 计划管理（可自由增删动作）
// ============================================================
let allExercises = [];
let editingPlan = null;      // { id: number|null, name, focus, note, items: [...] }
let pickerTargetIndex = -1;  // 当前正在替换的动作索引，-1 表示追加

const FOCUS_LABEL = {
    push: '推', pull: '拉', legs: '腿',
    upper: '上肢', lower: '下肢', full: '全身'
};

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

async function ensureExercises() {
    if (allExercises.length) return allExercises;
    const data = await API.get('/exercises');
    allExercises = data.items || [];
    return allExercises;
}

// ---------- 计划列表 ----------
async function openPlanManager() {
    document.getElementById('modal-plan-list').classList.remove('hidden');
    const box = document.getElementById('plan-list');
    box.innerHTML = '<div class="text-center py-4"><span class="loader"></span></div>';
    try {
        const data = await API.get('/templates');
        templatesData = data.items || [];
        if (!templatesData.length) {
            box.innerHTML = '<div class="text-center text-slate-400 text-sm py-6">还没有计划，点右上角「+ 新建」开始。</div>';
            return;
        }
        box.innerHTML = templatesData.map(t => `
            <div class="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <div class="flex justify-between items-start">
                    <div class="flex-1 min-w-0">
                        <div class="font-bold text-slate-700 truncate">
                            ${t.name}
                            ${t.is_builtin ? '<span class="ml-1 text-[10px] bg-slate-200 text-slate-500 px-1.5 py-0.5 rounded">内置</span>' : ''}
                        </div>
                        <div class="text-xs text-slate-400 mt-1">
                            ${FOCUS_LABEL[t.focus] || t.focus || ''} · ${t.items.length} 个动作 · 容量 ${planVolume(t.items).toLocaleString()} kg
                        </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0 ml-2">
                        <button onclick="editPlan(${t.id})" class="text-brand text-xs font-medium">编辑</button>
                        <button onclick="duplicatePlan(${t.id})" class="text-slate-500 text-xs">复制</button>
                        ${t.is_builtin ? '' : `<button onclick="removePlan(${t.id})" class="text-rose-500 text-xs">删除</button>`}
                    </div>
                </div>
                <div class="mt-2 text-xs text-slate-500 leading-relaxed">
                    ${t.items.map(it => `${it.exercise_name} ${it.sets || 3}×${it.reps || '—'}`).join('　·　')}
                </div>
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = `<div class="text-rose-500 text-sm">${e.message}</div>`;
    }
}

function newPlan() {
    editingPlan = { id: null, name: '', focus: 'push', note: '', items: [] };
    renderPlanEditor();
}

async function editPlan(id) {
    const t = templatesData.find(x => x.id === id);
    if (!t) return;
    editingPlan = {
        id: t.id,
        name: t.name,
        focus: t.focus || 'push',
        note: t.note || '',
        items: t.items.map(it => ({
            exercise_id: it.exercise_id,
            exercise_name: it.exercise_name,
            sets: it.sets || 3,
            reps: it.reps || '8-12',
            target_weight_kg: it.target_weight_kg ?? it.last_weight_kg ?? null,
            rest_s: null,
            note: it.note || ''
        }))
    };
    renderPlanEditor();
}

function duplicatePlan(id) {
    const t = templatesData.find(x => x.id === id);
    if (!t) return;
    editingPlan = {
        id: null,
        name: t.name + ' 副本',
        focus: t.focus || 'push',
        note: t.note || '',
        items: t.items.map(it => ({
            exercise_id: it.exercise_id,
            exercise_name: it.exercise_name,
            sets: it.sets || 3,
            reps: it.reps || '8-12',
            target_weight_kg: it.target_weight_kg ?? it.last_weight_kg ?? null,
            rest_s: null,
            note: it.note || ''
        }))
    };
    renderPlanEditor();
}

async function removePlan(id) {
    if (!confirm('确定删除这个计划？')) return;
    try {
        await API.delete(`/templates/${id}`);
        await openPlanManager();
        loadPlanPreview();
    } catch (e) { alert('删除失败：' + e.message); }
}


// 单个动作的预估容量 = 组数 × 次数(取中值) × 重量
function repsMid(reps) {
    if (!reps) return 0;
    const nums = String(reps).match(/\d+/g);
    if (!nums) return 0;
    const arr = nums.map(Number);
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}
function volumeOf(item) {
    const sets = item.sets || 0;
    const reps = repsMid(item.reps);
    const w = item.target_weight_kg || 0;
    return Math.round(sets * reps * w);
}
function planVolume(items) {
    return (items || []).reduce((sum, it) => sum + volumeOf(it), 0);
}

// ---------- 计划编辑器 ----------
function renderPlanEditor() {
    if (!editingPlan) return;
    closeModal('modal-plan-list');
    document.getElementById('modal-plan-edit').classList.remove('hidden');
    document.getElementById('plan-edit-title').textContent = editingPlan.id ? '编辑计划' : '新建计划';
    document.getElementById('plan-name').value = editingPlan.name || '';
    document.getElementById('plan-focus').value = editingPlan.focus || 'push';
    document.getElementById('plan-note').value = editingPlan.note || '';
    renderPlanItems();
}

function renderPlanItems() {
    const box = document.getElementById('plan-items');
    if (!editingPlan.items.length) {
        box.innerHTML = '<div class="text-center text-slate-400 text-xs py-6 border border-dashed border-slate-300 rounded-xl">还没有动作，点「+ 添加动作」</div>';
        return;
    }
    box.innerHTML = editingPlan.items.map((it, i) => `
        <div class="bg-slate-50 border border-slate-200 rounded-xl p-3">
            <div class="flex justify-between items-start mb-2">
                <div class="font-medium text-sm text-slate-700 flex-1 min-w-0 truncate">${i + 1}. ${it.exercise_name}</div>
                <div class="flex gap-2 shrink-0 ml-2 text-xs">
                    <button onclick="movePlanItem(${i}, -1)" class="text-slate-400" ${i === 0 ? 'disabled' : ''}>↑</button>
                    <button onclick="movePlanItem(${i}, 1)" class="text-slate-400" ${i === editingPlan.items.length - 1 ? 'disabled' : ''}>↓</button>
                    <button onclick="replacePlanItem(${i})" class="text-brand">换</button>
                    <button onclick="removePlanItem(${i})" class="text-rose-500">删</button>
                </div>
            </div>
            <div class="grid grid-cols-3 gap-2">
                <div>
                    <label class="text-[10px] text-slate-400">组数</label>
                    <input type="number" min="1" max="20" value="${it.sets}" onchange="updatePlanItem(${i}, 'sets', this.value)" class="w-full border border-slate-300 rounded px-2 py-1 text-xs">
                </div>
                <div>
                    <label class="text-[10px] text-slate-400">次数</label>
                    <input value="${it.reps || ''}" placeholder="8-12" onchange="updatePlanItem(${i}, 'reps', this.value)" class="w-full border border-slate-300 rounded px-2 py-1 text-xs">
                </div>
                <div>
                    <label class="text-[10px] text-slate-400">重量(kg)</label>
                    <input type="number" step="0.5" value="${it.target_weight_kg ?? ''}" placeholder="60" onchange="updatePlanItem(${i}, 'target_weight_kg', this.value)" class="w-full border border-slate-300 rounded px-2 py-1 text-xs">
                </div>
            </div>
            <div class="text-[10px] text-slate-400 mt-1 text-right">
                容量 ≈ ${volumeOf(it)} kg
            </div>
        </div>
    `).join('');
}

function updatePlanItem(i, key, val) {
    if (!editingPlan) return;
    const it = editingPlan.items[i];
    if (!it) return;
    if (key === 'sets') {
        it[key] = val === '' ? null : parseInt(val, 10);
    } else if (key === 'target_weight_kg') {
        it[key] = val === '' ? null : parseFloat(val);
        renderPlanItems();   // 重算容量
    } else {
        it[key] = val;
    }
}

function movePlanItem(i, delta) {
    const j = i + delta;
    if (j < 0 || j >= editingPlan.items.length) return;
    const tmp = editingPlan.items[i];
    editingPlan.items[i] = editingPlan.items[j];
    editingPlan.items[j] = tmp;
    renderPlanItems();
}

function removePlanItem(i) {
    editingPlan.items.splice(i, 1);
    renderPlanItems();
}

function replacePlanItem(i) {
    pickerTargetIndex = i;
    openExercisePicker();
}

function openExercisePicker() {
    if (pickerTargetIndex === -1) {
        // 追加模式
    }
    document.getElementById('modal-ex-picker').classList.remove('hidden');
    document.getElementById('ex-search').value = '';
    renderExerciseList('');
    document.getElementById('ex-search').focus();
}

async function renderExerciseList(kw) {
    const box = document.getElementById('ex-list');
    box.innerHTML = '<div class="text-center py-3"><span class="loader"></span></div>';
    try {
        await ensureExercises();
        const q = (kw || '').trim().toLowerCase();
        const list = allExercises.filter(e =>
            !q || e.name.toLowerCase().includes(q) ||
            (e.name_en && e.name_en.toLowerCase().includes(q)) ||
            (e.category && e.category.toLowerCase().includes(q))
        );
        if (!list.length) {
            box.innerHTML = '<div class="text-center text-slate-400 text-sm py-4">没有匹配的动作</div>';
            return;
        }
        // 按分类分组
        const groups = {};
        list.forEach(e => {
            const k = e.category || '其他';
            (groups[k] = groups[k] || []).push(e);
        });
        box.innerHTML = Object.entries(groups).map(([cat, arr]) => `
            <div class="mb-2">
                <div class="text-[11px] text-slate-400 px-1 mb-1">${cat}</div>
                ${arr.map(e => `
                    <button onclick="pickExercise(${e.id})" class="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-100 text-sm text-slate-700 flex justify-between items-center">
                        <span>${e.name}</span>
                        <span class="text-[11px] text-slate-400">${e.equipment || ''}</span>
                    </button>
                `).join('')}
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = `<div class="text-rose-500 text-sm">${e.message}</div>`;
    }
}

async function pickExercise(exId) {
    await ensureExercises();
    const ex = allExercises.find(e => e.id === exId);
    if (!ex || !editingPlan) return;
    const item = {
        exercise_id: ex.id,
        exercise_name: ex.name,
        sets: 3,
        reps: '8-12',
        rest_s: 90,
        note: ''
    };
    if (pickerTargetIndex >= 0) {
        editingPlan.items[pickerTargetIndex] = item;
    } else {
        editingPlan.items.push(item);
    }
    pickerTargetIndex = -1;
    closeModal('modal-ex-picker');
    renderPlanItems();
}

// ---------- 保存 ----------
async function savePlan() {
    if (!editingPlan) return;
    const name = document.getElementById('plan-name').value.trim();
    if (!name) { alert('请填写计划名称'); return; }
    if (!editingPlan.items.length) { alert('至少添加一个动作'); return; }

    const payload = {
        name,
        focus: document.getElementById('plan-focus').value,
        note: document.getElementById('plan-note').value.trim() || null,
        items: editingPlan.items.map(it => ({
            exercise_id: it.exercise_id,
            sets: it.sets,
            reps: it.reps,
            rest_s: null,
            target_weight_kg: it.target_weight_kg,
            note: it.note || null
        }))
    };

    const btn = document.getElementById('btn-save-plan');
    btn.disabled = true;
    btn.textContent = '保存中...';
    try {
        if (editingPlan.id) {
            await API.put(`/templates/${editingPlan.id}`, payload);
        } else {
            await API.post('/templates', payload);
        }
        closeModal('modal-plan-edit');
        editingPlan = null;
        loadPlanPreview();
        loadStrength();
    } catch (e) {
        alert('保存失败：' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '保存计划';
    }
}

// ---------- 力量页的计划预览 ----------
async function loadPlanPreview() {
    const box = document.getElementById('plan-preview');
    if (!box) return;
    try {
        const data = await API.get('/templates');
        const list = data.items || [];
        if (!list.length) {
            box.innerHTML = '<div class="text-slate-400">还没有计划，点上方「管理计划」新建。</div>';
            return;
        }
        box.innerHTML = list.map(t => `
            <div class="flex justify-between items-center py-1.5 border-b border-slate-50 last:border-0">
                <span class="text-slate-700 font-medium">${t.name}</span>
                <span class="text-slate-400 text-xs">${t.items.length} 个动作 · ${FOCUS_LABEL[t.focus] || t.focus || ''}</span>
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = `<div class="text-rose-500 text-xs">${e.message}</div>`;
    }
}

// ---------- 事件绑定 ----------
document.addEventListener('DOMContentLoaded', () => {
    const btnSave = document.getElementById('btn-save-plan');
    if (btnSave) btnSave.addEventListener('click', savePlan);

    const search = document.getElementById('ex-search');
    if (search) {
        let timer = null;
        search.addEventListener('input', (e) => {
            clearTimeout(timer);
            timer = setTimeout(() => renderExerciseList(e.target.value), 150);
        });
    }
});
// ==========================================================
// 我的（个人资料 / 设置）
// ==========================================================
function _meMsg(elId, text, ok) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = text;
    el.classList.remove('hidden', 'text-emerald-600', 'text-rose-600');
    el.classList.add(ok ? 'text-emerald-600' : 'text-rose-600');
    setTimeout(function () { el.classList.add('hidden'); }, 2600);
}

function _num(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    const v = el.value;
    if (v === '' || v === null || v === undefined) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}

function _str(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    return el.value === '' ? null : el.value;
}

async function loadMe() {
    try {
        const p = await API.get('/profile');
        document.getElementById('me-username').textContent = p.username || '--';
        const bits = [];
        if (p.sex) bits.push(p.sex === 'male' ? '男' : '女');
        if (p.age) bits.push(p.age + ' 岁');
        if (p.height_cm) bits.push(p.height_cm + ' cm');
        document.getElementById('me-sub').textContent = bits.length ? bits.join(' · ') : '资料未完善';
        document.getElementById('me-avatar').textContent = (p.username || 'U').charAt(0).toUpperCase();
        document.getElementById('me-sex').value = p.sex || '';
        document.getElementById('me-birth').value = p.birth_year || '';
        document.getElementById('me-height').value = p.height_cm || '';
        document.getElementById('me-days').value = p.training_days_per_week || '';
        document.getElementById('me-goal').value = p.goal || '';
        document.getElementById('me-activity').value = p.activity_level || '';
        document.getElementById('me-target-weight').value = p.target_weight_kg || '';
        document.getElementById('me-target-bf').value = p.target_bodyfat_pct || '';
        document.getElementById('me-diet').value = p.diet_notes || '';
        document.getElementById('me-injury').value = p.injury_notes || '';
        // me-llm 已移至设置页
        await loadBodyHistory();
        await loadTrends();
        await loadAiConfig();
        await loadPasskeys();
    } catch (e) {
        console.error('loadMe', e);
    }
}

async function loadBodyHistory() {
    const box = document.getElementById('me-body-history');
    if (!box) return;
    try {
        const d = await API.get('/body?days=60');
        const items = (d.items || []).slice(-8).reverse();
        if (!items.length) {
            box.innerHTML = '<div class="text-slate-400 text-xs">还没有记录，先在上面记一次体重吧</div>';
            return;
        }
        box.innerHTML = items.map(function (it) {
            const parts = [];
            if (it.weight_kg) parts.push(it.weight_kg + ' kg');
            if (it.bodyfat_pct) parts.push(it.bodyfat_pct + '%');
            if (it.resting_hr) parts.push('静息 ' + it.resting_hr);
            if (it.sleep_hours) parts.push('睡眠 ' + it.sleep_hours + 'h');
            return '<div class="flex justify-between border-b border-slate-50 pb-1">' +
                '<span class="text-slate-400 text-xs">' + it.date + '</span>' +
                '<span class="text-slate-700 text-xs">' + (parts.join(' · ') || '—') + '</span></div>';
        }).join('');
        const t = d.trend;
        if (t && t.direction) {
            box.innerHTML += '<div class="text-xs text-slate-400 pt-2">体重趋势：' + t.direction +
                (t.kg_per_week ? ' ' + t.kg_per_week + ' kg/周' : '') + '</div>';
        }
    } catch (e) {
        box.innerHTML = '<div class="text-rose-500 text-xs">' + e.message + '</div>';
    }
}

async function saveProfile() {
    const body = {
        sex: _str('me-sex'),
        birth_year: _num('me-birth'),
        height_cm: _num('me-height'),
        training_days_per_week: _num('me-days'),
        goal: _str('me-goal'),
        activity_level: _str('me-activity'),
        target_weight_kg: _num('me-target-weight'),
        target_bodyfat_pct: _num('me-target-bf'),
        diet_notes: _str('me-diet'),
        injury_notes: _str('me-injury')
    };
    Object.keys(body).forEach(function (k) { if (body[k] === null) delete body[k]; });
    try {
        await API.put('/profile', body);
        _meMsg('me-profile-msg', '已保存', true);
        await loadMe();
    } catch (e) {
        _meMsg('me-profile-msg', e.message, false);
    }
}

async function saveBody() {
    const today = new Date().toISOString().slice(0, 10);
    const body = { date: today };
    const w = _num('me-body-weight');
    const bf = _num('me-body-bf');
    const hr = _num('me-body-hr');
    const sl = _num('me-body-sleep');
    if (w !== null) body.weight_kg = w;
    if (bf !== null) body.bodyfat_pct = bf;
    if (hr !== null) body.resting_hr = hr;
    if (sl !== null) body.sleep_hours = sl;
    if (Object.keys(body).length === 1) {
        _meMsg('me-body-msg', '至少填一项', false);
        return;
    }
    try {
        await API.post('/body', body);
        _meMsg('me-body-msg', '已记录', true);
        setTimeout(closeBodyModal, 700);
        ['me-body-weight', 'me-body-bf', 'me-body-hr', 'me-body-sleep'].forEach(function (id) {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        await loadBodyHistory();
        await loadPasskeys();
    } catch (e) {
        _meMsg('me-body-msg', e.message, false);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const b1 = document.getElementById('btn-save-profile');
    if (b1) b1.addEventListener('click', saveProfile);
    const b2 = document.getElementById('btn-save-body');
    if (b2) b2.addEventListener('click', saveBody);
    const b3 = document.getElementById('btn-logout-2');
    if (b3) b3.addEventListener('click', async function () {
        try { await API.post('/auth/logout'); } catch (e) {}
        showAuth();
    });
});

// ==========================================================
// Passkey / WebAuthn
// ==========================================================
function _b64uToBuf(s) {
    s = String(s).replace(/-/g, '+').replace(/_/g, '/');
    var pad = new Array((4 - s.length % 4) % 4 + 1).join('=');
    var bin = atob(s + pad);
    var buf = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    return buf.buffer;
}

function _bufToB64u(buf) {
    var bytes = new Uint8Array(buf);
    var bin = '';
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function passkeySupported() {
    return !!(window.PublicKeyCredential && navigator.credentials && navigator.credentials.create);
}

// Passkey / WebAuthn 错误翻译（浏览器原生报错均为英文）
function pkFriendly(e) {
    var name = (e && e.name) || '';
    var msg = String((e && e.message) || '');
    if (name === 'NotAllowedError' || msg.indexOf('not allowed') >= 0) {
        return '已取消，或验证超时。请重试并在弹窗里完成指纹 / 面容验证';
    }
    if (name === 'InvalidStateError' || msg.indexOf('already registered') >= 0) {
        return '这台设备已经绑定过了，无需重复绑定';
    }
    if (name === 'SecurityError') {
        return '当前页面不是 HTTPS，指纹 / 面容登录需要 HTTPS 环境';
    }
    if (name === 'NotSupportedError') {
        return '这个浏览器不支持指纹 / 面容登录，请改用密码登录';
    }
    if (msg.indexOf('A request is already pending') >= 0 || msg.indexOf('pending') >= 0) {
        return '上一次验证还没结束，请等 2 秒再点一次';
    }
    if (msg.indexOf('Failed to fetch') >= 0 || name === 'TypeError') {
        return '网络连不上服务器，请检查手机网络后重试';
    }
    if (!msg) return '验证失败，请重试或改用密码登录';
    return msg;
}

function _pkMsg(elId, text, ok) {
    var el = document.getElementById(elId);
    if (!el) return;
    el.textContent = text;
    el.classList.remove('hidden', 'text-emerald-600', 'text-rose-600');
    el.classList.add(ok ? 'text-emerald-600' : 'text-rose-600');
    setTimeout(function () { el.classList.add('hidden'); }, 3000);
}

async function passkeyRegister() {
    if (!passkeySupported()) {
        _pkMsg('pk-msg', '此浏览器不支持 Passkey', false);
        return;
    }
    try {
        var begin = await API.post('/auth/passkey/register/begin', {});
        var o = begin.options;
        o.challenge = _b64uToBuf(o.challenge);
        if (o.user && o.user.id) o.user.id = _b64uToBuf(o.user.id);
        if (o.excludeCredentials) {
            o.excludeCredentials = o.excludeCredentials.map(function (c) {
                c.id = _b64uToBuf(c.id);
                return c;
            });
        }
        var cred = await navigator.credentials.create({ publicKey: o });
        var transports = cred.response.getTransports ? cred.response.getTransports() : [];
        var payload = {
            id: cred.id,
            rawId: _bufToB64u(cred.rawId),
            type: cred.type,
            response: {
                clientDataJSON: _bufToB64u(cred.response.clientDataJSON),
                attestationObject: _bufToB64u(cred.response.attestationObject),
                transports: transports
            },
            clientExtensionResults: cred.getClientExtensionResults ? cred.getClientExtensionResults() : {}
        };
        var ua = navigator.userAgent;
        var name = (ua.indexOf('iPhone') >= 0 || ua.indexOf('iPad') >= 0) ? 'iPhone / iPad'
                 : (ua.indexOf('Mac') >= 0 ? 'Mac' : (ua.indexOf('Windows') >= 0 ? 'Windows' : '本机设备'));
        await API.post('/auth/passkey/register/finish', {
            challenge_token: begin.challenge_token,
            credential: payload,
            name: name
        });
        _pkMsg('pk-msg', '已绑定，下次可指纹 / 面容登录', true);
        await loadPasskeys();
    } catch (e) {
        _pkMsg('pk-msg', '绑定失败：' + pkFriendly(e), false);
    }
}

async function passkeyLogin() {
    var errEl = document.getElementById('auth-error');
    if (!passkeySupported()) {
        if (errEl) { errEl.textContent = '此浏览器不支持 Passkey（需 HTTPS 或 localhost）'; errEl.classList.remove('hidden'); }
        return;
    }
    var uEl = document.getElementById('auth-user');
    var username = uEl ? uEl.value.trim() : '';
    try {
        var begin = await API.post('/auth/passkey/login/begin', { username: username || null });
        var o = begin.options;
        o.challenge = _b64uToBuf(o.challenge);
        if (o.allowCredentials) {
            o.allowCredentials = o.allowCredentials.map(function (c) {
                c.id = _b64uToBuf(c.id);
                return c;
            });
        }
        var cred = await navigator.credentials.get({ publicKey: o });
        var payload = {
            id: cred.id,
            rawId: _bufToB64u(cred.rawId),
            type: cred.type,
            response: {
                clientDataJSON: _bufToB64u(cred.response.clientDataJSON),
                authenticatorData: _bufToB64u(cred.response.authenticatorData),
                signature: _bufToB64u(cred.response.signature),
                userHandle: cred.response.userHandle ? _bufToB64u(cred.response.userHandle) : null
            },
            clientExtensionResults: cred.getClientExtensionResults ? cred.getClientExtensionResults() : {}
        };
        await API.post('/auth/passkey/login/finish', {
            challenge_token: begin.challenge_token,
            credential: payload
        });
        showApp();
    } catch (e) {
        if (errEl) {
            errEl.textContent = '登录失败：' + pkFriendly(e);
            errEl.classList.remove('hidden');
        }
    }
}

async function loadPasskeys() {
    var box = document.getElementById('pk-list');
    if (!box) return;
    try {
        var d = await API.get('/auth/passkey/list');
        var items = d.items || [];
        if (!items.length) {
            box.innerHTML = '<div class="text-slate-400 text-xs">还没有绑定任何设备</div>';
            return;
        }
        box.innerHTML = items.map(function (it) {
            var created = (it.created_at || '').slice(0, 10);
            var used = it.last_used_at ? ' · 上次使用 ' + it.last_used_at.slice(0, 10) : '';
            return '<div class="flex justify-between items-center border-b border-slate-50 py-1">' +
                '<div><div class="text-sm text-slate-700">' + (it.name || '设备') + '</div>' +
                '<div class="text-[11px] text-slate-400">绑定于 ' + created + used + '</div></div>' +
                '<button class="text-rose-500 text-xs" onclick="passkeyDelete(' + it.id + ')">移除</button>' +
                '</div>';
        }).join('');
    } catch (e) {
        box.innerHTML = '<div class="text-rose-500 text-xs">' + e.message + '</div>';
    }
}

async function passkeyDelete(id) {
    if (!confirm('确定移除这个设备？移除后该设备不能再用指纹登录')) return;
    try {
        await API.delete('/auth/passkey/' + id);
        await loadPasskeys();
    } catch (e) {
        alert('移除失败：' + e.message);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    var bReg = document.getElementById('btn-pk-register');
    if (bReg) bReg.addEventListener('click', passkeyRegister);

    var bLogin = document.getElementById('btn-pk-login');
    if (bLogin) bLogin.addEventListener('click', passkeyLogin);

    if (!passkeySupported()) {
        var hint = document.getElementById('pk-hint');
        if (hint) hint.textContent = '当前环境不支持 Passkey（需 HTTPS 或 localhost）';
    }
});
// ==========================================================
// AI 设置（每用户自己的 Key）
// ==========================================================
function _aiMsg(text, ok) {
    var el = document.getElementById('ai-msg');
    if (!el) return;
    el.textContent = text;
    el.classList.remove('hidden', 'text-emerald-600', 'text-rose-600');
    el.classList.add(ok ? 'text-emerald-600' : 'text-rose-600');
    setTimeout(function () { el.classList.add('hidden'); }, 3500);
}

async function loadAiConfig() {
    try {
        var d = await API.get('/settings/llm');
        var badge = document.getElementById('ai-status');
        if (badge) {
            if (d.own) {
                badge.textContent = '已配置（你自己的 Key）';
                badge.className = 'text-xs font-medium text-emerald-600';
            } else if (d.is_owner && d.configured) {
                badge.textContent = '使用站长默认 Key';
                badge.className = 'text-xs font-medium text-amber-600';
            } else {
                badge.textContent = '未配置 — AI 不可用';
                badge.className = 'text-xs font-medium text-rose-500';
            }
        }
        var kEl = document.getElementById('ai-key');
        if (kEl) {
            kEl.value = '';
            kEl.placeholder = d.own ? ('已保存：' + d.api_key_masked + '（留空不修改）') : 'sk-... 粘贴你的 API Key';
        }
        var bEl = document.getElementById('ai-base'); if (bEl) bEl.value = d.base_url || '';
        var mEl = document.getElementById('ai-model'); if (mEl) mEl.value = d.model || '';
        var vEl = document.getElementById('ai-vmodel'); if (vEl) vEl.value = d.vision_model || '';
        var hint = document.getElementById('ai-hint');
        if (hint) {
            hint.textContent = d.own
                ? 'Key 只存在本机数据库，仅用于调用你自己的 AI 服务。'
                : '未配置时 AI 教练、拍照识餐不可用。可到 platform.deepseek.com 申请 Key。';
        }
    } catch (e) { console.error('loadAiConfig', e); }
}

async function saveAiConfig() {
    var body = {};
    var k = document.getElementById('ai-key'); if (k && k.value.trim()) body.api_key = k.value.trim();
    var b = document.getElementById('ai-base'); if (b && b.value.trim()) body.base_url = b.value.trim();
    var m = document.getElementById('ai-model'); if (m && m.value.trim()) body.model = m.value.trim();
    var v = document.getElementById('ai-vmodel'); if (v && v.value.trim()) body.vision_model = v.value.trim();
    if (!Object.keys(body).length) { _aiMsg('没有需要保存的改动', false); return; }
    try {
        await API.put('/settings/llm', body);
        _aiMsg('已保存', true);
        await loadAiConfig(); await loadMe();
    } catch (e) { _aiMsg('保存失败：' + e.message, false); }
}

async function testAiConfig() {
    _aiMsg('正在测试...', true);
    try {
        var d = await API.post('/settings/llm/test', {});
        _aiMsg('可用，模型回复：' + (d.reply || 'OK'), true);
    } catch (e) { _aiMsg('测试失败：' + e.message, false); }
}

async function clearAiConfig() {
    if (!confirm('确定清除已保存的 API Key？清除后 AI 功能不可用。')) return;
    try {
        await API.delete('/settings/llm');
        _aiMsg('已清除', true);
        await loadAiConfig(); await loadMe();
    } catch (e) { _aiMsg('清除失败：' + e.message, false); }
}

// ==========================================================
// 身体数据趋势图
// ==========================================================
let _trendChart = null;
let _trendData = null;

async function loadTrends() {
    const canvas = document.getElementById('trend-chart');
    const empty = document.getElementById('trend-empty');
    const statsBox = document.getElementById('trend-stats');
    if (!canvas) return;
    try {
        const sel = document.getElementById('trend-metric');
        const rangeEl = document.getElementById('trend-range');
        const days = Number((rangeEl && rangeEl.value) || 90);
        const d = await API.get('/body/trends?days=' + days);
        _trendData = d;
        const avail = d.available || [];
        if (!avail.length) {
            if (empty) { empty.textContent = '还没有身体数据，点右上角 + 记一次'; empty.classList.remove('hidden'); }
            canvas.classList.add('hidden');
            if (statsBox) statsBox.innerHTML = '';
            return;
        }
        if (sel && sel.dataset.built !== '1') {
            sel.innerHTML = avail.map(function (k) {
                return '<option value="' + k + '">' + d.metrics[k].label + ' (' + d.metrics[k].unit + ')</option>';
            }).join('');
            sel.dataset.built = '1';
        }
        renderTrend(sel ? sel.value : avail[0], d);
    } catch (e) {
        if (empty) { empty.textContent = '加载失败：' + e.message; empty.classList.remove('hidden'); }
    }
}

function renderTrend(key, d) {
    const canvas = document.getElementById('trend-chart');
    const empty = document.getElementById('trend-empty');
    const statsBox = document.getElementById('trend-stats');
    const m = d.metrics[key];
    if (!m || !m.series || !m.series.length) {
        if (empty) { empty.textContent = '该指标暂无数据'; empty.classList.remove('hidden'); }
        canvas.classList.add('hidden');
        if (statsBox) statsBox.innerHTML = '';
        return;
    }
    if (empty) empty.classList.add('hidden');
    canvas.classList.remove('hidden');

    const labels = m.series.map(function (p) { return p.date.slice(5); });
    const values = m.series.map(function (p) { return p.value; });

    if (_trendChart) _trendChart.destroy();
    _trendChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                borderColor: '#0ea5e9',
                backgroundColor: 'rgba(14,165,233,0.12)',
                borderWidth: 2,
                pointRadius: values.length > 40 ? 0 : 3,
                pointHoverRadius: 5,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: function (ctx) { return ctx.parsed.y + ' ' + m.unit; } } }
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 6, font: { size: 10 } } },
                y: { grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { font: { size: 10 } } }
            }
        }
    });

    if (statsBox) {
        const sign = m.delta > 0 ? '+' : '';
        const color = m.delta > 0 ? 'text-rose-500' : (m.delta < 0 ? 'text-emerald-600' : 'text-slate-500');
        statsBox.innerHTML =
            '<div class="grid grid-cols-4 gap-2 text-center text-xs">' +
            '<div class="bg-slate-50 rounded-lg p-2"><div class="text-slate-400">最新</div><div class="font-bold text-slate-700 mt-1">' + m.last + '</div></div>' +
            '<div class="bg-slate-50 rounded-lg p-2"><div class="text-slate-400">变化</div><div class="font-bold ' + color + ' mt-1">' + sign + m.delta + '</div></div>' +
            '<div class="bg-slate-50 rounded-lg p-2"><div class="text-slate-400">最低</div><div class="font-bold text-slate-700 mt-1">' + m.min + '</div></div>' +
            '<div class="bg-slate-50 rounded-lg p-2"><div class="text-slate-400">最高</div><div class="font-bold text-slate-700 mt-1">' + m.max + '</div></div>' +
            '</div>' +
            '<div class="text-[11px] text-slate-400 mt-2 text-center">共 ' + m.count + ' 条 · 均值 ' + m.avg + ' ' + m.unit + '</div>';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const ms = document.getElementById('trend-metric');
    if (ms) ms.addEventListener('change', function () { if (_trendData) renderTrend(ms.value, _trendData); });
    const rg = document.getElementById('trend-range');
    if (rg) rg.addEventListener('change', loadTrends);
});


// ==========================================================
// \u8bbe\u7f6e\u9875\uff08AI Key / \u5bc6\u7801 / Passkey\uff09
// ==========================================================
function _setMsg(elId, text, ok) {
    var el = document.getElementById(elId);
    if (!el) return;
    el.textContent = text;
    el.classList.remove('hidden');
    el.style.color = ok ? '#059669' : '#e11d48';
    setTimeout(function () { el.classList.add('hidden'); }, 3500);
}

async function loadSettings() {
    try {
        var p = await API.get('/profile');
        var u = document.getElementById('set-username');
        if (u) u.textContent = p.username || '--';
        var l = document.getElementById('set-llm');
        if (l) {
            l.textContent = p.llm_configured ? '\u5df2\u8fde\u63a5' : '\u672a\u914d\u7f6e';
            l.style.color = p.llm_configured ? '#059669' : '#e11d48';
        }
    } catch (e) { console.warn('loadSettings profile', e); }
    try { await loadAiConfig(); } catch (e) { console.warn('loadAiConfig', e); }
    try { await loadPasskeys(); } catch (e) { console.warn('loadPasskeys', e); }
}

async function changePassword() {
    var oldPwd = (document.getElementById('pwd-old') || {}).value || '';
    var newPwd = (document.getElementById('pwd-new') || {}).value || '';
    var newPwd2 = (document.getElementById('pwd-new2') || {}).value || '';
    if (!oldPwd || !newPwd) { _setMsg('pwd-msg', '\u8bf7\u586b\u5199\u5b8c\u6574', false); return; }
    if (newPwd.length < 8) { _setMsg('pwd-msg', '\u65b0\u5bc6\u7801\u81f3\u5c11 8 \u4f4d', false); return; }
    if (newPwd !== newPwd2) { _setMsg('pwd-msg', '\u4e24\u6b21\u8f93\u5165\u4e0d\u4e00\u81f4', false); return; }
    try {
        await API.post('/auth/password', { old_password: oldPwd, new_password: newPwd });
        _setMsg('pwd-msg', '\u5bc6\u7801\u5df2\u66f4\u65b0', true);
        ['pwd-old', 'pwd-new', 'pwd-new2'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.value = '';
        });
    } catch (e) {
        _setMsg('pwd-msg', '\u5931\u8d25\uff1a' + e.message, false);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // AI \u8bbe\u7f6e\u4e09\u4e2a\u6309\u94ae\uff08\u4e4b\u524d\u5b8c\u5168\u6ca1\u7ed1\u5b9a\uff09
    var a1 = document.getElementById('btn-ai-save');
    if (a1) a1.addEventListener('click', saveAiConfig);
    var a2 = document.getElementById('btn-ai-test');
    if (a2) a2.addEventListener('click', testAiConfig);
    var a3 = document.getElementById('btn-ai-clear');
    if (a3) a3.addEventListener('click', clearAiConfig);

    // \u4fee\u6539\u5bc6\u7801
    var b1 = document.getElementById('btn-save-password');
    if (b1) b1.addEventListener('click', changePassword);

    // \u9000\u51fa\u767b\u5f55
    var b2 = document.getElementById('btn-logout-3');
    if (b2) b2.addEventListener('click', async function () {
        try { await API.post('/auth/logout'); } catch (e) {}
        showAuth();
    });

    // Passkey \u7ed1\u5b9a
    var b3 = document.getElementById('btn-pk-register');
    if (b3) b3.addEventListener('click', passkeyRegister);
});

// ==========================================================
// 报告面板（按类型切换 + 按次数列表）
// ==========================================================
var QUICK_META = {
    'btn-weekly': { module: 'weekly', label: '周报' },
    'btn-plan': { module: 'plan', label: '训练计划' },
    'btn-run-advice': { module: 'run', label: '跑步分析' },
    'btn-diet-advice': { module: 'diet', label: '饮食分析' }
};

var REPORT_PROMPT = {
    weekly: '请根据我最近 7 天的全部数据生成周复盘报告：1) 训练完成度 2) 跑步表现 3) 力量进展 4) 饮食执行 5) 下周三个最重要的调整建议。用中文，条理清晰。',
    plan: '请基于我最近 4 周训练数据给出下周训练计划：力量按三分化，写清动作、组数、次数和具体配重；跑步 2-3 次写明类型、距离、配速区间；给出热量与蛋白质目标。',
    run: '请作为跑步数据分析师深度分析我最近的跑步数据：配速分段、心率漂移、步频、有氧效率。指出最需改进的两个点并给出训练手段。',
    diet: '请作为营养师结合我的训练量、跑步消耗、体重趋势和目标评估饮食：总热量、蛋白质、碳水、训练日与休息日区分。给出具体到食物的建议。'
};

var _activeReport = 'btn-weekly';

var _reportsInited = false;
function initReports() {
    if (_reportsInited) return;
    _reportsInited = true;
    Object.keys(QUICK_META).forEach(function (id) {
        var btn = document.getElementById(id);
        if (!btn) return;
        btn.addEventListener('click', function () {
            _activeReport = id;
            Object.keys(QUICK_META).forEach(function (k) {
                var b = document.getElementById(k);
                if (!b) return;
                b.className = 'shrink-0 text-xs px-3 py-1.5 rounded-lg font-medium ' +
                    (k === id ? 'bg-brand text-white' : 'bg-slate-100 text-slate-700');
            });
            loadReportList();
        });
    });

    var genBtn = document.getElementById('btn-gen-report');
    if (genBtn) {
        genBtn.addEventListener('click', async function () {
            if (genBtn.disabled) return;
            var meta = QUICK_META[_activeReport];
            if (!meta) return;
            genBtn.disabled = true;
            var old = genBtn.textContent;
            var _cfg = null;
            try { _cfg = await API.get('/settings/llm'); } catch (e) {}
            if (!_cfg || !_cfg.configured) {
                genBtn.disabled = false;
                showLlmHint();
                return;
            }
            genBtn.textContent = '生成中...';
            try {
                await API.post('/coach/chat', { message: REPORT_PROMPT[meta.module], module: meta.module });
                await loadReportList();
            } catch (e) {
                alert('生成失败：' + e.message);
            } finally {
                genBtn.disabled = false;
                genBtn.textContent = old;
            }
        });
    }

    var listBox = document.getElementById('report-list');
    if (listBox) {
        listBox.addEventListener('click', function (ev) {
            var head = ev.target.closest('[data-report-id]');
            if (!head) return;
            var body = document.getElementById('report-body-' + head.dataset.reportId);
            if (body) body.classList.toggle('hidden');
        });
    }

    loadReportList();
}

async function loadReportList() {
    var box = document.getElementById('report-list');
    if (!box) return;
    var meta = QUICK_META[_activeReport];
    var module = meta ? meta.module : 'weekly';
    box.innerHTML = '<div class="text-center py-4 text-xs text-slate-400">加载中...</div>';
    try {
        var d = await API.get('/coach/history?module=' + encodeURIComponent(module) + '&limit=40');
        var rows = (d.items || []).filter(function (m) { return m.role === 'assistant'; });
        if (!rows.length) {
            box.innerHTML = '<div class="text-center text-xs text-slate-400 py-6">还没有这类报告，点上面的生成试试</div>';
            return;
        }
        rows.sort(function (a, b) { return b.id - a.id; });
        box.innerHTML = rows.map(function (m, i) {
            var at = m.at ? m.at.replace('T', ' ').slice(0, 16) : '';
            var preview = (m.content || '').replace(/[#*\n]/g, ' ').slice(0, 40);
            return '<div class="border border-slate-100 rounded-lg overflow-hidden">' +
                '<div data-report-id="' + m.id + '" class="px-3 py-2 bg-slate-50 cursor-pointer flex justify-between items-center">' +
                    '<div class="min-w-0">' +
                        '<span class="text-xs font-bold text-slate-700">第 ' + (rows.length - i) + ' 次</span>' +
                        '<span class="text-xs text-slate-400 ml-2">' + at + '</span>' +
                        '<div class="text-xs text-slate-400 truncate">' + preview + '</div>' +
                    '</div>' +
                    '<svg class="w-4 h-4 text-slate-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>' +
                '</div>' +
                '<div id="report-body-' + m.id + '" class="hidden px-3 py-2 text-xs text-slate-600 leading-relaxed chat-content">' +
                    formatMarkdown(m.content || '') +
                '</div>' +
            '</div>';
        }).join('');
    } catch (e) {
        box.innerHTML = '<div class="text-xs text-rose-500">加载失败：' + e.message + '</div>';
    }
}

// 设置入口 + 报告面板初始化
document.addEventListener('DOMContentLoaded', function () {
    var sb = document.getElementById('btn-open-settings');
    if (sb) sb.addEventListener('click', function () { switchTab('settings'); });
});

// 设置页返回按钮
document.addEventListener('DOMContentLoaded', function () {
    var bb = document.getElementById('btn-back-settings');
    if (bb) bb.addEventListener('click', function () { switchTab('me'); });
});

// 基础资料次级页 + 返回
document.addEventListener('DOMContentLoaded', function () {
    var op = document.getElementById('btn-open-profile');
    if (op) op.addEventListener('click', function () { switchTab('profile'); });
    var bp = document.getElementById('btn-back-profile');
    if (bp) bp.addEventListener('click', function () { switchTab('me'); });
});

// Apple 健康数据导入
document.addEventListener('DOMContentLoaded', function () {
    var hu = document.getElementById('health-upload');
    if (!hu) return;
    hu.addEventListener('change', async function (e) {
        var f = e.target.files && e.target.files[0];
        if (!f) return;
        var msg = document.getElementById('health-msg');
        function show(t, ok) {
            if (!msg) return;
            msg.textContent = t;
            msg.classList.remove('hidden');
            msg.style.color = ok ? '#059669' : '#e11d48';
        }
        show('上传解析中，大文件可能需要几分钟...', true);
        var fd = new FormData();
        fd.append('file', f);
        try {
            var res = await fetch('/api/health/import', { method: 'POST', body: fd });
            var d = await res.json();
            if (!res.ok) throw new Error(d.detail || '导入失败');
            show('导入完成：训练 ' + d.runs_imported + ' 条，新增 ' + d.body_days_added + ' 天身体数据，更新 ' + d.body_days_updated + ' 天', true);
            if (typeof loadDashboard === 'function') loadDashboard();
            if (typeof loadTrends === 'function') loadTrends();
        } catch (err) {
            show('失败：' + err.message, false);
        } finally {
            hu.value = '';
        }
    });
});

// ==========================================================
// 力量页：日/周/月/年切换 + 下拉刷新
// ==========================================================
document.addEventListener('DOMContentLoaded', function () {
    var wrap = document.getElementById('trend-grain');
    if (wrap) {
        wrap.addEventListener('click', function (ev) {
            var b = ev.target.closest('[data-grain]');
            if (!b) return;
            _strengthGrain = b.dataset.grain;
            wrap.querySelectorAll('[data-grain]').forEach(function (x) {
                var on = x.dataset.grain === _strengthGrain;
                x.className = 'grain-btn text-xs px-2.5 py-1 rounded-lg ' + (on ? 'bg-brand text-white' : 'bg-slate-100 text-slate-600');
            });
            loadStrengthTrend();
        });
    }

    // 力量页「导入健康数据」跳到设置
    var ih = document.getElementById('btn-import-health2');
    if (ih) ih.addEventListener('click', function () { switchTab('settings'); });
});

// 下拉刷新
(function () {
    var startY = 0, pulling = false, indicator = null;
    function getIndicator() {
        if (indicator) return indicator;
        indicator = document.createElement('div');
        indicator.id = 'pull-indicator';
        indicator.style.cssText = 'position:fixed;top:0;left:0;right:0;height:0;background:#0ea5e9;color:#fff;' +
            'display:flex;align-items:center;justify-content:center;font-size:12px;overflow:hidden;' +
            'transition:height .2s;z-index:9999;';
        indicator.textContent = '下拉刷新';
        document.body.appendChild(indicator);
        return indicator;
    }
    document.addEventListener('touchstart', function (e) {
        if (window.scrollY > 0) return;
        startY = e.touches[0].clientY;
        pulling = true;
    }, { passive: true });
    document.addEventListener('touchmove', function (e) {
        if (!pulling) return;
        var dy = e.touches[0].clientY - startY;
        if (dy > 0 && window.scrollY <= 0) {
            var ind = getIndicator();
            ind.style.height = Math.min(dy * 0.4, 60) + 'px';
            ind.textContent = dy > 120 ? '松开刷新' : '下拉刷新';
        }
    }, { passive: true });
    document.addEventListener('touchend', function (e) {
        if (!pulling) return;
        pulling = false;
        var ind = getIndicator();
        var dy = (e.changedTouches[0].clientY - startY);
        if (dy > 120) {
            ind.textContent = '刷新中...';
            ind.style.height = '44px';
            setTimeout(function () {
                if (typeof switchTab === 'function' && typeof currentTab !== 'undefined') {
                    switchTab(currentTab);
                }
                ind.style.height = '0px';
            }, 300);
        } else {
            ind.style.height = '0px';
        }
    }, { passive: true });
})();

// ==========================================================
// 力量记录编辑弹窗
// ==========================================================
var _editWorkout = null;

async function editWorkout(wid) {
    try {
        var d = await API.get('/workouts?limit=50');
        var w = (d.items || []).find(function (x) { return x.id === wid; });
        if (!w) { alert('记录不存在'); return; }
        _editWorkout = w;
        renderEditModal(w);
        document.getElementById('modal-edit-workout').classList.remove('hidden');
    } catch (e) { alert('加载失败：' + e.message); }
}

function renderEditModal(w) {
    document.getElementById('edit-workout-name').value = w.name || '';
    document.getElementById('edit-workout-date').value = String(w.date || '').slice(0, 10);
    document.getElementById('edit-workout-duration').value = w.duration_min || '';
    var box = document.getElementById('edit-set-list');
    box.innerHTML = (w.sets || []).map(function (s, i) {
        return '<div class="flex items-center gap-2 py-1.5 border-b border-slate-50">'
            + '<span class="text-xs text-slate-400 w-5">' + (i + 1) + '</span>'
            + '<span class="text-xs text-slate-700 flex-1 truncate">' + (s.exercise_name || ('动作' + s.exercise_id)) + '</span>'
            + '<input type="number" data-edit-idx="' + i + '" data-field="reps" value="' + (s.reps || '') + '" class="w-14 text-xs border border-slate-200 rounded px-1.5 py-1" placeholder="次">'
            + '<input type="number" step="0.5" data-edit-idx="' + i + '" data-field="weight" value="' + (s.weight_kg || '') + '" class="w-16 text-xs border border-slate-200 rounded px-1.5 py-1" placeholder="kg">'
            + '<button data-edit-del="' + i + '" class="text-xs text-rose-500 px-1">删</button>'
            + '</div>';
    }).join('') || '<div class="text-xs text-slate-400 py-3 text-center">没有动作</div>';
}

async function saveWorkoutEdit() {
    if (!_editWorkout) return;
    var sets = [];
    var rows = document.querySelectorAll('#edit-set-list [data-edit-idx]');
    var byIdx = {};
    rows.forEach(function (inp) {
        var i = inp.dataset.editIdx;
        byIdx[i] = byIdx[i] || {};
        byIdx[i][inp.dataset.field] = inp.value;
    });
    (_editWorkout.sets || []).forEach(function (s, i) {
        if (!byIdx[i]) return;
        sets.push({
            exercise_id: s.exercise_id,
            idx: sets.length,
            reps: byIdx[i].reps ? Number(byIdx[i].reps) : null,
            weight_kg: byIdx[i].weight ? Number(byIdx[i].weight) : null,
            rpe: s.rpe || null,
            is_warmup: !!s.is_warmup,
            rest_s: s.rest_s || null,
            note: s.note || null
        });
    });
    if (!sets.length) { alert('至少保留一组'); return; }
    var body = {
        date: document.getElementById('edit-workout-date').value,
        name: document.getElementById('edit-workout-name').value || '训练',
        focus: _editWorkout.focus || null,
        duration_min: Number(document.getElementById('edit-workout-duration').value) || null,
        rpe: _editWorkout.rpe || null,
        notes: _editWorkout.notes || null,
        sets: sets
    };
    try {
        await API.put('/workouts/' + _editWorkout.id, body);
        document.getElementById('modal-edit-workout').classList.add('hidden');
        _editWorkout = null;
        await loadStrength();
    } catch (e) { alert('保存失败：' + e.message); }
}

document.addEventListener('DOMContentLoaded', function () {
    var sv = document.getElementById('btn-save-workout-edit');
    if (sv) sv.addEventListener('click', saveWorkoutEdit);
    var cl = document.getElementById('btn-close-workout-edit');
    if (cl) cl.addEventListener('click', function () {
        document.getElementById('modal-edit-workout').classList.add('hidden');
        _editWorkout = null;
    });
    var box = document.getElementById('edit-set-list');
    if (box) box.addEventListener('click', function (ev) {
        var del = ev.target.closest('[data-edit-del]');
        if (!del) return;
        var i = del.dataset.editDel;
        _editWorkout.sets.splice(Number(i), 1);
        renderEditModal(_editWorkout);
    });
});

// ==========================================================
// 编辑当天训练记录（整体替换）
// ==========================================================
var _editingWorkout = null;

async function editWorkout(wid) {
    try {
        var d = await API.get('/workouts?limit=60');
        var w = (d.items || []).find(function (x) { return x.id === wid; });
        if (!w) { alert('记录不存在'); return; }
        _editingWorkout = w;

        var modal = document.getElementById('modal-log');
        var titleEl = document.getElementById('log-title');
        var items = document.getElementById('log-items');
        if (titleEl) titleEl.textContent = '编辑：' + (w.name || '训练记录');

        var sets = w.sets || [];
        var html = '<div class="text-xs text-slate-400 mb-2">修改重量或 RPE，保存后整条记录会被替换</div>';
        sets.forEach(function (st, i) {
            var nm = st.exercise_name || ('动作' + (st.exercise_id || ''));
            html += '<div class="flex items-center gap-2 bg-slate-50 p-2.5 rounded-xl">';
            html += '<div class="flex-1 min-w-0">';
            html += '<div class="text-sm font-medium text-slate-700 truncate">' + nm + '</div>';
            html += '<div class="text-xs text-slate-400">第 ' + (i + 1) + ' 组 · ' + (st.reps || 0) + ' 次</div>';
            html += '</div>';
            html += '<input type="number" step="0.5" data-set-idx="' + i + '" value="' + (st.weight_kg || '') + '" placeholder="kg" class="w-20 text-center border border-slate-300 rounded p-1.5 text-sm bg-white">';
            html += '<input type="number" step="0.5" data-rpe-idx="' + i + '" value="' + (st.rpe || '') + '" placeholder="RPE" class="w-16 text-center border border-slate-300 rounded p-1.5 text-sm bg-white">';
            html += '</div>';
        });
        items.innerHTML = html;
        modal.classList.remove('hidden');

        var btn = document.getElementById('btn-save-log');
        btn.textContent = '保存修改';
    } catch (e) {
        alert('加载失败：' + e.message);
    }
}

async function saveWorkoutEdit() {
    var w = _editingWorkout;
    if (!w) return;
    var sets = [];
    (w.sets || []).forEach(function (st, i) {
        var wEl = document.querySelector('[data-set-idx="' + i + '"]');
        var rEl = document.querySelector('[data-rpe-idx="' + i + '"]');
        var wt = wEl && wEl.value !== '' ? parseFloat(wEl.value) : st.weight_kg;
        var rp = rEl && rEl.value !== '' ? parseFloat(rEl.value) : st.rpe;
        sets.push({
            exercise_id: st.exercise_id,
            idx: i,
            reps: st.reps,
            weight_kg: wt,
            rpe: rp,
            is_warmup: !!st.is_warmup,
            rest_s: st.rest_s,
            note: st.note
        });
    });
    var body = {
        date: w.date, name: w.name, focus: w.focus,
        duration_min: w.duration_min, rpe: w.rpe, notes: w.notes,
        sets: sets
    };
    var btn = document.getElementById('btn-save-log');
    btn.disabled = true; btn.textContent = '保存中...';
    try {
        await API.put('/workouts/' + w.id, body);
        document.getElementById('modal-log').classList.add('hidden');
        _editingWorkout = null;
        btn.textContent = '保存并生成记录';
        await loadStrength();
        alert('已更新');
    } catch (e) {
        alert('保存失败：' + e.message);
        btn.textContent = '保存修改';
    } finally {
        btn.disabled = false;
    }
}

function closeLogModal() {
    document.getElementById('modal-log').classList.add('hidden');
    if (typeof _editingWorkout !== 'undefined') _editingWorkout = null;
    if (typeof currentTemplateToLog !== 'undefined') currentTemplateToLog = null;
    var btn = document.getElementById('btn-save-log');
    if (btn) { btn.textContent = '保存并生成记录'; btn.disabled = false; }
    var t = document.getElementById('log-title');
    if (t) t.textContent = '填写训练数据';
}


// ==========================================================
// 首页“记录今天”加号 + AI 未配置提醒
// ==========================================================
async function refreshAiStatus() {
    var el = document.getElementById('dash-ai-status');
    if (!el) return;
    try {
        var d = await API.get('/settings/llm');
        if (d && d.configured) {
            el.className = 'text-xs font-medium text-emerald-600';
            el.textContent = '已配置';
            el.style.cursor = 'default';
            el.onclick = null;
        } else {
            el.className = 'text-xs font-medium text-rose-500 underline';
            el.textContent = '未配置 API';
            el.style.cursor = 'pointer';
            el.onclick = showLlmHint;
        }
    } catch (e) {
        el.className = 'text-xs font-medium text-slate-400';
        el.textContent = '状态未知';
    }
}

function showLlmHint() {
    var go = confirm('还没有配置 AI Key，所以 AI 教练无法生成内容。\n\n请到「我的」→「设置」→「AI 设置」里填入 DeepSeek API Key。\n\n现在就去配置吗？');
    if (go) switchTab('me');
}

function openBodyModal() {
    var m = document.getElementById('modal-body');
    if (!m) return;
    m.classList.remove('hidden');
    var msg = document.getElementById('me-body-msg');
    if (msg) { msg.classList.add('hidden'); msg.textContent = ''; }
}

function closeBodyModal() {
    var m = document.getElementById('modal-body');
    if (m) m.classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', function () {
    var qb = document.getElementById('btn-quick-body');
    if (qb) qb.addEventListener('click', openBodyModal);
    var cb = document.getElementById('btn-close-body');
    if (cb) cb.addEventListener('click', closeBodyModal);
    var mb = document.getElementById('modal-body');
    if (mb) mb.addEventListener('click', function (ev) { if (ev.target === mb) closeBodyModal(); });
});

// ==========================================================
// 统一错误文案（中文）
// ==========================================================
// 餐次选择器：用户点了就用点的，没点就按当前时间推断
var _mealSlot = null;
function _currentMealSlot() {
    var picked = document.querySelector('#meal-slot-pick [data-slot].is-picked');
    if (picked) return picked.dataset.slot;
    if (_mealSlot) return _mealSlot;
    var h = new Date().getHours();
    if (h < 10) return 'breakfast';
    if (h < 15) return 'lunch';
    if (h < 20) return 'dinner';
    return 'snack';
}
function _markSlotBtn(b) {
    document.querySelectorAll('#meal-slot-pick [data-slot]').forEach(function (x) {
        x.classList.remove('is-picked', 'bg-brand', 'text-white');
        x.classList.add('bg-slate-100', 'text-slate-600');
    });
    b.classList.add('is-picked', 'bg-brand', 'text-white');
    b.classList.remove('bg-slate-100', 'text-slate-600');
    _mealSlot = b.dataset.slot;
}
document.addEventListener('DOMContentLoaded', function () {
    var box = document.getElementById('meal-slot-pick');
    if (!box) return;
    box.addEventListener('click', function (ev) {
        var b = ev.target.closest('[data-slot]');
        if (b) _markSlotBtn(b);
    });
    // 默认高亮当前时间对应餐次
    var guess = document.querySelector('#meal-slot-pick [data-slot="' + _currentMealSlot() + '"]');
    if (guess) _markSlotBtn(guess);
});

// 手机照片动辄 5-10MB，直接上传会超时。先在本地压缩到长边 1280px、JPEG 0.82
function compressImage(file, maxSide, quality) {
    maxSide = maxSide || 1280;
    quality = quality || 0.82;
    return new Promise(function (resolve) {
        if (!file || !/^image\//.test(file.type || '')) return resolve(file);
        var url = URL.createObjectURL(file);
        var img = new Image();
        img.onload = function () {
            try {
                var w = img.naturalWidth, h = img.naturalHeight;
                var scale = Math.min(1, maxSide / Math.max(w, h));
                var cw = Math.round(w * scale), ch = Math.round(h * scale);
                var cv = document.createElement('canvas');
                cv.width = cw; cv.height = ch;
                cv.getContext('2d').drawImage(img, 0, 0, cw, ch);
                cv.toBlob(function (blob) {
                    URL.revokeObjectURL(url);
                    if (!blob) return resolve(file);
                    // 压缩后反而更大就用原图
                    resolve(blob.size < file.size ? blob : file);
                }, 'image/jpeg', quality);
            } catch (e) {
                URL.revokeObjectURL(url);
                resolve(file);
            }
        };
        img.onerror = function () { URL.revokeObjectURL(url); resolve(file); };
        img.src = url;
    });
}

function friendlyError(e) {
    var m = String((e && e.message) || e || '').trim();
    var low = m.toLowerCase();
    if (low.indexOf('failed to fetch') >= 0 || low.indexOf('networkerror') >= 0 || low.indexOf('load failed') >= 0) {
        return '网络连接中断，请检查手机网络后重试';
    }
    if (low.indexOf('timeout') >= 0 || low.indexOf('timed out') >= 0) {
        return '请求超时，请稍后重试（图片过大时请先压缩）';
    }
    if (low.indexOf('401') >= 0 || low.indexOf('unauthorized') >= 0) {
        return '登录已过期，请重新登录';
    }
    if (low.indexOf('413') >= 0) {
        return '图片太大（超过 12MB），请换一张小一点的';
    }
    if (low.indexOf('502') >= 0 || low.indexOf('503') >= 0 || low.indexOf('504') >= 0) {
        return '服务器暂时忙，请稍后重试';
    }
    return m || '未知错误';
}
