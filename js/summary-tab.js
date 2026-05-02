/* ===========================================================
   SUMMARY TAB — Executive Summary + Market Summary
   Loaded dynamically by tab-switching.js
   =========================================================== */

function initSummaryTab() {
    // Check if we have cached data from today
    var cached = sessionStorage.getItem('cot_summary_cache');
    var cacheDate = sessionStorage.getItem('cot_summary_cache_date');
    var today = new Date().toISOString().split('T')[0];

    if(cached && cacheDate === today) {
        var data = JSON.parse(cached);
        sumData = data.sumData || [];
        scData = data.scData || [];
        if(sumData.length) renderSum('sumBody', sumData);
        if(scData.length) popExec(scData);
        console.log('[Summary Tab] Loaded from cache');
        return;
    }

    // Generate fresh data
    if(!sumData || !sumData.length) {
        generateSummary();
    }
    console.log('[Summary Tab] Initialized');
}

function cacheSummaryData() {
    try {
        var cache = { sumData: sumData, scData: scData };
        sessionStorage.setItem('cot_summary_cache', JSON.stringify(cache));
        sessionStorage.setItem('cot_summary_cache_date', new Date().toISOString().split('T')[0]);
    } catch(e) { console.warn('Failed to cache summary:', e); }
}

/* ===========================================================
   EXEC SUMMARY (all BCOM)
   =========================================================== */
function popExec(data){
  document.getElementById('execSec').style.display='block';
  var gs=data.slice().sort(function(a,b){return b.mSP-a.mSP;});
  var ns=data.slice().sort(function(a,b){return a.mNP-b.mNP;});
  var gl=data.slice().sort(function(a,b){return a.mLP-b.mLP;});
  var gso=data.slice().sort(function(a,b){return b.mSPoi-a.mSPoi;});
  var nso=data.slice().sort(function(a,b){return a.mNPoi-b.mNPoi;});
  var glo=data.slice().sort(function(a,b){return a.mLPoi-b.mLPoi;});
  function pColor(p,r,g,b){var a=0.08+0.52*(p/100);return 'rgba('+r+','+g+','+b+','+a.toFixed(2)+')';}
  function fill(id,arr,field,r,g,b,inv){var tb=document.getElementById(id);if(!tb)return;tb.innerHTML='';arr.forEach(function(it){var v=inv?100-it[field]:it[field];v=Math.max(0,Math.min(100,v));var tr=document.createElement('tr');tr.innerHTML='<td>'+it.comm+'</td><td style="background:'+pColor(v,r,g,b)+';color:#1a1a1a;">'+v.toFixed(1)+'%</td>';tb.appendChild(tr);});}
  fill('t_gs',gs,'mSP',231,76,60,false);fill('t_ns',ns,'mNP',243,156,18,true);fill('t_gl',gl,'mLP',39,174,96,false);fill('t_gso',gso,'mSPoi',169,50,38,false);fill('t_nso',nso,'mNPoi',183,149,11,true);fill('t_glo',glo,'mLPoi',30,132,73,false);
  var eS=[],eL=[],cS=[],cL=[],longC=[],shortC=[];
  data.forEach(function(d){if(d.mSP>=80)eS.push(d.comm);if(d.mLP>=80)eL.push(d.comm);if(d.mNP<=15)cS.push(d.comm);if(d.mNP>=85)cL.push(d.comm);if(d.mSP>=75&&d.mNP<=25)longC.push(d.comm);if(d.mLP>=75&&d.mNP>=75)shortC.push(d.comm);});
  var txt='<strong>BCOM Managed Money Positioning Analysis (Historical Percentile Since 2006):</strong><br>';
  txt+='Positioning extremes are powerful contrarian signals. Crowded shorts fuel covering rallies; crowded longs create liquidation cascades.<br><br>';
  if(eS.length)txt+='<strong>&#x1F534; Extreme Gross Short (&gt;80th %ile):</strong> '+eS.join(', ')+' — Contrarian LONG bias, limited room to add shorts.<br>';
  if(cS.length)txt+='<strong>&#x1F7E0; Extreme Net Short (&lt;15th %ile):</strong> '+cS.join(', ')+' — Maximum bearishness, short-covering risk elevated.<br>';
  if(eL.length)txt+='<strong>&#x1F7E2; Extreme Gross Long (&gt;80th %ile):</strong> '+eL.join(', ')+' — Crowded longs, liquidation risk.<br>';
  if(cL.length)txt+='<strong>&#x1F535; Extreme Net Long (&gt;85th %ile):</strong> '+cL.join(', ')+' — Contrarian SHORT bias.<br>';
  if(!eS.length&&!eL.length&&!cS.length&&!cL.length)txt+='No commodities at extreme positioning levels currently.<br>';
  txt+='<br>';
  if(longC.length)txt+='<strong>&#x2705; Long Candidates (high short + low net):</strong> '+longC.join(', ')+'<br>';
  if(shortC.length)txt+='<strong>&#x274C; Short Candidates (high long + high net):</strong> '+shortC.join(', ')+'<br>';
  document.getElementById('execText').innerHTML=txt;
}

/* ===========================================================
   BCOM MARKET SUMMARY
   =========================================================== */
function generateSummary(){
  showL(true,'Generating summary...');document.getElementById('sumSec').style.display='block';sumData=[];
  var ep=EP[document.getElementById('reportType').value],tot=allBCOM.length*CATS.length,done=0;
  if(!allBCOM.length){showL(false);return;}
  allBCOM.forEach(function(it){CATS.forEach(function(cat){
    fetchT(ep+"?$where=market_and_exchange_names='"+it.api.replace(/'/g,"''")+"' AND report_date_as_yyyy_mm_dd >= '2006-01-01'&$order=report_date_as_yyyy_mm_dd ASC&$limit=10000",20000)
    .then(function(r){return r.json();}).then(function(data){
      if(!data.length)return;var p=procData(data,cat);if(!p)return;var l=p.net.length-1;
      sumData.push({comm:it.name,cat:CAT_LBL[cat],catKey:cat,sec:it.sector,net:p.net[l],netMn:Math.min.apply(null,p.net),netMx:Math.max.apply(null,p.net),nPct:p.nPct[l],nPctMn:Math.min.apply(null,p.nPct),nPctMx:Math.max.apply(null,p.nPct),lon:p.long[l],lonMn:Math.min.apply(null,p.long),lonMx:Math.max.apply(null,p.long),lPct:p.lPct[l],lPctMn:Math.min.apply(null,p.lPct),lPctMx:Math.max.apply(null,p.lPct),sho:p.short[l],shoMn:Math.min.apply(null,p.short),shoMx:Math.max.apply(null,p.short),sPct:p.sPct[l],sPctMn:Math.min.apply(null,p.sPct),sPctMx:Math.max.apply(null,p.sPct)});
    }).catch(function(){}).finally(function(){done++;if(done>=tot){renderSum('sumBody',sumData);popExec(scData);cacheSummaryData();showL(false);}});
  });});
}

function mmBar(cur,mn,mx,isN){
  if(mn===mx)return '';
  var p=((cur-mn)/(mx-mn))*100,safe=Math.max(2,Math.min(98,p));
  var cl,grad;
  if(isN){
    if(cur>=0){cl='#1a8c4e';grad='linear-gradient(90deg,#d5f5e3 0%,#1a8c4e 100%)';}
    else{cl='#c0392b';grad='linear-gradient(90deg,#fadbd8 0%,#c0392b 100%)';}
  } else {cl='#2a5298';grad='linear-gradient(90deg,#d6eaf8 0%,#2a5298 100%)';}
  return '<div class="mmbar-wrap">'+
    '<div class="mmbar-cont">'+
      '<div style="position:absolute;left:0;top:0;height:100%;width:'+safe+'%;background:'+grad+';border-radius:8px;opacity:0.85;"></div>'+
      '<div class="mmbar-dot" style="left:'+safe+'%;background:'+cl+';border:2px solid white;box-shadow:0 0 3px rgba(0,0,0,0.4);"></div>'+
    '</div>'+
    '<div class="mmbar-lbl"><span>'+ff(mn)+'</span><span>'+ff(mx)+'</span></div>'+
  '</div>';
}

function renderSum(tbodyId,data){
  var tb=document.getElementById(tbodyId);if(!tb)return;tb.innerHTML='';
  if(!data.length){tb.innerHTML='<tr><td colspan="14" style="text-align:center;padding:20px;">No data</td></tr>';return;}
  data.sort(function(a,b){if(a.sec!==b.sec)return a.sec.localeCompare(b.sec);if(a.comm!==b.comm)return a.comm.localeCompare(b.comm);return a.cat.localeCompare(b.cat);});
  var cs='',cc='';
  data.forEach(function(it){
    if(it.sec!==cs){cs=it.sec;var hr=document.createElement('tr');hr.innerHTML='<td colspan="14" class="section-header">'+cs+'</td>';tb.appendChild(hr);}
    var sh=it.comm!==cc;cc=it.comm;var r=document.createElement('tr');
    r.innerHTML='<td class="commodity-name">'+(sh?it.comm:'')+'</td><td style="font-weight:600;color:'+(CAT_COL[it.catKey]||'#333')+'">'+it.cat+'</td>'+
    '<td>'+mmBar(it.net,it.netMn,it.netMx,true)+'</td><td class="data-cell '+(it.net>0?'positive-value':it.net<0?'negative-value':'')+'">'+it.net.toLocaleString()+'</td>'+
    '<td>'+mmBar(it.nPct,it.nPctMn,it.nPctMx,true)+'</td><td class="data-cell '+(it.nPct>0?'positive-value':it.nPct<0?'negative-value':'')+'">'+it.nPct.toFixed(1)+'%</td>'+
    '<td>'+mmBar(it.lon,it.lonMn,it.lonMx,false)+'</td><td class="data-cell positive-value">'+it.lon.toLocaleString()+'</td>'+
    '<td>'+mmBar(it.lPct,it.lPctMn,it.lPctMx,false)+'</td><td class="data-cell positive-value">'+it.lPct.toFixed(1)+'%</td>'+
    '<td>'+mmBar(it.sho,it.shoMn,it.shoMx,false)+'</td><td class="data-cell negative-value">'+it.sho.toLocaleString()+'</td>'+
    '<td>'+mmBar(it.sPct,it.sPctMn,it.sPctMx,false)+'</td><td class="data-cell negative-value">'+it.sPct.toFixed(1)+'%</td>';
    tb.appendChild(r);
  });
}

