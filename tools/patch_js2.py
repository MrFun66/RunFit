import io
p="web/assets/app.js"
s=io.open(p,encoding="utf-8").read()
i=s.index("async function loadStrengthTrend")
j=s.index("async function editWorkout", i)
new = r'''async function loadStrengthTrend() {
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
    if (!series.length || !buckets.length) return;

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

'''
s = s[:i] + new + s[j:]
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("app.js len", len(s))
