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
    loadTab('cot', 'tabs/cot-tab.html', 'js/cot-tab.js', initCotTab);
  }
  if(tab==='summary' && !_tabLoaded['summary']){
    loadTab('summary', 'tabs/summary-tab.html', 'js/summary-tab.js', initSummaryTab);
  }
  if(tab==='scatter' && !_tabLoaded['scatter']){
    loadTab('scatter', 'tabs/scatter-tab.html', 'js/scatter-tab.js', initScatterTab);
  }
  if(tab==='seasonality' && !_tabLoaded['seasonality']){
    loadTab('seasonality', 'tabs/seasonality-tab.html', 'js/seasonality-tab.js', initSeasonalityTab);
  }
  if(tab==='formula' && !_tabLoaded['formula']){
    loadTab('formula', 'tabs/formula-tab.html', 'js/formula-tab.js', initFormulaTab);
  }
  if(tab==='ai' && !_tabLoaded['ai']){
    loadTab('ai', 'tabs/ai-tab.html', 'js/ai-tab.js', initAiTab);
  }

  // Init is called by loadTab when tab is first loaded, or by the cached path above
}

