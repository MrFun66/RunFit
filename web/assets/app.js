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
            errEl.textContent = err.message;
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
    if (tabId === 'dashboard') loadDashboard();
    if (tabId === 'run') loadRuns();
    if (tabId === 'strength') loadStrength();
    if (tabId === 'nutrition') loadNutrition();
    if (tabId === 'coach') loadChatHistory();
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
async function loadStrength() {
    // 1. 加载历史训练
    const list = document.getElementById('workout-list');
    try {
        const data = await API.get('/workouts');
        if (!data.items.length) {
            list.innerHTML = '<div class="text-center text-slate-400 text-sm py-4">还没有力量训练记录。</div>';
        } else {
            list.innerHTML = data.items.map(w => `
                <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                    <div class="flex justify-between">
                        <div class="font-bold text-slate-700">${w.name || '自由训练'}</div>
                        <div class="text-xs text-slate-400">${w.date}</div>
                    </div>
                    <div class="text-xs text-slate-500 mt-2">${w.sets.length} 组 · ${w.duration_min || '?'} 分钟</div>
                </div>
            `).join('');
        }
    } catch (e) {}

    // 2. 加载图表
    try {
        const stats = await API.get('/strength/stats');
        const muscleData = stats.muscles.filter(m => m.sets > 0).sort((a,b) => b.sets - a.sets).slice(0, 8);
        if (muscleData.length) {
            renderStrengthChart(muscleData);
        }
    } catch (e) { console.error('图表加载失败', e); }
}

function renderStrengthChart(data) {
    const ctx = document.getElementById('strength-chart').getContext('2d');
    if (strengthChartInstance) strengthChartInstance.destroy();
    
    strengthChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.name),
            datasets: [{
                label: '近 7 天组数',
                data: data.map(d => d.sets),
                backgroundColor: '#0ea5e9',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { display: false } },
                x: { grid: { display: false } }
            }
        }
    });
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
                <input type="number" step="0.5" placeholder="重量" value="${it.last_weight_kg || ''}" class="w-full text-center border border-slate-300 rounded p-1 text-sm bg-white" id="weight-${it.exercise_id}">
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
            list.innerHTML = data.items.map(m => `
                <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 flex justify-between items-center">
                    <div>
                        <div class="font-bold text-slate-700">${m.description || '一餐'}</div>
                        <div class="text-xs text-slate-400 mt-1">${m.slot || '用餐'}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-brand font-bold text-lg">${Math.round(m.kcal || 0)} <span class="text-xs">kcal</span></div>
                        <div class="text-xs text-slate-500 mt-1">P:${m.protein_g||0} C:${m.carb_g||0} F:${m.fat_g||0}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) {
        list.innerHTML = '';
    }
}

// 拍照识餐
document.getElementById('meal-upload')?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const modal = document.getElementById('modal-meal');
    const container = document.getElementById('meal-result-items');
    modal.classList.remove('hidden');
    container.innerHTML = '<div class="text-center py-8"><span class="loader"></span> AI 正在识别食物...</div>';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const res = await fetch('/api/meals/photo', { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        
        currentMealResult = data;
        container.innerHTML = `
            <div class="text-sm text-slate-500 mb-2">识别置信度：${data.confidence === 'high' ? '高' : data.confidence === 'low' ? '低' : '中'}</div>
            ${data.items.map((it, i) => `
                <div class="bg-slate-50 p-3 rounded-xl mb-2">
                    <div class="flex justify-between items-center mb-1">
                        <span class="font-bold text-slate-700 text-sm">${it.name}</span>
                        <span class="text-xs text-slate-500">${it.grams}g</span>
                    </div>
                    <div class="flex gap-3 text-xs text-slate-500">
                        <span class="text-brand font-bold">${it.kcal} kcal</span>
                        <span>P ${it.protein_g}</span>
                        <span>C ${it.carb_g}</span>
                        <span>F ${it.fat_g}</span>
                    </div>
                </div>
            `).join('')}
            <div class="mt-4 pt-3 border-t border-slate-200 flex justify-between font-bold text-slate-800">
                <span>合计</span>
                <span>${data.total.kcal} kcal</span>
            </div>
            <div class="text-xs text-slate-400 mt-2">${data.note || ''}</div>
        `;
    } catch (err) {
        container.innerHTML = `<div class="text-red-500 text-center py-8">识别失败：${err.message}</div>`;
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
        await API.post('/meals', {
            date: new Date().toISOString().split('T')[0],
            slot: '正餐',
            description: desc,
            kcal: currentMealResult.total.kcal,
            protein_g: currentMealResult.total.protein_g,
            carb_g: currentMealResult.total.carb_g,
            fat_g: currentMealResult.total.fat_g
        });
        document.getElementById('modal-meal').classList.add('hidden');
        loadNutrition();
    } catch (e) {
        alert('保存失败：' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '确认并记录';
    }
});

// --- AI 教练 ---
function initChat() {
    const input = document.getElementById('chat-input');
    const send = document.getElementById('chat-send');
    
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

    // --- 快捷指令：一键周报 / 下周计划 / 跑步分析 / 饮食调整 ---
    const QUICK = {
        'btn-weekly': {
            label: '📊 生成周报',
            prompt: '请根据我最近 7 天的全部数据，生成一份周复盘报告。'
                + '必须包含：1) 训练完成度（力量次数/跑步公里数 vs 目标）；'
                + '2) 跑步表现（配速、心率漂移、步频、有氧效率变化趋势）；'
                + '3) 力量进展（各主要动作重量/容量变化，是否有停滞）；'
                + '4) 饮食执行（热量与蛋白质是否达标）；'
                + '5) 下周三个最重要的调整建议，按优先级排序。用中文，条理清晰。'
        },
        'btn-plan': {
            label: '📅 下周计划',
            prompt: '请基于我最近 4 周的训练数据与当前目标，给出下周的训练计划。'
                + '要求：1) 力量按三分化（推/拉/腿）安排，写清每天的动作、组数、次数和具体配重（配重必须基于我历史记录渐进超负荷）；'
                + '2) 跑步安排 2-3 次，写明类型（轻松跑/节奏跑/间歇）、距离、配速区间；'
                + '3) 说明力量与跑步如何错开避免相互干扰；'
                + '4) 给出本周热量与蛋白质的每日目标。'
        },
        'btn-run-advice': {
            label: '🏃 跑步分析',
            prompt: '请作为跑步数据分析师，深度分析我最近的跑步数据。'
                + '重点看：配速分段是否均匀、心率漂移（后半程心率是否明显高于前半程）、'
                + '步频是否偏低（低于 170 说明步幅过大）、触地时间与垂直振幅反映的跑姿效率、'
                + '有氧效率（同等配速下心率是否在下降，即 Aerobic Decoupling）。'
                + '指出最需要改进的两个点，并给出可执行的训练手段。'
        },
        'btn-diet-advice': {
            label: '🍽 饮食调整',
            prompt: '请作为营养师，结合我最近的力量训练量、跑步消耗、体重变化趋势和目标（减脂同时增肌），'
                + '评估我当前的饮食是否合理。重点：总热量是否匹配、蛋白质是否足够（每公斤体重 1.6-2.2g）、'
                + '碳水是否够支撑训练、训练日与休息日是否需要区分。给出具体到食物的调整建议。'
        },
    };

    Object.entries(QUICK).forEach(([id, cfg]) => {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.addEventListener('click', async () => {
            if (btn.disabled) return;
            const original = btn.textContent;
            btn.disabled = true;
            btn.textContent = '生成中...';
            appendChatMsg('user', cfg.label + '（' + cfg.prompt.slice(0, 0) + '）'.replace('（）', ''));
            const aiMsgEl = appendChatMsg('assistant', '<span class="loader"></span>');
            try {
                await streamCoachReply(cfg.prompt, aiMsgEl);
            } catch (e) {
                aiMsgEl.innerHTML = `<span class="text-red-500">出错：${e.message}</span>`;
            } finally {
                btn.disabled = false;
                btn.textContent = original;
            }
        });
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
    const div = document.createElement('div');
    div.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} w-full`;
    div.innerHTML = `<div class="${role === 'user' ? 'bg-brand text-white' : 'bg-white border border-slate-100 shadow-sm'} rounded-2xl ${role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'} px-4 py-2 max-w-[85%] text-sm chat-content">${html}</div>`;
    box.appendChild(div);
    if (scroll) scrollToBottom();
    return div.querySelector('.chat-content');
}

function scrollToBottom() {
    const box = document.getElementById('chat-box');
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