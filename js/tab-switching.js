/* ===========================================================
   TAB SWITCHING
   =========================================================== */
function switchTab(tab){
  var allTabs = ['cot','summary','scatter','seasonality','formula','ai'];
  allTabs.forEach(function(t){
    var pane = document.getElementById('pane_'+t);
    var btn = document.getElementById('tb_'+t);
    if(pane) pane.style.display = t===tab ? 'block' : 'none';
    if(btn) btn.classList.toggle('active', t===tab);
  });

  // Load tab content on demand
  if(tab==='cot' && !_tabLoaded['cot']){
    loadTab('cot', 'tabs/cot-tab.html', 'js/cot-tab.js').then(function(){ initCotTab(); });
  }
  if(tab==='summary' && !_tabLoaded['summary']){
    loadTab('summary', 'tabs/summary-tab.html', 'js/summary-tab.js').then(function(){ initSummaryTab(); });
  }
  if(tab==='scatter' && !_tabLoaded['scatter']){
    loadTab('scatter', 'tabs/scatter-tab.html', 'js/scatter-tab.js').then(function(){ initScatterTab(); });
  }
  if(tab==='seasonality' && !_tabLoaded['seasonality']){
    loadTab('seasonality', 'tabs/seasonality-tab.html', 'js/seasonality-tab.js').then(function(){ initSeasonalityTab(); });
  }
  if(tab==='formula' && !_tabLoaded['formula']){
    loadTab('formula', 'tabs/formula-tab.html', 'js/formula-tab.js').then(function(){ initFormulaTab(); });
  }
  if(tab==='ai' && !_tabLoaded['ai']){
    loadTab('ai', 'tabs/ai-tab.html', 'js/ai-tab.js').then(function(){ initAiTab(); });
  }

  // Call init functions for already-loaded tabs
  if(tab==='ai' && _tabLoaded['ai']) initAiTab();
  if(tab==='formula' && _tabLoaded['formula']) initFormulaTab();
  // First visit to the COT Analyzer: show Cotton straight away instead of an empty page
  if(tab==='cot' && _tabLoaded['cot']) autoLoadDefaultMarket();
  if(tab==='cot' && !_tabLoaded['cot']) setTimeout(function wait(){ if(_tabLoaded['cot']) autoLoadDefaultMarket(); else setTimeout(wait,150); },150);
}

/* ===========================================================
   AI TAB — Groq integration + pre-computed data
   =========================================================== */
var _aiInited = false;


var _autoLoaded=false;
function autoLoadDefaultMarket(){
  if(_autoLoaded||typeof CD==='undefined'||CD)return;
  var sel=document.getElementById('commoditySelect');if(!sel||sel.value)return;
  var o=sel.querySelector('option[data-tk="CT"]');if(!o)return;
  _autoLoaded=true;sel.value=o.value;
  if(typeof onCommChange==='function')onCommChange();
  if(typeof fetchData==='function')fetchData();
}
