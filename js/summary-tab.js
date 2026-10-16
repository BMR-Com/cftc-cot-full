/* ===========================================================
   SUMMARY TAB — Desk Brief, Positioning Monitor, league tables, range table
   All cross-market numbers come from the pre-computed weekly snapshot
   (data/web/snapshot.json, cached in the browser), so this tab renders
   instantly and makes no CFTC calls. Legacy live-API fallback kept for the
   case where the snapshot file is missing.
   =========================================================== */

var _deskA = null, _deskSort = { k: 'score', dir: -1 }, _snap = null;

function initSummaryTab() {
  generateSummary();
  document.querySelectorAll('#monTable th[data-k]').forEach(function (th) {
    th.onclick = function () {
      var k = th.getAttribute('data-k');
      if (k === 'spark' || k === 'read') return;
      _deskSort = { k: k, dir: (_deskSort.k === k ? -_deskSort.dir : (k === 'name' || k === 'drv' ? 1 : -1)) };
      document.querySelectorAll('#monTable th').forEach(function (h) { h.classList.remove('sorted', 'asc'); });
      th.classList.add('sorted'); if (_deskSort.dir > 0) th.classList.add('asc');
      renderMonitor();
    };
  });
}

/* Entry point (also called by other code). Idempotent and cache-backed. */
function generateSummary() {
  var sub = document.getElementById('briefSub');
  COTStore.snapshot().then(function (snap) {
    _snap = snap;
    renderDesk();
  }).catch(function (e) {
    console.warn('[Summary] snapshot unavailable, using live CFTC API:', e && e.message);
    if (sub) sub.textContent = 'Pre-computed data not found — falling back to live CFTC API (slower). Run the "Weekly COT Data Update" workflow to enable the fast path.';
    legacyGenerateSummary();
  });
}

function deskOpts() {
  var w = document.getElementById('dkWin'), c = document.getElementById('dkCrop');
  return { win: w ? w.value : 'y3', crop: c ? c.value : 'all' };
}

function renderDesk() {
  if (!_snap) return;
  var o = deskOpts();
  _deskA = COTInsights.analyze(_snap, o);
  var a = _deskA, W = COTInsights.WIN_LBL[o.win];
  var stale = (_snap.commodities || []).filter(function (c) { return c.stale; }).map(function (c) { return c.name; });
  document.getElementById('briefSub').innerHTML = 'CFTC Disaggregated F&amp;O combined · positions as of <b>' + fmtDate(a.date) + '</b> · look-back ' + W +
    (o.crop !== 'all' ? ' · ' + o.crop + '-crop view for grains/softs/hogs' : '') +
    (stale.length ? ' · excluded (stale): ' + stale.join(', ') : '') +
    ' · not reported by CFTC: ' + BCOM_NOT_REPORTED.join(', ');

  /* narrative */
  document.getElementById('briefBody').innerHTML = COTInsights.brief(a).map(function (l) {
    return '<div class="bh">' + l.h + '</div><div>' + l.t + '</div>';
  }).join('');

  /* setup cards */
  function card(title, tone, rows, val) {
    var body = rows.length ? rows.map(function (r) {
      return '<div class="setup-item" onclick="openInCot(\'' + r.ticker + '\')" title="' + r.read.replace(/"/g, '&quot;') + '"><span>' + r.name + '</span><span class="sv">' + val(r) + '</span></div>';
    }).join('') : '<div class="empty">None this week</div>';
    return '<div class="setup-card ' + tone + '"><h4>' + title + '</h4>' + body + '</div>';
  }
  var sc = function (r) { return (r.score > 0 ? '+' : '') + r.score; };
  document.getElementById('setupCards').innerHTML =
    card('&#x2705; Contrarian long setups', 'bull', a.longSetups, sc) +
    card('&#x274C; Contrarian short setups', 'bear', a.shortSetups, sc) +
    card('&#x1F525; Short-squeeze fuel', 'warn', a.squeeze, function (r) { return 'shorts ' + COTInsights.ord(r.mm.p.S[a.win]) + ' pct'; }) +
    card('&#x26A0;&#xFE0F; Long-liquidation risk', 'warn', a.liqRisk, function (r) { return 'longs ' + COTInsights.ord(r.mm.p.L[a.win]) + ' pct'; });

  renderSectors();
  renderMonitor();
  renderLeagueAndRanges();
  /* AI tab reads scData for context when present */
  try { scData = COTInsights.scatterRows(_snap, 'f', 'all'); } catch (e) { }
}

function renderSectors() {
  var el = document.getElementById('secStrip'); if (!el || !_deskA) return;
  el.innerHTML = _deskA.sectors.slice().sort(function (x, y) { return y.cot - x.cot; }).map(function (s) {
    var c = s.cot, bg = c >= 75 ? 'rgba(192,57,43,.12)' : c <= 25 ? 'rgba(26,140,78,.12)' : '#f7f9fb';
    return '<div class="sec-card" style="background:' + bg + '" title="' + s.names.join(', ') + '"><div class="sn">' + s.sector + '</div>' +
      '<div class="sv">' + Math.round(c) + '</div><div class="sm">avg COT idx · ' + s.buy + '↑ ' + s.sell + '↓ · Δnet ' + (s.dnp >= 0 ? '+' : '') + s.dnp.toFixed(1) + ' pts OI</div></div>';
  }).join('');
}

function spark(arr, w, h) {
  w = w || 90; h = h || 22;
  var a = (arr || []).filter(function (v) { return v != null; }); if (a.length < 2) return '';
  var mn = Math.min.apply(null, a), mx = Math.max.apply(null, a), rg = (mx - mn) || 1;
  var pts = a.map(function (v, i) { return (i / (a.length - 1) * w).toFixed(1) + ',' + (h - (v - mn) / rg * (h - 2) - 1).toFixed(1); }).join(' ');
  var zero = (mn < 0 && mx > 0) ? '<line x1="0" x2="' + w + '" y1="' + (h - (0 - mn) / rg * (h - 2) - 1).toFixed(1) + '" y2="' + (h - (0 - mn) / rg * (h - 2) - 1).toFixed(1) + '" stroke="#bbb" stroke-dasharray="2,2"/>' : '';
  var last = a[a.length - 1], col = last >= 0 ? '#1a8c4e' : '#c0392b';
  return '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">' + zero + '<polyline fill="none" stroke="' + col + '" stroke-width="1.5" points="' + pts + '"/></svg>';
}

function renderMonitor() {
  var tb = document.getElementById('monBody'); if (!tb || !_deskA) return;
  var k = _deskSort.k, d = _deskSort.dir;
  var val = function (r) {
    switch (k) {
      case 'name': return r.name; case 'drv': return r.drv.main; case 'N': return r.mm.N; case 'dN': return r.mm.dN;
      default: return r[k] == null ? -1e9 : r[k];
    }
  };
  var rows = _deskA.rows.slice().sort(function (a, b) { var x = val(a), y = val(b); return typeof x === 'string' ? d * x.localeCompare(y) : d * (x - y); });
  var K = COTInsights.k, SK = COTInsights.sk, ORD = COTInsights.ord;
  tb.innerHTML = rows.map(function (r) {
    var f = '';
    r.flags.forEach(function (fl) { f += fl.key === 'squeeze' ? '<span class="flag" title="' + fl.txt + '">&#x1F525;</span>' : fl.key === 'liq' ? '<span class="flag" title="' + fl.txt + '">&#x26A0;&#xFE0F;</span>' : fl.key === 'fast' ? '<span class="flag" title="' + fl.txt + '">&#x23E9;</span>' : ''; });
    if (r.comm) f += '<span class="flag" title="' + r.comm.txt + '">&#x2195;&#xFE0F;</span>';
    var sw = Math.abs(r.score) / 2, sl = r.score >= 0 ? 50 : 50 - sw, scol = r.score >= 0 ? '#1a8c4e' : '#c0392b';
    return '<tr>' +
      '<td><span class="mk" onclick="openInCot(\'' + r.ticker + '\')">' + r.name + '</span><span class="tk">' + r.ticker + (r.crop !== 'all' ? ' · ' + r.crop : '') + '</span> ' + f + '</td>' +
      '<td><span class="badge b-' + r.reg.tone + '">' + r.reg.lbl + '</span></td>' +
      '<td class="num ' + (r.mm.N >= 0 ? 'pos' : 'neg') + '">' + K(r.mm.N) + '</td>' +
      '<td class="num ' + (r.mm.dN >= 0 ? 'pos' : 'neg') + '">' + SK(r.mm.dN) + '</td>' +
      '<td class="num ' + (r.z >= 0 ? 'pos' : 'neg') + '" title="' + r.size + '">' + (r.z >= 0 ? '+' : '−') + Math.abs(r.z).toFixed(1) + '</td>' +
      '<td title="' + r.drv.detail + '">' + r.drv.main + (Math.abs(r.mm.streak) >= 3 ? ' <small>(' + Math.abs(r.mm.streak) + 'w)</small>' : '') + '</td>' +
      '<td>' + spark(r.mm.spark) + '</td>' +
      '<td class="num"><span class="cotbar"><i style="left:' + Math.max(0, Math.min(100, r.cot)) + '%"></i></span>' + Math.round(r.cot) + '</td>' +
      '<td class="num">' + ORD(r.pN) + '</td>' +
      '<td class="num">' + (r.pmP == null ? '–' : ORD(r.pmP)) + '</td>' +
      '<td class="num"><span class="scorebar"><b style="left:' + sl + '%;width:' + sw + '%;background:' + scol + '"></b></span>' + (r.score > 0 ? '+' : '') + r.score + '</td>' +
      '<td class="read">' + r.read + '</td></tr>';
  }).join('');
}

/* League tables (exec) + range table, from the same snapshot */
function renderLeagueAndRanges() {
  var o = deskOpts(), w = o.win;
  var ex = COTInsights.scatterRows(_snap, w, o.crop);
  document.getElementById('execSec').style.display = 'block';
  fillPctTables('', ex);
  var t = document.querySelector('#execSec .exec-title');
  if (t) t.innerHTML = '&#x1F4CA; Percentile League Tables — Managed Money (' + COTInsights.WIN_LBL[w] + ')';

  document.getElementById('sumSec').style.display = 'block';
  sumData = snapToSumRows(_snap, o.crop);
  renderSum('sumBody', sumData);
}

/* Range-table rows (Net / Net%OI / Long / Long%OI / Short / Short%OI, full history) */
function snapToSumRows(snap, crop) {
  var out = [];
  (snap.commodities || []).forEach(function (cm) {
    if (cm.stale) return;
    var v = (crop && crop !== 'all' && cm.v[crop]) ? cm.v[crop] : cm.v.all; if (!v) return;
    var nm = cm.name + (crop && crop !== 'all' && cm.v[crop] ? ' (' + crop + ')' : '');
    CATS.forEach(function (cat) {
      var c = v.cats[cat]; if (!c) return;
      out.push({ comm: nm, cat: CAT_LBL[cat], catKey: cat, sec: cm.sector,
        net: c.N, netMn: c.r.N[0], netMx: c.r.N[1], nPct: c.np, nPctMn: c.r.np[0], nPctMx: c.r.np[1],
        lon: c.L, lonMn: c.r.L[0], lonMx: c.r.L[1], lPct: c.lp, lPctMn: c.r.lp[0], lPctMx: c.r.lp[1],
        sho: c.S, shoMn: c.r.S[0], shoMx: c.r.S[1], sPct: c.sp, sPctMn: c.r.sp[0], sPctMx: c.r.sp[1] });
    });
  });
  return out;
}

/* Kept for compatibility (scatter-tab used to call this to fill the exec section) */
function popExec(data) { document.getElementById('execSec').style.display = 'block'; fillPctTables('', data); }

/* Jump from Summary to the full COT Analyzer for one market */
function openInCot(ticker) {
  var it = allBCOM.filter(function (b) { return b.ticker === ticker; })[0]; if (!it) return;
  switchTab('cot');
  var go = function () {
    var sel = document.getElementById('commoditySelect'); if (!sel) return setTimeout(go, 100);
    sel.value = it.api; if (typeof onCommChange === 'function') onCommChange();
    fetchData(); window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  go();
}

/* Plain-text brief for pasting into notes / client emails */
function copyBrief() {
  if (!_deskA) return;
  var a = _deskA, txt = 'COT DESK BRIEF — positions as of ' + a.date + ' (look-back ' + COTInsights.WIN_LBL[a.win] + ')\n\n';
  COTInsights.brief(a).forEach(function (l) { txt += l.h.toUpperCase() + ': ' + l.t + '\n\n'; });
  txt += 'MARKET READS\n';
  a.rows.slice().sort(function (x, y) { return y.score - x.score; }).forEach(function (r) { txt += '• ' + r.name + ' [' + (r.score > 0 ? '+' : '') + r.score + ']: ' + r.read + '\n'; });
  txt += '\nSource: CFTC Disaggregated COT, futures & options combined. Positioning read, not a price forecast.';
  var done = function () { var b = document.getElementById('copyBriefBtn'); if (b) { var t = b.innerHTML; b.innerHTML = '✓ Copied'; setTimeout(function () { b.innerHTML = t; }, 1500); } };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt).then(done, function () { fallbackCopy(txt); done(); });
  else { fallbackCopy(txt); done(); }
}
function fallbackCopy(t) { var ta = document.createElement('textarea'); ta.value = t; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); } catch (e) { } ta.remove(); }

/* ===========================================================
   LEGACY FALLBACK — live CFTC API (only if the snapshot is missing).
   One request per commodity (was one per commodity × category = 4× more).
   =========================================================== */
function legacyGenerateSummary() {
  showL(true, 'Generating summary (live CFTC)...'); document.getElementById('sumSec').style.display = 'block'; sumData = [];
  var ep = EP[document.getElementById('reportType') ? document.getElementById('reportType').value : 'combined'] || EP.combined;
  var list = liveBCOM(), done = 0; if (!list.length) { showL(false); return; }
  list.forEach(function (it) {
    fetchT(ep + "?$where=" + liveWhere(it.api) + " AND report_date_as_yyyy_mm_dd >= '2006-01-01'&$order=report_date_as_yyyy_mm_dd ASC&$limit=10000", 25000)
      .then(function (r) { return r.json(); }).then(function (data) {
        if (!data.length) return;
        CATS.forEach(function (cat) {
          var p = procData(data, cat); if (!p) return; var l = p.net.length - 1;
          var mn = function (a) { return Math.min.apply(null, a); }, mx = function (a) { return Math.max.apply(null, a); };
          sumData.push({ comm: it.name, cat: CAT_LBL[cat], catKey: cat, sec: it.sector, net: p.net[l], netMn: mn(p.net), netMx: mx(p.net), nPct: p.nPct[l], nPctMn: mn(p.nPct), nPctMx: mx(p.nPct), lon: p.long[l], lonMn: mn(p.long), lonMx: mx(p.long), lPct: p.lPct[l], lPctMn: mn(p.lPct), lPctMx: mx(p.lPct), sho: p.short[l], shoMn: mn(p.short), shoMx: mx(p.short), sPct: p.sPct[l], sPctMn: mn(p.sPct), sPctMx: mx(p.sPct) });
        });
      }).catch(function () { }).finally(function () { done++; if (done >= list.length) { renderSum('sumBody', sumData); showL(false); } });
  });
}
