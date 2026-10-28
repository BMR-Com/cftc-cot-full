/* ===========================================================
   SOFTS SEASONALS TAB — data/web/softs_seasonal.json
   =========================================================== */
var SFT = {D: null, mk: 'CT', scope: 'all', hm: 'avg', sp: 'avg', seas: null, chart: null, inited: false};

function initSoftsTab() {
  if (SFT.inited) return; SFT.inited = true;
  fetch('data/web/softs_seasonal.json?' + Date.now()).then(function (r) { return r.json(); }).then(function (j) {
    SFT.D = j;
    document.getElementById('sftAsof').textContent = 'ICE contract closes since 2000 · prices through ' + j.as_of + ' · rebuilt ' + j.generated;
    sftChips('#sftMk', Object.keys(j.markets).map(function (k) { return [k, j.markets[k].name]; }), SFT.mk, function (k) { SFT.mk = k; SFT.seas = null; sftAll(); });
    sftBind('[data-scope]', 'scope', sftTrades); sftBind('[data-hm]', 'hm', sftHeat); sftBind('[data-sp]', 'sp', sftSpread);
    sftAll();
  }).catch(function (e) { document.getElementById('sftAsof').textContent = 'Could not load softs data: ' + e; });
}

function sftBind(sel, key, fn) {
  document.querySelectorAll('#sft ' + sel).forEach(function (b) {
    b.onclick = function () {
      document.querySelectorAll('#sft ' + sel).forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on'); SFT[key] = b.getAttribute(sel.slice(1, -1)); fn();
    };
  });
}
function sftChips(id, items, cur, cb) {
  var g = document.querySelector(id); g.querySelectorAll('button').forEach(function (b) { b.remove(); });
  items.forEach(function (it) {
    var b = document.createElement('button'); b.className = 'sft-chip' + (it[0] === cur ? ' on' : ''); b.textContent = it[1];
    b.onclick = function () { cb(it[0]); }; g.appendChild(b);
  });
}
function sftAll() {
  var j = SFT.D; sftChips('#sftMk', Object.keys(j.markets).map(function (k) { return [k, j.markets[k].name]; }), SFT.mk, function (k) { SFT.mk = k; SFT.seas = null; sftAll(); });
  sftTrades(); sftSeas(); sftHeat(); sftSpread(); sftGrid(); sftFnd();
  document.getElementById('sftFoot').textContent = 'Seasonal tendencies, not forecasts: a rule that worked in 75% of years still fails one year in four. Prices are exchange closes; results exclude commissions and slippage.';
}

var SFT_MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function sftCol(v, scale) { // diverging green/red background
  if (v == null || isNaN(v)) return '';
  var a = Math.min(1, Math.abs(v) / scale) * 0.55;
  return v >= 0 ? 'background:rgba(15,122,61,' + a.toFixed(3) + ')' : 'background:rgba(196,48,43,' + a.toFixed(3) + ')';
}
function sftFmt(v, d) { return v == null ? '–' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d == null ? 1 : d); }
function sftDays(d) { return Math.round((new Date(d + 'T00:00:00Z') - new Date(SFT.D.as_of + 'T00:00:00Z')) / 864e5); }

function sftTrades() {
  var j = SFT.D, mk = j.markets[SFT.mk];
  var L = j.trades.filter(function (t) { return SFT.scope === 'all' || t.root === SFT.mk; });
  L.sort(function (a, b) { return (a.next_entry || '9') < (b.next_entry || '9') ? -1 : 1; });
  var h = '<thead><tr><th>Market</th><th>Trade</th><th>Next window</th><th>% of years worked</th><th>Last 10 yrs</th><th>Average per trade</th><th>Worst year</th><th>Last 5 years</th><th>Years</th></tr></thead><tbody>';
  if (!L.length) h += '<tr><td colspan="9" class="mu">No rule passes the screen for this market.</td></tr>';
  L.forEach(function (t) {
    var u = j.markets[t.root].unit, d = sftDays(t.next_entry), soon = d >= 0 && d <= 45;
    var avg = t.avg_pct != null ? sftFmt(t.avg_pct, 2) + '%' + (t.usd != null ? ' · $' + Math.round(t.usd).toLocaleString() : '') :
      sftFmt(t.avg_chg, 2) + ' ' + u + ' · $' + Math.round(t.usd).toLocaleString();
    var worst = t.worst_pct != null ? sftFmt(t.worst_pct, 1) + '%' : sftFmt(t.worst_chg, 2) + ' ' + u;
    var l5 = (t.last5 || []).map(function (x) { return '<span style="' + sftCol(x, t.avg_pct != null ? 5 : Math.abs(t.avg_chg) * 2 || 1) + '">' + sftFmt(x, t.avg_pct != null ? 1 : 2) + '</span>'; }).join('');
    h += '<tr' + (soon ? ' class="soon"' : '') + '><td>' + t.market + '</td><td class="l">' + t.what + (t.contract ? ' <span class="mu">(' + t.contract + ')</span>' : '') +
      (soon ? '<span class="tag">in ' + d + 'd</span>' : '') + '</td><td>' + t.next_entry + ' → ' + t.next_exit + '</td><td><b>' + t.hit + '%</b></td><td>' + (t.hit_last10 == null ? '–' : t.hit_last10 + '%') +
      '</td><td>' + avg + '</td><td class="dn">' + worst + '</td><td class="l5">' + l5 + '</td><td>' + t.n + '</td></tr>';
  });
  document.getElementById('sftTrades').innerHTML = h + '</tbody>';
}

function sftHeat() {
  var mk = SFT.D.markets[SFT.mk], H = mk.contract_heat, key = SFT.hm;
  var h = '<thead><tr><th>Contract</th>' + SFT_MON.map(function (m) { return '<th>' + m + '</th>'; }).join('') + '</tr></thead><tbody>';
  Object.keys(H).forEach(function (code) {
    var row = H[code], name = mk.cycle[Object.keys(H).indexOf(code)];
    h += '<tr><td class="rl">' + name + '</td>';
    SFT_MON.forEach(function (m, i) {
      var c = row[m];
      if (!c) { h += '<td class="mu">·</td>'; return; }
      var v = key === 'avg' ? c.avg : c.hit - 50, txt = key === 'avg' ? sftFmt(c.avg, 1) + '%' : c.hit + '%';
      h += '<td' + (c.back === 1 ? ' class="dlv"' : '') + ' style="' + sftCol(v, key === 'avg' ? 3 : 25) + '" title="' + name + ' in ' + m + ': avg ' + sftFmt(c.avg, 2) + '%, median ' + sftFmt(c.med, 2) + '%, up ' + c.hit + '% of ' + c.n + ' years">' + txt + '<small>' + (key === 'avg' ? c.hit + '% up' : sftFmt(c.avg, 1) + '%') + '</small></td>';
    });
    h += '</tr>';
  });
  document.getElementById('sftHm').innerHTML = h + '</tbody>';
}

function sftSpread() {
  var mk = SFT.D.markets[SFT.mk], S = mk.spread_heat, key = SFT.sp, u = mk.unit;
  var vals = []; ['s1', 's2', 's3'].forEach(function (s) { SFT_MON.forEach(function (m) { if (S[s][m]) vals.push(Math.abs(S[s][m].avg)); }); });
  vals.sort(function (a, b) { return a - b; }); var sc = vals[Math.floor(vals.length * 0.8)] || 1;
  var h = '<thead><tr><th>Spread</th>' + SFT_MON.map(function (m) { return '<th>' + m + '</th>'; }).join('') + '</tr></thead><tbody>';
  [['s1', 'Front – 2nd'], ['s2', '2nd – 3rd'], ['s3', '3rd – 4th']].forEach(function (r) {
    h += '<tr><td class="rl">' + r[1] + '</td>';
    SFT_MON.forEach(function (m) {
      var c = S[r[0]][m];
      if (!c) { h += '<td class="mu">·</td>'; return; }
      var v = key === 'avg' ? c.avg : c.hit - 50, txt = key === 'avg' ? sftFmt(c.avg, 2) : c.hit + '%';
      h += '<td style="' + sftCol(v, key === 'avg' ? sc : 25) + '" title="' + c.pair + ' in ' + m + ': avg ' + sftFmt(c.avg, 3) + ' ' + u + ', front gained ' + c.hit + '% of ' + c.n + ' years">' + txt + '<small>' + c.pair + '</small></td>';
    });
    h += '</tr>';
  });
  document.getElementById('sftSp').innerHTML = h + '</tbody>';
}

function sftGrid() {
  var mk = SFT.D.markets[SFT.mk], G = mk.front_grid, A = mk.front_avg;
  var yrs = Object.keys(G).map(Number).sort(function (a, b) { return b - a; });
  var h = '<thead><tr><th>Year</th>' + SFT_MON.map(function (m) { return '<th>' + m + '</th>'; }).join('') + '<th>Year</th></tr></thead><tbody>';
  yrs.forEach(function (y) {
    var tot = 1, any = false;
    h += '<tr><td>' + y + '</td>';
    for (var i = 1; i <= 12; i++) {
      var v = G[y][i]; if (v != null) { tot *= 1 + v / 100; any = true; }
      h += '<td style="' + sftCol(v, 10) + '">' + (v == null ? '' : sftFmt(v, 1)) + '</td>';
    }
    var ty = any ? (tot - 1) * 100 : null;
    h += '<td style="' + sftCol(ty, 30) + '"><b>' + (ty == null ? '' : sftFmt(ty, 0) + '%') + '</b></td></tr>';
  });
  h += '<tr class="ft"><td>Average</td>' + SFT_MON.map(function (m) { var c = A[m]; return '<td style="' + sftCol(c && c.avg, 3) + '">' + (c ? sftFmt(c.avg, 1) : '') + '</td>'; }).join('') + '<td></td></tr>';
  h += '<tr class="ft"><td>% up</td>' + SFT_MON.map(function (m) { var c = A[m]; return '<td style="' + sftCol(c && c.hit - 50, 25) + '">' + (c ? c.hit + '%' : '') + '</td>'; }).join('') + '<td></td></tr>';
  document.getElementById('sftGrid').innerHTML = h + '</tbody>';
}

function sftFnd() {
  var mk = SFT.D.markets[SFT.mk], L = mk.fnd_switch || [];
  var h = '<thead><tr><th>Buy</th><th>Days before first notice of</th><th>Hold</th><th>% of years up</th><th>Average</th><th>Median</th><th>Average $/lot</th><th>Worst</th><th>Last 5 years</th><th>Years</th></tr></thead><tbody>';
  L.forEach(function (r) {
    h += '<tr><td><b>' + r.contract + '</b></td><td>5 · ' + r.prev + '</td><td>' + r.hold + ' days</td><td style="' + sftCol(r.hit - 50, 25) + '"><b>' + r.hit + '%</b></td><td class="' + (r.avg >= 0 ? 'up' : 'dn') + '">' + sftFmt(r.avg, 2) + '%</td><td>' + sftFmt(r.med, 2) + '%</td><td class="' + (r.usd >= 0 ? 'up' : 'dn') + '">' + (r.usd >= 0 ? '+' : '−') + '$' + Math.abs(r.usd).toLocaleString() + '</td><td class="dn">' + sftFmt(r.worst, 1) + '%</td><td class="l5">' +
      r.last5.map(function (x) { return '<span style="' + sftCol(x, 6) + '">' + sftFmt(x, 1) + '</span>'; }).join('') + '</td><td>' + r.n + '</td></tr>';
  });
  document.getElementById('sftFnd').innerHTML = h + '</tbody>';
}

function sftSeas() {
  var L = SFT.D.seasonal.filter(function (s) { return s.root === SFT.mk; });
  if (!L.length) return;
  if (!SFT.seas || !L.some(function (s) { return s.key === SFT.seas; })) SFT.seas = L[0].key;
  sftChips('#sftSeasChips', L.map(function (s) { return [s.key, (s.kind === 'px' ? '' : 'Spread ') + s.label]; }), SFT.seas, function (k) { SFT.seas = k; sftSeas(); });
  var u = SFT.D.markets[SFT.mk].unit, f2 = function (v) { return v == null ? '–' : v.toFixed(2); };
  var h = '<thead><tr><th>Series</th><th>First notice</th><th>Now</th><th>Weeks to first notice</th><th>Percentile, same week</th><th>Seasons</th></tr></thead><tbody>';
  L.forEach(function (s) {
    var p = s.pct_same_time, cls = p == null ? '' : (p >= 80 || p <= 20) ? ' style="font-weight:700;color:#2a5298"' : '';
    h += '<tr><td>' + (s.kind === 'px' ? '' : 'Spread ') + s.label + '</td><td>' + s.fnd + '</td><td><b>' + f2(s.now) + '</b></td><td>' + (s.wk_now == null ? '–' : s.wk_now) + '</td><td' + cls + '>' + (p == null ? '–' : p.toFixed(0)) + '</td><td>' + s.n_years + '</td></tr>';
  });
  document.getElementById('sftPct').innerHTML = h + '</tbody>';
  var x = L.filter(function (s) { return s.key === SFT.seas; })[0], fnd = new Date(x.fnd + 'T00:00:00Z');
  var lab = function (w) { var d = new Date(fnd); d.setUTCDate(d.getUTCDate() - 7 * w); return d.toLocaleDateString('en-US', {month: 'short', day: 'numeric', timeZone: 'UTC'}); };
  var P = function (a) { return (a || []).map(function (p) { return {x: p[0], y: p[1]}; }); };
  if (SFT.chart) SFT.chart.destroy();
  var band = 'rgba(138,137,132,.16)', band2 = 'rgba(138,137,132,.28)';
  SFT.chart = new Chart(document.getElementById('sftSeas'), {type: 'line', data: {datasets: [
    {label: '90th', data: P(x.bands[90]), borderWidth: 0, pointRadius: 0, fill: false},
    {label: '10–90th', data: P(x.bands[10]), borderWidth: 0, pointRadius: 0, backgroundColor: band, fill: '-1'},
    {label: '75th', data: P(x.bands[75]), borderWidth: 0, pointRadius: 0, fill: false},
    {label: '25–75th', data: P(x.bands[25]), borderWidth: 0, pointRadius: 0, backgroundColor: band2, fill: '-1'},
    {label: 'Median', data: P(x.bands[50]), borderColor: '#8a8984', borderWidth: 1, pointRadius: 0, borderDash: [2, 3]},
    {label: '5-yr avg', data: P(x.avg5), borderColor: '#8a8984', borderWidth: 1.5, pointRadius: 0, borderDash: [5, 4]},
    {label: 'Last year', data: P(x.last_year), borderColor: '#eb6834', borderWidth: 1.8, pointRadius: 0},
    {label: x.label, data: P(x.current), borderColor: '#2a78d6', borderWidth: 2.8, pointRadius: 0}]},
    options: {responsive: true, maintainAspectRatio: false, animation: false, interaction: {mode: 'index', intersect: false},
      plugins: {legend: {display: false}, zoom: false, tooltip: {filter: function (i) { return ['90th', '75th'].indexOf(i.dataset.label) < 0; },
        callbacks: {title: function (i) { return i[0].parsed.x + ' weeks to first notice (~' + lab(i[0].parsed.x) + ')'; }, label: function (c) { return c.dataset.label + ': ' + c.parsed.y.toFixed(2) + ' ' + u; }}}},
      scales: {x: {type: 'linear', reverse: true, min: 0, max: 52, grid: {display: false}, ticks: {callback: function (v) { return lab(v); }, maxTicksLimit: 9}},
               y: {grid: {color: '#eeede9'}, ticks: {callback: function (v) { return v + (u === '$/t' ? '' : '¢'); }}}}}});
}
