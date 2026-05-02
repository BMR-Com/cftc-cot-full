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
}

/* ===========================================================
   AI TAB — Groq integration + pre-computed data
   =========================================================== */
var _aiInited = false;

