/* ===========================================================
   CONSTANTS
   =========================================================== */
var EP={futures:'https://publicreporting.cftc.gov/resource/72hh-3qpy.json',combined:'https://publicreporting.cftc.gov/resource/kh3c-gbw2.json'};
var BCOM={'Energy (29.44%)':[{name:'Brent Crude Oil',ticker:'CO',cftc:'BRENT CRUDE OIL LAST DAY - NEW YORK MERCANTILE EXCHANGE'},{name:'Natural Gas',ticker:'NG',cftc:'NATURAL GAS - NEW YORK MERCANTILE EXCHANGE'},{name:'WTI Crude Oil',ticker:'CL',cftc:'CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE'},{name:'Low Sulphur Gas Oil',ticker:'QS',cftc:'GAS OIL LOW SULPHUR - ICE FUTURES EUROPE'},{name:'ULS Diesel',ticker:'HO',cftc:'NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE'},{name:'RBOB Gasoline',ticker:'XB',cftc:'GASOLINE, RBOB - NEW YORK MERCANTILE EXCHANGE'}],'Grains (21.15%)':[{name:'Corn',ticker:'C',cftc:'CORN - CHICAGO BOARD OF TRADE'},{name:'Soybeans',ticker:'S',cftc:'SOYBEANS - CHICAGO BOARD OF TRADE'},{name:'Soybean Meal',ticker:'SM',cftc:'SOYBEAN MEAL - CHICAGO BOARD OF TRADE'},{name:'Soybean Oil',ticker:'BO',cftc:'SOYBEAN OIL - CHICAGO BOARD OF TRADE'},{name:'Wheat',ticker:'W',cftc:'WHEAT-SRW - CHICAGO BOARD OF TRADE'},{name:'HRW Wheat',ticker:'KW',cftc:'WHEAT-HRW - CHICAGO BOARD OF TRADE'}],'Industrial Metals (15.76%)':[{name:'Copper',ticker:'HG',cftc:'COPPER- #1 - COMMODITY EXCHANGE INC.'},{name:'Aluminum',ticker:'LA',cftc:'ALUMINUM - COMMODITY EXCHANGE INC.'},{name:'Zinc',ticker:'LX',cftc:'ZINC - COMMODITY EXCHANGE INC.'},{name:'Nickel',ticker:'LN',cftc:'NICKEL - COMMODITY EXCHANGE INC.'},{name:'Lead',ticker:'LL',cftc:'LEAD - COMMODITY EXCHANGE INC.'}],'Precious Metals (18.84%)':[{name:'Gold',ticker:'GC',cftc:'GOLD - COMMODITY EXCHANGE INC.'},{name:'Silver',ticker:'SI',cftc:'SILVER - COMMODITY EXCHANGE INC.'}],'Softs (9.12%)':[{name:'Sugar',ticker:'SB',cftc:'SUGAR NO. 11 - ICE FUTURES U.S.'},{name:'Coffee',ticker:'KC',cftc:'COFFEE C - ICE FUTURES U.S.'},{name:'Cocoa',ticker:'CC',cftc:'COCOA - ICE FUTURES U.S.'},{name:'Cotton',ticker:'CT',cftc:'COTTON NO. 2 - ICE FUTURES U.S.'}],'Livestock (5.64%)':[{name:'Live Cattle',ticker:'LC',cftc:'LIVE CATTLE - CHICAGO MERCANTILE EXCHANGE'},{name:'Lean Hogs',ticker:'LH',cftc:'LEAN HOGS - CHICAGO MERCANTILE EXCHANGE'}]};
var CROP_COMM={Corn:1,Soybeans:1,'Soybean Meal':1,'Soybean Oil':1,Wheat:1,'HRW Wheat':1,Coffee:1,Cocoa:1,Cotton:1,'Lean Hogs':1};
var CATS=['managed_money','swap_dealers','prod_merc','other_rept'];
var CROP_KW_LIST=['CORN','SOYBEAN','WHEAT','COTTON','COFFEE','COCOA','HOG'];
function isCrop(n){return CROP_KW_LIST.some(function(k){return (n||'').toUpperCase().indexOf(k)!==-1;});}
var CAT_LBL={managed_money:'Managed Money',swap_dealers:'Swap Dealers',prod_merc:'Prod/Merchant',other_rept:'Other Rept'};
var CAT_COL={managed_money:'#2a5298',swap_dealers:'#1a8c4e',prod_merc:'#d4880f',other_rept:'#8e44ad'};
var CAT_CLS={managed_money:'mm',swap_dealers:'sd',prod_merc:'pm',other_rept:'or'};

/* ── EXACT Socrata API field names (confirmed from API foundry).
   Fields are INCONSISTENT across crop types — hardcoded exactly as returned.
   All:   PM/OR/MM-spread have NO _all suffix; SD/MM-long/short have _all
   Old:   PM/OR/MM-spread/_OR-spread use _1; SD/MM-long/short use _old
   Other: PM/OR/MM-spread/_OR-spread use _2; SD/MM-long/short use _other  ── */
var TF={
  managed_money:{
    long:  ['m_money_positions_long_all'],
    short: ['m_money_positions_short_all'],
    spread:['m_money_positions_spread'],       /* no _all suffix */
    tl:    ['traders_m_money_long_all'],
    ts:    ['traders_m_money_short_all']
  },
  swap_dealers:{
    long:  ['swap_positions_long_all'],
    short: ['swap__positions_short_all'],      /* double underscore */
    spread:['swap__positions_spread_all'],     /* double underscore */
    tl:    ['traders_swap_long_all'],
    ts:    ['traders_swap_short_all']
  },
  prod_merc:{
    long:  ['prod_merc_positions_long'],       /* no _all suffix */
    short: ['prod_merc_positions_short'],      /* no _all suffix */
    spread:[],                                 /* PM has no spread */
    tl:    ['traders_prod_merc_long_all'],
    ts:    ['traders_prod_merc_short_all']
  },
  other_rept:{
    long:  ['other_rept_positions_long'],      /* no _all suffix */
    short: ['other_rept_positions_short'],     /* no _all suffix */
    spread:['other_rept_positions_spread'],    /* no _all suffix */
    tl:    ['traders_other_rept_long_all'],
    ts:    ['traders_other_rept_short_all']
  }
};

/* Crop-year field maps — exact per Socrata foundry */
var TF_OLD={
  managed_money:{
    long:  ['m_money_positions_long_old'],
    short: ['m_money_positions_short_old'],
    spread:['m_money_positions_spread_1'],     /* _1 */
    tl:    ['traders_m_money_long_old'],
    ts:    ['traders_m_money_short_old']
  },
  swap_dealers:{
    long:  ['swap_positions_long_old'],
    short: ['swap__positions_short_old'],      /* double underscore */
    spread:['swap__positions_spread_old'],     /* double underscore */
    tl:    ['traders_swap_long_old'],
    ts:    ['traders_swap_short_old']
  },
  prod_merc:{
    long:  ['prod_merc_positions_long_1'],     /* _1 */
    short: ['prod_merc_positions_short_1'],    /* _1 */
    spread:[],
    tl:    ['traders_prod_merc_long_old'],
    ts:    ['traders_prod_merc_short_old']
  },
  other_rept:{
    long:  ['other_rept_positions_long_1'],    /* _1 */
    short: ['other_rept_positions_short_1'],   /* _1 */
    spread:['other_rept_positions_spread_1'],  /* _1 */
    tl:    ['traders_other_rept_long_old'],
    ts:    ['traders_other_rept_short_old']
  }
};

var TF_OTHER={
  managed_money:{
    long:  ['m_money_positions_long_other'],
    short: ['m_money_positions_short_other'],
    spread:['m_money_positions_spread_2'],     /* _2 */
    tl:    ['traders_m_money_long_other'],
    ts:    ['traders_m_money_short_other']
  },
  swap_dealers:{
    long:  ['swap_positions_long_other'],
    short: ['swap__positions_short_other'],    /* double underscore */
    spread:['swap__positions_spread_other'],   /* double underscore */
    tl:    ['traders_swap_long_other'],
    ts:    ['traders_swap_short_other']
  },
  prod_merc:{
    long:  ['prod_merc_positions_long_2'],     /* _2 */
    short: ['prod_merc_positions_short_2'],    /* _2 */
    spread:[],
    tl:    ['traders_prod_merc_long_other'],
    ts:    ['traders_prod_merc_short_other']
  },
  other_rept:{
    long:  ['other_rept_positions_long_2'],    /* _2 */
    short: ['other_rept_positions_short_2'],   /* _2 */
    spread:['other_rept_positions_spread_2'],  /* _2 */
    tl:    ['traders_other_rept_long_other'],
    ts:    ['traders_other_rept_short_other']
  }
};

function getFM(cat,crop){
  if(!crop||crop==='all') return TF[cat]||TF.managed_money;
  if(crop==='old')        return TF_OLD[cat]||TF_OLD.managed_money;
  if(crop==='other')      return TF_OTHER[cat]||TF_OTHER.managed_money;
  return TF[cat]||TF.managed_money;
}

/* ===========================================================
   STATE
   =========================================================== */
var CD=null,ATD={},rawCache=null,cropInfo=null,apiList=[],allBCOM=[];
var dbgInfo={};
var sumData=[],scData=[],spData=[];
var seaCache={},seaYrs=new Set(),seaComms=new Set();
var agriRaw={};  /* apiName -> raw[] */
var agriSeaType='old',agriSeaComms=new Set(),agriSeaYrs=new Set();
var charts={};
var zPct={pos:100,cmp:100,trd:100,sz:100};

/* DOMContentLoaded moved to index.html shell */

/* ===========================================================
   UTILITIES
   =========================================================== */
function fetchT(url,ms){
  ms=ms||15000;
  return new Promise(function(res,rej){
    var t=setTimeout(function(){rej(new Error('Timeout'));},ms);
    fetch(url).then(function(r){clearTimeout(t);res(r);}).catch(function(e){clearTimeout(t);rej(e);});
  });
}
function showL(on,txt){
  document.getElementById('loading').style.display=on?'block':'none';
  if(txt)document.getElementById('loadingText').textContent=txt;
  /* Only disable the main action buttons, not AI or utility buttons */
  var btn=document.getElementById('fetchBtn');if(btn)btn.disabled=on;
}
function showE(m){var e=document.getElementById('errDiv');e.textContent=m;e.style.display='block';setTimeout(function(){e.style.display='none';},12000);}
function hideE(){document.getElementById('errDiv').style.display='none';}
function wk(d){var u=new Date(Date.UTC(d.getFullYear(),d.getMonth(),d.getDate()));var dn=u.getUTCDay()||7;u.setUTCDate(u.getUTCDate()+4-dn);var y=new Date(Date.UTC(u.getUTCFullYear(),0,1));return Math.ceil((((u-y)/86400000)+1)/7);}
function pct(arr,v){var s=arr.slice().sort(function(a,b){return a-b;});var i=s.indexOf(v);return s.length>1?(i/(s.length-1))*100:50;}
function pts(dates,vals){return dates.map(function(d,i){return{x:d,y:vals[i]};});}
function si(v){return(v==null||v==='')?0:(parseInt(v)||0);}
function ff(n){return Math.abs(n)>=1000?(n/1000).toFixed(1)+'k':n.toLocaleString();}

function findF(rec,pats){
  if(!pats||!pats.length)return null;
  /* Pass 1: exact match with non-empty value */
  for(var i=0;i<pats.length;i++){var p=pats[i];if(rec.hasOwnProperty(p)&&rec[p]!=null&&rec[p]!=='')return p;}
  /* Pass 2: exact match even if value is null/empty (field exists in schema) */
  for(var i=0;i<pats.length;i++){if(rec.hasOwnProperty(pats[i]))return pats[i];}
  /* Pass 3: case-insensitive */
  var k=Object.keys(rec);
  for(var i=0;i<pats.length;i++){var lp=pats[i].toLowerCase();for(var j=0;j<k.length;j++){if(k[j].toLowerCase()===lp)return k[j];}}
  return null;
}

/* Fuzzy field finder: returns first key containing ALL word fragments */
function findFuzzy(keys,words){
  var wl=words.map(function(w){return w.toLowerCase();});
  return keys.find(function(k){var kl=k.toLowerCase();return wl.every(function(w){return kl.indexOf(w)!==-1;});})
         ||null;
}

function matchComm(name,list){
  var u=name.toUpperCase();
  for(var i=0;i<list.length;i++){if(list[i].toUpperCase()===u)return list[i];}
  for(var i=0;i<list.length;i++){if(list[i].toUpperCase().indexOf(u)!==-1)return list[i];}
  var np=u.split(' - ')[0].trim(),ep2=u.split(' - ').slice(1).join(' - ').trim();
  for(var i=0;i<list.length;i++){var cu=list[i].toUpperCase(),cn=cu.split(' - ')[0].trim(),ce=cu.split(' - ').slice(1).join(' - ').trim();if(cn.indexOf(np)!==-1&&(!ep2||ce.indexOf(ep2)!==-1))return list[i];}
  for(var i=0;i<list.length;i++){var cn=list[i].toUpperCase().split(' - ')[0].trim();if(cn===np||cn.indexOf(np)!==-1||np.indexOf(cn)!==-1)return list[i];}
  return null;
}

/* ===========================================================
   PROCESS DATA — safe and normal versions
   =========================================================== */
function procData(raw,cat,crop){
  cat=cat||'managed_money';crop=crop||'all';
  if(!raw||!raw.length)return null;
  raw=raw.slice().sort(function(a,b){return new Date(a.report_date_as_yyyy_mm_dd)-new Date(b.report_date_as_yyyy_mm_dd);});
  /* Use the LAST (most recent) record for field detection — early records (pre-2009)
     may have null crop-year fields since CFTC only introduced old/other breakdown in 2009 */
  var f=raw[raw.length-1],fFirst=raw[0],fm=getFM(cat,crop);
  var allKeys=Object.keys(f);
  /* Primary field detection from most recent record */
  var fl={L:findF(f,fm.long),S:findF(f,fm.short),Sp:findF(f,fm.spread),tl:findF(f,fm.tl),ts:findF(f,fm.ts)};
  /* Fuzzy fallback for crop-year fields if exact names not found */
  if(!fl.L&&crop!=='all'){
    var sfx=crop;  /* 'old' or 'other' */
    var catKey=cat==='managed_money'?'money':cat==='swap_dealers'?'swap':cat==='prod_merc'?'merc':'rept';
    fl.L=findFuzzy(allKeys,['long',sfx,catKey])||findFuzzy(allKeys,['long',sfx]);
    fl.S=findFuzzy(allKeys,['short',sfx,catKey])||findFuzzy(allKeys,['short',sfx]);
  }
  /* OI: prefer crop-specific, fall back to all */
  var oiPats=crop==='all'?['open_interest_all','open_interest']:['open_interest_'+crop,'open_interest_all','open_interest'];
  fl.oi=findF(f,oiPats)||findF(fFirst,oiPats);
  if(!fl.L||!fl.S){
    console.warn('[procData] No fields for',cat,crop,'- tried:',fm.long,fm.short,'- available crop fields:',allKeys.filter(function(k){return k.indexOf(crop)!==-1;}).slice(0,8));
    return null;
  }
  var n=raw.length,p={dates:[],long:[],short:[],spread:[],tL:[],tS:[],oi:[],cat:cat,crop:crop,comm:fFirst.market_and_exchange_names};
  for(var i=0;i<n;i++){var d=raw[i];p.dates.push(d.report_date_as_yyyy_mm_dd);p.long.push(si(d[fl.L]));p.short.push(si(d[fl.S]));p.spread.push(fl.Sp?si(d[fl.Sp]):0);p.tL.push(fl.tl?si(d[fl.tl]):0);p.tS.push(fl.ts?si(d[fl.ts]):0);p.oi.push(fl.oi?si(d[fl.oi]):0);}
  p.tT=p.tL.map(function(v,i){return v+p.tS[i];});
  p.net=p.long.map(function(v,i){return v-p.short[i];});
  p.lPct=p.oi.map(function(v,i){return v>0?p.long[i]/v*100:0;});
  p.sPct=p.oi.map(function(v,i){return v>0?p.short[i]/v*100:0;});
  p.nPct=p.lPct.map(function(v,i){return v-p.sPct[i];});
  p.plL=p.tL.map(function(v,i){return v>0?p.long[i]/v:0;});
  p.plS=p.tS.map(function(v,i){return v>0?p.short[i]/v:0;});
  return p;
}

/* Returns zeroed dataset if fields not found — so tables render gracefully */
function procSafe(raw,cat,crop){
  var r=procData(raw,cat,crop);
  if(r)return r;
  if(!raw||!raw.length)return null;
  var n=raw.length,z=function(){return new Array(n).fill(0);};
  var dates=raw.map(function(d){return d.report_date_as_yyyy_mm_dd;});
  return{dates:dates,long:z(),short:z(),spread:z(),tL:z(),tS:z(),oi:z(),tT:z(),net:z(),lPct:z(),sPct:z(),nPct:z(),plL:z(),plS:z(),cat:cat,crop:crop,_nd:true,comm:raw[0].market_and_exchange_names};
}

/* ===========================================================
   LOAD COMMODITY LIST
   Always shows dropdown immediately from hardcoded BCOM names.
   API verification runs in background and updates matches silently.
   =========================================================== */
function loadList(){
  /* Step 1: Build dropdown immediately from hardcoded BCOM names — no API wait */
  buildFallback();
  showL(false);

  /* Step 2: Quietly verify/update names against the live API in the background */
  var url=EP.combined+'?$select=market_and_exchange_names&$limit=5000&$order=report_date_as_yyyy_mm_dd+DESC';
  var ctrl=typeof AbortController!=='undefined'?new AbortController():null;
  var tid=setTimeout(function(){if(ctrl)ctrl.abort();},20000);
  fetch(url,ctrl?{signal:ctrl.signal}:{})
  .then(function(r){clearTimeout(tid);if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
  .then(function(data){
    if(!Array.isArray(data)||!data.length)return;
    var seen={};apiList=[];
    data.forEach(function(d){var n=d.market_and_exchange_names;if(n&&!seen[n]){seen[n]=true;apiList.push(n);}});
    apiList.sort();
    /* Re-build dropdown with exact API names for accurate fetching */
    buildSel(apiList);
    buildSeaCommSel();
  })
  .catch(function(e){
    /* API unreachable — hardcoded fallback already loaded, just log */
    console.warn('API name verify failed (using hardcoded names):',e.message);
  });
}

function buildSel(api){
  var sel=document.getElementById('commoditySelect');sel.innerHTML='<option value="">-- Select BCOM Commodity --</option>';allBCOM=[];
  Object.keys(BCOM).forEach(function(sec){
    var comms=BCOM[sec],og=document.createElement('optgroup');og.label=sec;var any=false;
    comms.forEach(function(c){var m=matchComm(c.cftc,api);if(m){var o=document.createElement('option');o.value=m;o.textContent=c.name+' ('+c.ticker+')';o.setAttribute('data-cn',c.name);og.appendChild(o);any=true;allBCOM.push({name:c.name,ticker:c.ticker,sector:sec,api:m});}else console.warn('No match:',c.cftc);});
    if(any)sel.appendChild(og);
  });sel.disabled=false;
}

function buildFallback(){
  var sel=document.getElementById('commoditySelect');sel.innerHTML='<option value="">-- Select Commodity --</option>';allBCOM=[];
  Object.keys(BCOM).forEach(function(sec){var comms=BCOM[sec],og=document.createElement('optgroup');og.label=sec;comms.forEach(function(c){var o=document.createElement('option');o.value=c.cftc;o.textContent=c.name+' ('+c.ticker+')';o.setAttribute('data-cn',c.name);og.appendChild(o);allBCOM.push({name:c.name,ticker:c.ticker,sector:sec,api:c.cftc});});sel.appendChild(og);});sel.disabled=false;
}

function onCommChange(){
  var sel=document.getElementById('commoditySelect'),opt=sel.options[sel.selectedIndex];
  var cn=opt?opt.getAttribute('data-cn'):'';
  cropInfo=cn&&CROP_COMM[cn]?{name:cn}:null;
  var has=!!cropInfo;
  document.getElementById('cropYearGroup').style.display=has?'':'none';
  document.getElementById('cropNotes').style.display=has?'':'none';
  if(!has)document.getElementById('cropYear').value='all';
  if(has)document.getElementById('cropBadge').textContent='('+cn+')';
}
function toggleCropNotes(){var b=document.getElementById('cropBody'),t=document.getElementById('cropToggle'),o=b.style.display==='block';b.style.display=o?'none':'block';t.textContent=o?'▼':'▲';}
function onCropYearChange(){
  if(!rawCache)return;
  var tc=document.getElementById('traderCategory').value,crop=document.getElementById('cropYear').value||'all';
  CD=procData(rawCache,tc,crop);if(!CD)return;
  ATD={};CATS.forEach(function(c){ATD[c]=procData(rawCache,c,crop);});
  updateAll();
}

/* ===========================================================
   FETCH DATA
   =========================================================== */
function fetchData(){
  var comm=document.getElementById('commoditySelect').value,rt=document.getElementById('reportType').value,tc=document.getElementById('traderCategory').value,sd=document.getElementById('startDate').value,ed=document.getElementById('endDate').value;
  if(!comm){showE('Select a commodity first');return;}
  var crop=document.getElementById('cropYear').value||'all';
  showL(true,'Fetching '+comm.split(' - ')[0]+'...');hideE();
  var ep=EP[rt],enc=comm.replace(/'/g,"''");
  var url=ep+"?$where=market_and_exchange_names='"+enc+"' AND report_date_as_yyyy_mm_dd >= '"+sd+"' AND report_date_as_yyyy_mm_dd <= '"+ed+"'&$order=report_date_as_yyyy_mm_dd ASC&$limit=10000";
  dbgInfo={url:url,comm:comm,cat:tc};
  fetchT(url,30000).then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
  .then(function(data){
    dbgInfo.n=data.length;if(!data.length)throw new Error('No data');
    dbgInfo.sample=data[0];rawCache=data;
    CD=procData(data,tc,crop);if(!CD)throw new Error('Field mapping failed. Open Debug for available fields.');
    ATD={};CATS.forEach(function(c){ATD[c]=procData(data,c,crop);});
    seaCache[comm]=CD;
    /* Reset zooms */
    ['pos','cmp','trd','sz'].forEach(function(k){zPct[k]=100;var s=document.getElementById('zs_'+k);if(s)s.value=100;var l=document.getElementById('zl_'+k);if(l)l.textContent='All data';});
    ['chart1','chart2','chart3','chart4','chart5','weeklyDetail'].forEach(function(id){document.getElementById(id).style.display='block';});
    popYears();buildSeaCommSel();updateAll();buildWeeklyDetail();
    /* Auto-trigger all other sections */
    generateSummary();
    doScatter();
    doScatterPct();
    if(isCrop(comm))doAgriCrop();
    /* Show AI section if key is present */
    if(sessionStorage.getItem('groqKey'))document.getElementById('aiSec').style.display='block';
    showL(false);
  }).catch(function(e){dbgInfo.err=e.message;showE('Error: '+e.message);showL(false);});
}

/* ===========================================================
   ZOOM
   =========================================================== */
function onZoom(key,val){
  zPct[key]=parseInt(val);
  var ch=charts[key];if(!ch||!CD)return;
  applyZoom(ch,key);updateZoomLbl(key);
}
function resetZoom(key){
  zPct[key]=100;var s=document.getElementById('zs_'+key);if(s)s.value=100;
  var ch=charts[key];if(ch&&CD){applyZoom(ch,key);updateZoomLbl(key);}
}
function applyZoom(ch,key){
  var p=zPct[key]||100,dates=CD.dates,n=dates.length;
  if(p>=100){ch.options.scales.x.min=undefined;ch.options.scales.x.max=undefined;}
  else{var show=Math.max(8,Math.round(n*p/100)),si2=Math.max(0,n-show);ch.options.scales.x.min=dates[si2];ch.options.scales.x.max=dates[n-1];}
  ch.update('none');
}
function updateZoomLbl(key){
  var el=document.getElementById('zl_'+key);if(!el)return;
  var p=zPct[key]||100;if(p>=100){el.textContent='All data';return;}
  el.textContent='Last ~'+Math.max(8,Math.round(CD.dates.length*p/100))+' wks';
}

/* ===========================================================
   CHART HELPERS
   =========================================================== */
function mkLine(ctx,ds,xTime,yLabel,isP,showLeg){
  var sc={x:{grid:{display:false},ticks:{maxTicksLimit:12,font:{size:9},color:'#333'}},y:{grid:{color:'rgba(0,0,0,0.05)'},ticks:{font:{size:9},color:'#333',callback:function(v){return isP?v.toFixed(0)+'%':(Math.abs(v)>=1000?(v/1000).toFixed(0)+'k':v);}},title:{display:!!yLabel,text:yLabel||'',font:{weight:'bold',size:10},color:'#333'}}};
  if(xTime){sc.x.type='time';sc.x.time={unit:'month',displayFormats:{month:'MMM yy'}};}
  return new Chart(ctx,{type:'line',data:{datasets:ds},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:!!showLeg,position:'top',labels:{boxWidth:12,font:{size:9},color:'#333'}}},scales:sc}});
}

/* ===========================================================
   MISC
   =========================================================== */
function dlCSV(){
  if(!CD){showE('No data loaded');return;}
  var csv='Date,Long,Short,Net,Spread,Long%OI,Short%OI,Net%OI,TrL,TrS,L/Tr,S/Tr,OI\n';
  CD.dates.forEach(function(dt,i){csv+=[dt,CD.long[i],CD.short[i],CD.net[i],CD.spread[i],CD.lPct[i].toFixed(2),CD.sPct[i].toFixed(2),CD.nPct[i].toFixed(2),CD.tL[i],CD.tS[i],CD.plL[i].toFixed(2),CD.plS[i].toFixed(2),CD.oi[i]].join(',')+'\n';});
  var b=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='COT_'+new Date().toISOString().split('T')[0]+'.csv';a.click();
}
function toggleDbg(){
  var p=document.getElementById('dbgPanel');p.style.display=p.style.display==='block'?'none':'block';
  var c=document.getElementById('dbgContent');
  if(!dbgInfo.n){c.innerHTML='<p>Click Generate Charts first.</p>';return;}
  var h='<p>URL: '+(dbgInfo.url||'')+'</p><p>Records: '+(dbgInfo.n||0)+'</p>';
  if(dbgInfo.sample){
    var sample=dbgInfo.sample;
    /* Show crop-year field detection for the LAST record */
    var lastRec=rawCache&&rawCache.length?rawCache[rawCache.length-1]:sample;
    var cropKeys=Object.keys(lastRec).filter(function(k){return k.indexOf('_old')!==-1||k.indexOf('_other')!==-1;});
    h+='<p><strong>Crop-year fields in latest record ('+cropKeys.length+'):</strong> '+cropKeys.slice(0,20).join(', ')+(cropKeys.length>20?'...':'')+'</p>';
    h+='<pre style="background:#111;padding:8px;max-height:220px;overflow:auto;font-size:0.7em;">'+Object.keys(lastRec).sort().map(function(k){return k+': '+String(lastRec[k]).substring(0,50);}).join('\n')+'</pre>';
  }
  c.innerHTML=h;
}
function doPrint(){
  /* Explicitly resize every chart canvas to its print height before printing.
     This ensures Chart.js redraws at the correct size rather than overflowing. */
  var pH={
    posChart:210,cmpChart:200,trdChart:210,szChart:200,seaChart:330,
    sc1:195,sc2:195,sc3:195,sc4:195,sc5:195,sc6:195,
    sp1:195,sp2:195,sp3:195,sp4:195,sp5:195,sp6:195,
    aSeaChartOld:200,aSeaChartOther:200,aSeaChartAll:200
  };
  var saved=[];
  Object.keys(pH).forEach(function(id){
    var canvas=document.getElementById(id);if(!canvas)return;
    var cont=canvas.parentElement;
    saved.push({el:cont,h:cont.style.height});
    cont.style.height=pH[id]+'px';
  });
  /* Resize all Chart.js instances */
  Object.keys(charts).forEach(function(k){if(charts[k]&&charts[k].resize){try{charts[k].resize();}catch(e){}}});
  setTimeout(function(){
    window.print();
    setTimeout(function(){
      saved.forEach(function(s){s.el.style.height=s.h||'';});
      Object.keys(charts).forEach(function(k){if(charts[k]&&charts[k].resize){try{charts[k].resize();}catch(e){}}});
    },600);
  },400);
}
