/* ===========================================================
   TAB SWITCHING
   =========================================================== */
function switchTab(tab){
  var allTabs = ['cot','summary','scatter','seasonality','formula','ai'];
  allTabs.forEach(function(t){
    var pane = document.getElementById('pane_'+t);
    var btn = document.getElementById('tb_'+t);
    if(pane) {
      try { pane.style.display = t===tab ? 'block' : 'none'; } 
      catch(e) { console.warn('Cannot set style on pane_'+t, e); }
    }
    if(btn) {
      try { btn.classList.toggle('active', t===tab); } 
      catch(e) { console.warn('Cannot toggle class on tb_'+t, e); }
    }
  });

  // Load tab content on demand
  var tabConfigs = {
    'cot': {html: 'tabs/cot-tab.html', js: 'js/cot-tab.js', init: initCotTab},
    'summary': {html: 'tabs/summary-tab.html', js: 'js/summary-tab.js', init: initSummaryTab},
    'scatter': {html: 'tabs/scatter-tab.html', js: 'js/scatter-tab.js', init: initScatterTab},
    'seasonality': {html: 'tabs/seasonality-tab.html', js: 'js/seasonality-tab.js', init: initSeasonalityTab},
    'formula': {html: 'tabs/formula-tab.html', js: 'js/formula-tab.js', init: initFormulaTab},
    'ai': {html: 'tabs/ai-tab.html', js: 'js/ai-tab.js', init: initAiTab}
  };

  var config = tabConfigs[tab];
  if(config && !_tabLoaded[tab]){
    loadTab(tab, config.html, config.js, config.init);
  }
}

