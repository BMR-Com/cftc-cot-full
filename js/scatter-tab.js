/* ===========================================================
   SCATTER TAB — Prod/Merch vs Managed Money Scatter Plots
   Loaded dynamically by tab-switching.js
   =========================================================== */

function initScatterTab() {
    if(!scData || !scData.length) {
        doScatter();
        doScatterPct();
    }
    console.log('[Scatter Tab] Initialized');
}

/* ===========================================================
   SCATTER PLOTS
   =========================================================== */
function doScatter(){
  showL(true,'Generating Prod vs MM scatter...');document.getElementById('chart6').style.display='block';scData=[];
  var ep=EP[document.getElementById('reportType').value],tot=allBCOM.length,done=0;
  if(!tot){showL(false);return;}
  allBCOM.forEach(function(it,idx){
    fetchT(ep+"?$where=market_and_exchange_names='"+it.api.replace(/'/g,"''")+"' AND report_date_as_yyyy_mm_dd >= '2006-01-01'&$order=report_date_as_yyyy_mm_dd ASC&$limit=10000",20000)
    .then(function(r){return r.json();}).then(function(data){
      if(data.length<10)return;var pr=procData(data,'prod_merc'),mm=procData(data,'managed_money');if(!pr||!mm)return;
      var l=pr.net.length-1;
      scData.push({comm:it.name,idx:idx,pSP:pct(pr.short,pr.short[l]),mSP:pct(mm.short,mm.short[l]),mLP:pct(mm.long,mm.long[l]),pLP:pct(pr.long,pr.long[l]),pNP:pct(pr.net,pr.net[l]),mNP:pct(mm.net,mm.net[l]),pS:pr.short[l],mS:mm.short[l],pL:pr.long[l],mL:mm.long[l],pN:pr.net[l],mN:mm.net[l],mSPoi:pct(mm.sPct,mm.sPct[l]),mLPoi:pct(mm.lPct,mm.lPct[l]),mNPoi:pct(mm.nPct,mm.nPct[l])});
    }).catch(function(){}).finally(function(){done++;if(done>=tot){
      var combos=[{c:'sc1',x:'pSP',y:'mSP',xl:'Prod Short',yl:'MM Short'},{c:'sc2',x:'pSP',y:'mLP',xl:'Prod Short',yl:'MM Long'},{c:'sc3',x:'pLP',y:'mSP',xl:'Prod Long',yl:'MM Short'},{c:'sc4',x:'pLP',y:'mLP',xl:'Prod Long',yl:'MM Long'},{c:'sc5',x:'pNP',y:'mNP',xl:'Prod Net',yl:'MM Net'},{c:'sc6',x:'pNP',y:'mNP',xl:'Prod Net',yl:'MM Net'}];
      drawScatter('sc',scData,combos);drawLeg('scLeg',scData);popExec(scData);showL(false);
    }});
  });
}
function doScatterPct(){
  showL(true,'Generating %OI scatter...');document.getElementById('chart7').style.display='block';spData=[];
  var ep=EP[document.getElementById('reportType').value],tot=allBCOM.length,done=0;
  if(!tot){showL(false);return;}
  allBCOM.forEach(function(it,idx){
    fetchT(ep+"?$where=market_and_exchange_names='"+it.api.replace(/'/g,"''")+"' AND report_date_as_yyyy_mm_dd >= '2006-01-01'&$order=report_date_as_yyyy_mm_dd ASC&$limit=10000",20000)
    .then(function(r){return r.json();}).then(function(data){
      if(data.length<10)return;var pr=procData(data,'prod_merc'),mm=procData(data,'managed_money');if(!pr||!mm)return;var l=pr.net.length-1;
      spData.push({comm:it.name,idx:idx,pSP:pct(pr.sPct,pr.sPct[l]),mSP:pct(mm.sPct,mm.sPct[l]),mLP:pct(mm.lPct,mm.lPct[l]),pLP:pct(pr.lPct,pr.lPct[l]),pNP:pct(pr.nPct,pr.nPct[l]),mNP:pct(mm.nPct,mm.nPct[l]),pS:pr.sPct[l],mS:mm.sPct[l],pL:pr.lPct[l],mL:mm.lPct[l],pN:pr.nPct[l],mN:mm.nPct[l]});
    }).catch(function(){}).finally(function(){done++;if(done>=tot){
      var combos=[{c:'sp1',x:'pSP',y:'mSP',xl:'Prod S%',yl:'MM S%'},{c:'sp2',x:'pSP',y:'mLP',xl:'Prod S%',yl:'MM L%'},{c:'sp3',x:'pLP',y:'mSP',xl:'Prod L%',yl:'MM S%'},{c:'sp4',x:'pLP',y:'mLP',xl:'Prod L%',yl:'MM L%'},{c:'sp5',x:'pNP',y:'mNP',xl:'Prod N%',yl:'MM N%'},{c:'sp6',x:'pNP',y:'mNP',xl:'Prod N%',yl:'MM N%'}];
      drawScatter('sp',spData,combos);drawLeg('spLeg',spData);showL(false);
    }});
  });
}

/* Point styles cycling through distinct shapes */
var PS=['circle','rect','triangle','star','cross','rectRot','rectRounded','crossRot'];
/* Distinct color palette — 24 colors covering all BCOM commodities */
var UC=['#e6194b','#3cb44b','#4363d8','#f58231','#911eb4','#42d4f4','#f032e6','#9A6324','#000075','#469990','#2c3e50','#1abc9c','#d35400','#c0392b','#2ecc71','#8e44ad','#16a085','#e8a838','#a9a9a9','#dcbeff','#aaffc3','#800000','#808000','#bfef45'];

function drawScatter(pfx,data,combos){
  combos.forEach(function(c,idx){
    var ctx=document.getElementById(c.c).getContext('2d'),ck=pfx+(idx+1);if(charts[ck])charts[ck].destroy();
    /* Each commodity = its own dataset so legend entries work */
    var ds=data.map(function(it){
      var col=UC[it.idx%UC.length];
      var ps=PS[it.idx%PS.length];
      return{
        label:it.comm,
        data:[{x:it[c.x],y:it[c.y],comm:it.comm}],
        backgroundColor:col,borderColor:col,
        pointStyle:ps,pointRadius:7,pointHoverRadius:11,borderWidth:1.5
      };
    });
    /* Quadrant lines */
    ds.push({data:[{x:50,y:0},{x:50,y:100}],borderColor:'rgba(0,0,0,0.2)',borderDash:[4,4],pointRadius:0,fill:false,showLine:true,label:'_q1'});
    ds.push({data:[{x:0,y:50},{x:100,y:50}],borderColor:'rgba(0,0,0,0.2)',borderDash:[4,4],pointRadius:0,fill:false,showLine:true,label:'_q2'});
    charts[ck]=new Chart(ctx,{
      type:'scatter',
      data:{datasets:ds},
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{
          legend:{
            display:false
          },
          tooltip:{callbacks:{
            title:function(i){return i[0].raw.comm;},
            label:function(i){return[c.xl+': '+i.raw.x.toFixed(1)+'%ile',c.yl+': '+i.raw.y.toFixed(1)+'%ile'];}
          }}
        },
        scales:{
          x:{min:0,max:100,title:{display:true,text:c.xl+' %ile',font:{size:8},color:'#333'},ticks:{font:{size:7},color:'#333',maxTicksLimit:6}},
          y:{min:0,max:100,title:{display:true,text:c.yl+' %ile',font:{size:8},color:'#333'},ticks:{font:{size:7},color:'#333',maxTicksLimit:6}}
        }
      }
    });
  });
}
function drawLeg(id,data){
  /* Keep the HTML legend below charts as a backup for web view */
  var ct=document.getElementById(id);ct.innerHTML='';
  data.forEach(function(d){
    var e=document.createElement('div');e.className='comm-legend-item';
    var col=UC[d.idx%UC.length];
    e.innerHTML='<div style="background:'+col+';width:11px;height:11px;border-radius:2px;"></div><span>'+d.comm+'</span>';
    ct.appendChild(e);
  });
}

