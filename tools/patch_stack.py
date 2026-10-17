import io

# ---------- app.js ----------
p = "web/assets/app.js"
s = io.open(p, encoding="utf-8").read()

start_marker = "async function loadStrengthTrend"
end_marker = "function editWorkout"
i = s.index(start_marker)
j = s.index(end_marker, i)
old = s[i:j]
assert "renderStrengthChart" in old, "block mismatch"

new = r'''async function loadStrengthTrend() {
    var canvas = document.getElementById('strength-chart');
    if (!canvas) return;
    try {
        var d = await API.get('/strength/trend?grain=' + _strengthGrain);
        var totalEl = document.getElementById('trend-total');
        var series = d.series || [];
        if (totalEl) {
            totalEl.textContent = d.total_volume > 0
                ? (d.active_buckets || 0) + ' \u4e2a\u65f6\u95f4\u6bb5\u6709\u8bad\u7ec3 \u00b7 \u603b\u5bb9\u91cf ' + Number(d.total_volume).toLocaleString() + ' kg'
                : '\u8fd9\u4e2a\u5468\u671f\u8fd8\u6ca1\u6709\u8bad\u7ec3\u6570\u636e';
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
        legend.innerHTML = series.length
            ? series.map(function (s) {
                return '<span class="inline-flex items-center gap-1 mr-2.5"><i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:' + s.color + '"></i>' + s.label + '</span>';
              }).join('')
            : '';
    }
    if (!series.length) return;

    var datasets = series.map(function (s) {
        return {
            label: s.label,
            data: s.data,
            backgroundColor: s.color,
            borderRadius: 3,
            stack: 'vol',
            maxBarThickness: 26
        };
    });

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
                            return c.dataset.label + ': ' + Number(c.parsed.y || 0).toLocaleString() + ' kg';
                        }
                    }
                }
            },
            scales: {
                x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 0, autoSkip: true } },
                y: { stacked: true, beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { size: 10 } } }
            }
        }
    });
}

'''
s = s[:i] + new + s[j:]
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("app.js patched, len", len(s))

# ---------- index.html ----------
h = io.open("web/index.html", encoding="utf-8").read()
if 'id="trend-legend"' not in h:
    anchor = '<div class="h-48">\n                        <canvas id="strength-chart"></canvas>\n                    </div>'
    assert anchor in h, "canvas anchor not found"
    h = h.replace(
        anchor,
        '<div class="h-44">\n                        <canvas id="strength-chart"></canvas>\n                    </div>\n                    <div id="trend-legend" class="text-xs text-slate-500 mt-2 text-center leading-relaxed"></div>'
    )
    io.open("web/index.html", "w", encoding="utf-8", newline="\n").write(h)
    print("index.html patched, legend added")
else:
    print("legend already exists")
