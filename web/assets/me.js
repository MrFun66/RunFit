// GRF Coach - 「我的」页面模块
// 依赖 app.js 中已定义的 API / showAuth

function _meMsg(elId, text, ok) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = text;
    el.classList.remove('hidden', 'text-emerald-600', 'text-rose-600');
    el.classList.add(ok ? 'text-emerald-600' : 'text-rose-600');
    setTimeout(() => el.classList.add('hidden'), 2600);
}

function _num(id) {
    const v = document.getElementById(id)?.value;
    if (v === undefined || v === null || v === '') return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}

function _str(id) {
    const v = document.getElementById(id)?.value;
    return (v === undefined || v === null || v === '') ? null : v;
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

        const llmEl = document.getElementById('me-llm');
        if (llmEl) {
            llmEl.textContent = p.llm_configured ? '已连接 DeepSeek' : '未配置';
            llmEl.className = 'font-medium ' + (p.llm_configured ? 'text-emerald-600' : 'text-rose-500');
        }

        await loadBodyHistory();
    } catch (e) {
        console.error('loadMe', e);
    }
}