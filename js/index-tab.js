/* ===========================================================
   INDEX TAB — CFTC Supplemental (CIT) index-trader positions.
   Reads data/web/snapshot.json (cit, cit_agg) and series/<T>.json (cit).
   =========================================================== */
var _ixCharts = {};
function _ixK(n) { return COTInsights.k(n); }
function _ixSK(n) { return n == null ? '–' : COTInsights.sk(n); }
function _ixP(v) { return v == null ? '–' : (v >= 0 ? '+' : '') + v.toFixed(2); }
function _ixCls(v) { return v == null ? '' : v > 0 ? 'ix-pos' : v < 0 ? 'ix-neg' : ''; }

function initIndexTab() {
  COTStore.snapshot().then(function (snap) {
    var a = snap.cit_agg, rows = (snap.commodities || []).filter(function (c) { return c.cit; });
    if (!a || !rows.length) { document.getElementById('ixNote').textContent = 'Index-trader data is not available yet. It is added by the weekly update.'; return; }
    document.getElementById('ixDate').textContent = 'Report of ' + a.date + (a.rebal ? ' · ' : '');
    if (a.rebal) document.getElementById('ixDate').innerHTML += '<span class="ix-rb">January reweight window</span>';
    var kp = [
      { k: 'Markets adding (4 weeks)', v: a.adding4 + ' / ' + a.n, m: 'breadth ' + (a.breadth4 != null ? a.breadth4.toFixed(0) + '%' : '–') + (a.breadth4_pct != null ? ', ' + COTInsights.ord(a.breadth4_pct) + ' pct of history' : '') },
      { k: 'Markets adding (13 weeks)', v: a.adding13 + ' / ' + a.n, m: 'quarter-long trend in allocation' },
      { k: 'Avg share-of-OI change, 4w', v: _ixP(a.avg_dnp4), m: 'points of open interest' },
      { k: 'Avg share-of-OI change, 13w', v: _ixP(a.avg_dnp13), m: 'points of open interest' }
    ];
    Object.keys(a.sectors || {}).forEach(function (s) { kp.push({ k: s + ' (13w)', v: _ixP(a.sectors[s].dnp13), m: '4w ' + _ixP(a.sectors[s].dnp4) + ' pts' }); });
    document.getElementById('ixKpis').innerHTML = kp.map(function (x) { return '<div class="ix-kpi"><div class="k">' + x.k + '</div><div class="v">' + x.v + '</div><div class="m">' + x.m + '</div></div>'; }).join('');
    var br = COTInsights.brief(COTInsights.analyze(snap, {})).filter(function (l) { return l.h === 'Index flows'; })[0];
    document.getElementById('ixNote').textContent = br ? br.t : '';
    ixBreadth(a.breadth_hist);
    rows.sort(function (x, y) { return (y.cit.dnp13 || 0) - (x.cit.dnp13 || 0); });
    var sel = document.getElementById('ixSel');
    sel.innerHTML = rows.map(function (c) { return '<option value="' + c.ticker + '"' + (c.ticker === 'CT' ? ' selected' : '') + '>' + c.name + '</option>'; }).join('');
    document.getElementById('ixBody').innerHTML = rows.map(function (c) {
      var x = c.cit, mm = (((c.v || {}).all || {}).cats || {}).managed_money || {};
      return '<tr data-t="' + c.ticker + '"><td><b>' + c.name + '</b></td>' +
        '<td class="num">' + _ixK(x.N) + '</td><td class="num">' + (x.np != null ? x.np.toFixed(1) + '%' : '–') + '</td>' +
        '<td class="num ' + _ixCls(x.dN) + '">' + _ixSK(x.dN) + '</td><td class="num ' + _ixCls(x.dN4) + '">' + _ixSK(x.dN4) + '</td>' +
        '<td class="num ' + _ixCls(x.dN13) + '">' + _ixSK(x.dN13) + '</td><td class="num ' + _ixCls(x.dnp13) + '">' + _ixP(x.dnp13) + '</td>' +
        '<td class="num">' + (x.p && x.p.N && x.p.N.y3 != null ? COTInsights.ord(x.p.N.y3) : '–') + '</td>' +
        '<td class="num">' + _ixK(mm.N) + '</td><td class="num">' + (x.TL != null ? x.TL : '–') + '</td></tr>';
    }).join('');
    document.querySelectorAll('#ixBody tr').forEach(function (tr) {
      tr.onclick = function () { sel.value = tr.getAttribute('data-t'); ixChart(sel.value); };
    });
    ixChart(sel.value);
  });
}

function ixBreadth(h) {
  if (!h || !h.dates || typeof Chart === 'undefined') return;
  if (_ixCharts.b) _ixCharts.b.destroy();
  _ixCharts.b = new Chart(document.getElementById('ixBreadth'), {
    type: 'line',
    data: { labels: h.dates, datasets: [{ label: 'Share of markets where index net rose over 4 weeks (%)', data: h.v, borderColor: '#2a5298', backgroundColor: 'rgba(42,82,152,.12)', fill: true, pointRadius: 0, borderWidth: 1.6, tension: 0.2 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { labels: { boxWidth: 12, font: { size: 11 } } } },
      scales: { x: { type: 'time', time: { unit: 'year' } }, y: { min: 0, max: 100, ticks: { callback: function (v) { return v + '%'; } } } } }
  });
}

function ixChart(t) {
  if (!t) return;
  document.querySelectorAll('#ixBody tr').forEach(function (tr) { tr.classList.toggle('sel', tr.getAttribute('data-t') === t); });
  var from = document.getElementById('ixFrom').value + '-01-01';
  COTStore.series(t).then(function (s) {
    if (!s.cit) return;
    var mm = s.ct.all.managed_money, D = [], I = [], M = [], P = [];
    for (var i = 0; i < s.dates.length; i++) {
      if (s.dates[i] < from) continue;
      D.push(s.dates[i]);
      I.push(s.cit.l[i] != null ? s.cit.l[i] - s.cit.s[i] : null);
      M.push(mm.l[i] != null ? mm.l[i] - mm.s[i] : null);
      P.push(s.px ? s.px[i] : null);
    }
    document.getElementById('ixMktTitle').textContent = s.name + ': index vs funds';
    if (_ixCharts.m) _ixCharts.m.destroy();
    _ixCharts.m = new Chart(document.getElementById('ixMkt'), {
      type: 'line',
      data: { labels: D, datasets: [
        { label: 'Index traders net', data: I, borderColor: '#b7791f', pointRadius: 0, borderWidth: 2, yAxisID: 'y' },
        { label: 'Managed money net', data: M, borderColor: '#2a5298', pointRadius: 0, borderWidth: 1.6, yAxisID: 'y' },
        { label: 'Price (roll-adjusted)', data: P, borderColor: '#7f8c8d', pointRadius: 0, borderWidth: 1.2, borderDash: [4, 3], yAxisID: 'y1', spanGaps: true }
      ] },
      options: { maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { boxWidth: 12, font: { size: 11 } } } },
        scales: { x: { type: 'time', time: { unit: D.length > 400 ? 'year' : 'month' } },
          y: { title: { display: true, text: 'contracts' } },
          y1: { position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'price' } } } }
    });
  });
}
