/* Based on Paper Curation by 이제현 (https://github.com/jehyunlee/paper-curation)
 * 원본: pipeline/generate_network.py 의 D3 네트워크 스크립트를 이 키트의 데이터(wiki/papers, related.json, 주제 노트)에 맞게 고친 것.
 * 바꾼 점: 데이터는 network-data.js(window.LLMWIKI_GRAPH)에서 읽음(file:// 동작), UMAP·3D(three.js)·CDN 제거,
 *          관계 종류를 이 키트의 것(리뷰 근거 연결·자동 유사도·주제 공유·저자 공유)으로, 화면 글자는 한국어로,
 *          점 크기에 리뷰 점수 반영, 논문이 적을 때 점·간격·이름표를 크게, 상세 창에 「Codex에게 물어보기」 복사 버튼.
 */
(function(){
"use strict";
if(!window.d3){ return; }
document.documentElement.classList.add("net-live");
// Data
const DATA = window.LLMWIKI_GRAPH || {nodes:[],links:[],conns:{},catColors:{},catShapes:{},catCounts:{},subColors:{},subCounts:{},catSubs:{},relColors:{},relLabels:{},yearMin:2020,yearMax:2026};
const nodesRaw = DATA.nodes;
const linksRaw = DATA.links;
const NODECONNS = DATA.conns;
const catColors = DATA.catColors;
const catShapes = DATA.catShapes;
const catCounts = DATA.catCounts;
const shapeMap = {
  circle: d3.symbolCircle,
  square: d3.symbolSquare,
  triangle: d3.symbolTriangle,
  diamond: d3.symbolDiamond,
};
const subColors = DATA.subColors;
const subCounts = DATA.subCounts;
let colorBy = "cat"; // "cat" or "sub"
const catSubs = DATA.catSubs;
const relColors = DATA.relColors;
const relLabels = DATA.relLabels || {
  alternative:"\uD83D\uDD04 \uB2E4\uB978 \uC811\uADFC",
  extension:"\uD83D\uDD17 \uD6C4\uC18D \uC5F0\uAD6C",
  foundation:"\uD83C\uDFDB \uAE30\uBC18 \uC5F0\uAD6C",
  counterpoint:"\u2696\uFE0F \uBC18\uB860/\uBE44\uD310",
  application:"\uD83E\uDDEA \uC751\uC6A9"
};

const activeCats = new Set(Object.keys(catColors));
const activeRels = new Set(Object.keys(relColors));
let egoId = null;
let yearMin = DATA.yearMin, yearMax = DATA.yearMax;
let hlMode = null; // null, "hub", "bridge"
const hasUMAP = false; // 이 키트에는 UMAP 좌표가 없어 힘 기반 배치만 씁니다
const SMALL = nodesRaw.length <= 15; // 논문이 적을 때는 점·간격을 크게
const has3D = false;
let useUMAP = hasUMAP;

// SVG setup — fixed coordinate system so layout is INDEPENDENT of browser size.
// The SVG element still fills the viewport (CSS: width:100vw; height:100vh),
// but viewBox + preserveAspectRatio make the content scale uniformly while
// keeping the same aspect ratio and identical force-simulation geometry.
const svg = d3.select("#graph");
const W = 1600, H = 1000;  // fixed logical canvas (16:10)
svg.attr("viewBox",[0,0,W,H]).attr("preserveAspectRatio","xMidYMid meet");
const defs = svg.append("defs");
const glowFilter = defs.append("filter").attr("id","glow").attr("x","-50%").attr("y","-50%").attr("width","200%").attr("height","200%");
glowFilter.append("feGaussianBlur").attr("in","SourceGraphic").attr("stdDeviation","5").attr("result","blur1");
glowFilter.append("feGaussianBlur").attr("in","SourceGraphic").attr("stdDeviation","2").attr("result","blur2");
const feMerge = glowFilter.append("feMerge");
feMerge.append("feMergeNode").attr("in","blur1");
feMerge.append("feMergeNode").attr("in","blur2");
feMerge.append("feMergeNode").attr("in","SourceGraphic");
const g = svg.append("g");

// 링크 굵기: 관계 강도(0~1)에 비례
function lw(d){ return 1 + (d.w||0)*3; }
// 검색: 제목·요약·저자·짧은 이름(여러 단어는 모두 들어 있어야 함)
function nfc(x){ x=String(x||""); return x.normalize?x.normalize("NFC"):x; }
function hit(d,q){
  const hay=nfc(d.title+" "+(d.essence||"")+" "+(d.authors||"")+" "+d.num+" "+d.category).toLowerCase();
  return nfc(q).split(/\s+/).filter(Boolean).every(w=>hay.includes(w));
}

// Force simulation
const sim = d3.forceSimulation()
  .force("link",d3.forceLink().id(d=>d.id).distance(SMALL?230:60).strength(SMALL?0.25:0.4))
  .force("charge",d3.forceManyBody().strength(SMALL?-1400:-80))
  .force("x",d3.forceX(W/2).strength(SMALL?0.08:0.05))
  .force("y",d3.forceY(H/2).strength(SMALL?0.08:0.05))
  .force("collide",d3.forceCollide(d=>nr(d)+2))
  .alphaDecay(0.02);

// Pre-compute degree (connection count) per node
const degree = {};
linksRaw.forEach(l=>{
  const s=l.source.id||l.source, t=l.target.id||l.target;
  degree[s]=(degree[s]||0)+1;
  degree[t]=(degree[t]||0)+1;
});
let nodeSizeMul=SMALL?2.6:(nodesRaw.length<=60?1.5:1.0);
document.getElementById("node-size-slider").value=nodeSizeMul;
document.getElementById("node-size-label").textContent=nodeSizeMul.toFixed(1)+"x";
// 시작 위치: 가운데 둘레에 주제별로 나눠 놓고 시작(빨리 자리 잡고, 매번 같은 모양)
(function(){
  const cats=Object.keys(catColors);
  nodesRaw.forEach((n,i)=>{
    const ci=Math.max(0,cats.indexOf(n.category)), ang=2*Math.PI*ci/Math.max(1,cats.length)+i*0.7;
    const R=SMALL?180:300;
    n.x=W/2+R*Math.cos(ang)+((i*37)%50); n.y=H/2+R*Math.sin(ang)+((i*53)%50);
  });
})();
// 점 크기 = 연결 수 + 리뷰 종합 점수(1~5)
function nr(d){ return Math.max(3,Math.min(18,2+Math.sqrt(degree[d.id]||0)*2+(d.score||0)*0.6))*nodeSizeMul; }
document.getElementById("node-size-slider").addEventListener("input",function(){
  nodeSizeMul=parseFloat(this.value);
  document.getElementById("node-size-label").textContent=nodeSizeMul.toFixed(1)+"x";
  nodeG.selectAll("path.node").attr("d",d=>d3.symbol().type(shapeMap[d.shape]||d3.symbolCircle).size(nr(d)*nr(d)*3)());
});

const linkG = g.append("g");
const nodeG = g.append("g");
const labelG = g.append("g").attr("id","node-labels");
const tooltip = document.getElementById("tooltip");
const linkTooltip = document.getElementById("link-tooltip");
const info = document.getElementById("info");

// Track current zoom level for label rendering
let currentZoom = 1;
const zoomBehavior = d3.zoom().scaleExtent([0.1,8]).on("zoom",e=>{
  g.attr("transform",e.transform);
  currentZoom = e.transform.k;
  updateLabels();
});
svg.call(zoomBehavior);

function isNodeActive(n){
  if(!activeCats.has(n.category)) return false;
  if(!activeSubs.has(n.sub_category||"General")) return false;
  if(n.year&&n.year.match(/^\d{4}$/)&&(parseInt(n.year)<yearMin||parseInt(n.year)>yearMax)) return false;
  return true;
}
function getVisible(){
  // Mark all nodes active/inactive instead of filtering
  nodesRaw.forEach(n=>{ n._active = isNodeActive(n); });
  const activeIds = new Set(nodesRaw.filter(n=>n._active).map(n=>n.id));
  let ls = linksRaw.filter(l=>activeRels.has(l.relation)&&activeIds.has(l.source.id||l.source)&&activeIds.has(l.target.id||l.target));
  if(egoId){
    const neighbors = new Set([egoId]);
    ls.forEach(l=>{
      const s=l.source.id||l.source, t=l.target.id||l.target;
      if(s===egoId) neighbors.add(t);
      if(t===egoId) neighbors.add(s);
    });
    nodesRaw.forEach(n=>{ if(n._active && !neighbors.has(n.id)) n._active=false; });
    const nids2 = new Set(nodesRaw.filter(n=>n._active).map(n=>n.id));
    ls = ls.filter(l=>nids2.has(l.source.id||l.source)&&nids2.has(l.target.id||l.target));
  }
  return [nodesRaw, ls];
}
const ghostOp = ()=> parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ghost-opacity'))||0.08;

function render(){
  const [ns,ls] = getVisible();
  const activeCount = ns.filter(n=>n._active).length;
  document.getElementById("node-count").textContent=activeCount;
  document.getElementById("link-count").textContent=ls.length;

  const lk = linkG.selectAll("line").data(ls,d=>(d.source.id||d.source)+"-"+(d.target.id||d.target)+"-"+d.relation);
  lk.exit().remove();
  const lkE = lk.enter().append("line")
    .attr("stroke",d=>d.color).attr("stroke-opacity",0.45).attr("stroke-width",lw)
    .on("mouseover",(e,d)=>{
      d3.select(e.currentTarget).attr("stroke-width",d=>lw(d)+2).attr("stroke-opacity",0.9);
      const s=d.source.id||d.source, t=d.target.id||d.target;
      nodeG.selectAll("path.node").filter(n=>n.id===s||n.id===t).attr("filter","url(#glow)");
      linkTooltip.style.display="block";
      linkTooltip.style.left=(e.clientX+10)+"px";
      linkTooltip.style.top=(e.clientY-8)+"px";
      linkTooltip.innerHTML="<b>"+esc(d.sl)+" \u2194 "+esc(d.tl)+"</b><br>"+esc(relLabels[d.relation]||d.relation)+(d.reason?" \u2014 "+esc(d.reason.slice(0,140)):"");
    })
    .on("mouseout",(e,d)=>{
      d3.select(e.currentTarget).attr("stroke-width",lw).attr("stroke-opacity",0.45);
      nodeG.selectAll("path.node").attr("filter",null);
      linkTooltip.style.display="none";
    });
  const lkAll = lkE.merge(lk);

  const nd = nodeG.selectAll("path.node").data(ns,d=>d.id);
  nd.exit().remove();
  const ndE = nd.enter().append("path").attr("class","node")
    .attr("d",d=>d3.symbol().type(shapeMap[d.shape]||d3.symbolCircle).size(nr(d)*nr(d)*3)())
    .attr("fill",d=>d.color)
    .attr("stroke",d=>d.multi?"#666":getComputedStyle(document.documentElement).getPropertyValue('--node-stroke')).attr("stroke-width",d=>d.multi?1.5:0.5)
    .attr("cursor","pointer")
    .call(d3.drag()
      .on("start",(e,d)=>{ if(useUMAP) return; if(!e.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;})
      .on("drag",(e,d)=>{ if(useUMAP) return; d.fx=e.x;d.fy=e.y;})
      .on("end",(e,d)=>{ if(useUMAP) return; if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}))
    .on("mouseover",(e,d)=>{
      if(!d._active) return;
      d3.select(e.currentTarget).attr("filter","url(#glow)").raise();
      tooltip.style.display="block";
      tooltip.style.left=(e.clientX+12)+"px";
      tooltip.style.top=(e.clientY-10)+"px";
      const cats = d.all_categories ? d.all_categories.join(" \u00B7 ") : d.category;
      const essenceSnip = d.essence?(d.essence.slice(0,100)+(d.essence.length>100?"...":"")):"";
      tooltip.innerHTML = '<div class="tt-title"><span class="tt-score" style="background:'+d.color+'"></span>'+esc(d.num)+' \u00B7 '+esc(d.title)+'</div>'
        +'<div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:0.15rem">'+esc(cats)+' \u00B7 '+d.year+' \u00B7 \uC810\uC218 '+(d.score||'-')+'/5</div>'
        +(essenceSnip?'<div class="tt-essence">'+esc(essenceSnip)+'</div>':'');
    })
    .on("mouseout",(e,d)=>{d3.select(e.currentTarget).attr("filter",null);tooltip.style.display="none";})
    .on("click",(e,d)=>{if(!d._active) return; e.stopPropagation();showInfo(d);});
  const ndAll = ndE.merge(nd);

  // Base styling: active vs ghost
  const go = ghostOp();
  ndAll.attr("fill",d=>{
      const c = colorBy==="sub"?(subColors[d.sub_category]||"#999"):d.color;
      return d._active ? c : c;
    })
    .attr("opacity",d=>d._active?1:go)
    .attr("d",d=>d3.symbol().type(shapeMap[d.shape]||d3.symbolCircle).size(nr(d)*nr(d)*3)())
    .attr("pointer-events",d=>d._active?"all":"none");

  // Highlight modes (only affect active nodes)
  if(egoId){
    ndAll.filter(d=>d._active).attr("opacity",d=>d.id===egoId?1:0.8);
  } else if(hlMode==="hub"){
    const activeNs = ns.filter(n=>n._active);
    const sorted = [...activeNs].sort((a,b)=>(degree[b.id]||0)-(degree[a.id]||0));
    const top10 = new Set(sorted.slice(0,10).map(n=>n.id));
    ndAll.filter(d=>d._active).attr("opacity",d=>top10.has(d.id)?1:go*1.5)
      .attr("d",d=>d3.symbol().type(shapeMap[d.shape]||d3.symbolCircle).size((top10.has(d.id)?nr(d)*2:nr(d))**2*3)());
    lkAll.attr("stroke-opacity",d=>{
      const s=d.source.id||d.source,t=d.target.id||d.target;
      return top10.has(s)||top10.has(t)?0.5:0.04;
    });
  } else if(hlMode==="bridge"){
    const bridgeIds = new Set();
    ls.forEach(l=>{
      const sn=ns.find(n=>n.id===(l.source.id||l.source));
      const tn=ns.find(n=>n.id===(l.target.id||l.target));
      if(sn&&tn&&sn._active&&tn._active&&sn.category!==tn.category){ bridgeIds.add(sn.id); bridgeIds.add(tn.id); }
    });
    ndAll.filter(d=>d._active).attr("opacity",d=>bridgeIds.has(d.id)?1:go*1.5)
      .attr("d",d=>d3.symbol().type(shapeMap[d.shape]||d3.symbolCircle).size((bridgeIds.has(d.id)?nr(d)*1.5:nr(d))**2*3)());
    lkAll.attr("stroke-opacity",d=>{
      const s=d.source.id||d.source,t=d.target.id||d.target;
      return bridgeIds.has(s)&&bridgeIds.has(t)?0.6:0.04;
    });
  }

  // Position update helper
  function positionAll(){
    lkAll.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
    ndAll.attr("transform",d=>"translate("+(d.x||0)+","+(d.y||0)+")");
    updateLabels();
  }

  const activeNs = ns.filter(n=>n._active);
  if(useUMAP){
    // UMAP: no simulation — direct positioning
    sim.stop();
    // Ensure all nodes have UMAP coordinates set as x,y
    ns.forEach(n=>{ if(n.umapX!=null) { n.x=n.umapX; n.y=n.umapY; } });
    // Resolve link references (D3 needs source/target as objects)
    const nodeMap = {};
    ns.forEach(n=>{ nodeMap[n.id]=n; });
    ls.forEach(l=>{
      if(typeof l.source==="string") l.source=nodeMap[l.source]||l.source;
      if(typeof l.target==="string") l.target=nodeMap[l.target]||l.target;
    });
    positionAll();
  } else {
    // Force mode: run simulation with only active nodes
    activeNs.forEach(n=>{ n.fx=null; n.fy=null; });
    sim.nodes(activeNs);
    sim.force("link").links(ls);
    sim.on("tick", positionAll);
    sim.alpha(0.3).restart();
  }
}

function updateLabels(){
  const activeNs = nodesRaw.filter(n=>n._active);
  const showNum = SMALL || nodesRaw.length<=60 || currentZoom > 2;
  const showTitle = currentZoom > 4;
  if(!showNum){ labelG.selectAll("text").remove(); return; }
  const lbls = labelG.selectAll("text.node-label").data(activeNs, d=>d.id);
  lbls.exit().remove();
  const lblsE = lbls.enter().append("text").attr("class","node-label");
  lblsE.merge(lbls)
    .attr("x",d=>(d.x||0))
    .attr("y",d=>(d.y||0)+nr(d)+16).attr("text-anchor","middle")
    .text(d=>showTitle?(d.title?d.title.slice(0,25)+"…":d.num):d.num);
}

function showInfo(d){
  const nc = (NODECONNS[d.id]||[]);
  const infoCats = d.all_categories ? d.all_categories.join(" &middot; ") : d.category;
  let html = '<button id="info-close" title="Close" onclick="closeInfo()">&times;</button>';
  html += "<h3>"+esc(d.title)+"</h3>";
  html += '<div class="info-meta"><span style="color:'+d.color+'">\u25CF</span> '+esc(infoCats)+"<br>"+esc(d.num)+" &middot; "+d.year+" &middot; \uC810\uC218 "+(d.score||"-")+"/5 &middot; \uC5F0\uACB0 "+nc.length+"\uAC1C</div>";
  html += '<div class="info-essence">'+esc(d.essence)+"</div>";
  html += '<div class="info-actions">';
  html += '<a class="review-btn" id="info-review" href="papers/'+encodeURIComponent(d.id)+'/index.html">\u2192 \uB9AC\uBDF0 \uC77D\uAE30</a> ';
  html += '<a class="review-btn ask-btn" data-ask="'+esc('$wiki-query <\uC9C8\uBB38\uC744 \uC5EC\uAE30\uC5D0> (\uCC38\uACE0: wiki/papers/'+d.id+'/review.md)').replace(/"/g,'&quot;')+'">\uD83D\uDCAC Codex\uC5D0\uAC8C \uBB3C\uC5B4\uBCF4\uAE30</a><br>';
  if(egoId===d.id) html += '<a id="info-ego" onclick="clearEgo()">\u26D4 \uC774\uC6C3\uB9CC \uBCF4\uAE30 \uB044\uAE30</a>';
  else html += '<a id="info-ego" onclick="setEgo(\''+d.id+'\')">\uD83D\uDD0D \uC774\uC6C3\uB9CC \uBCF4\uAE30 (Ego)</a>';
  html += "</div><hr style=\"border:none;border-top:1px solid #333;margin:0.4rem 0\">";
  nc.slice(0,30).forEach(item=>{
    const o = nodesRaw.find(n=>n.id===item.o);
    const name = o?o.num+" \u00B7 "+o.title:item.o;
    const reasons = item.r.map(function(rr){
      const rel=rr[0], reason=rr[1];
      return '<div class="conn-reason"><span class="conn-rel" style="color:'+(relColors[rel]||'#ccc')+'">'+(relLabels[rel]||rel)+'</span> '+esc(reason)+'</div>';
    }).join('');
    html += '<div class="conn-item"><a class="conn-link" data-id="'+item.o+'">'+esc(name)+'</a>'+reasons+'</div>';
  });
  info.innerHTML = html;
  info.classList.add("open");
}
window.closeInfo = function(){ info.classList.remove("open"); };

function esc(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
window.setEgo = function(id){ egoId=id; render(); const d=nodesRaw.find(n=>n.id===id); if(d)showInfo(d); };
window.clearEgo = function(){ egoId=null; render(); closeInfo(); };
svg.on("click",()=>{ closeInfo(); if(egoId){egoId=null;render();} });
info.addEventListener("click",function(e){
  const link=e.target.closest(".conn-link");
  if(link){
    e.stopPropagation();
    const id=link.dataset.id;
    const n=nodesRaw.find(x=>x.id===id);
    if(n) showInfo(n);
  }
});
info.addEventListener("mouseover",function(e){
  const link=e.target.closest(".conn-link");
  if(link){
    const id=link.dataset.id;
    nodeG.selectAll("path.node").filter(d=>d.id===id).attr("filter","url(#glow)");
  }
});
info.addEventListener("mouseout",function(e){
  const link=e.target.closest(".conn-link");
  if(link) nodeG.selectAll("path.node").attr("filter",null);
});

// (Category filters handled by buildTree above)

// Relation filters
const rf = document.getElementById("rel-filters");
Object.keys(relColors).forEach(rel=>{
  const el = document.createElement("span");
  el.className="rel-toggle";
  el.style.borderColor=relColors[rel]; el.style.color=relColors[rel];
  el.textContent=relLabels[rel]||rel;
  el.onclick=()=>{
    if(activeRels.has(rel)){activeRels.delete(rel);el.classList.add("off");}
    else{activeRels.add(rel);el.classList.remove("off");}
    render();
  };
  rf.appendChild(el);
});

// Search
document.getElementById("search").addEventListener("input",function(){
  const q=this.value.toLowerCase().trim();
  const sc=document.getElementById("search-count");
  const go=ghostOp();
  if(!q){ nodeG.selectAll("path.node").attr("opacity",d=>d._active?1:go).attr("d",d=>d3.symbol().type(shapeMap[d.shape]||d3.symbolCircle).size(nr(d)*nr(d)*3)()); linkG.selectAll("line").attr("stroke-opacity",0.45); nodeG.selectAll("path.node").classed("hit",false); sc.textContent=""; return; }
  let c=0;
  nodeG.selectAll("path.node").attr("opacity",d=>{
    if(!d._active) return go;
    const m=hit(d,q);
    if(m)c++; return m?1:go;
  }).attr("d",d=>{
    const m=d._active&&hit(d,q);
    const sz=m?nr(d)*1.5:nr(d);
    return d3.symbol().type(shapeMap[d.shape]||d3.symbolCircle).size(sz*sz*3)();
  });
  linkG.selectAll("line").attr("stroke-opacity",0.04);
  nodeG.selectAll("path.node").classed("hit",d=>d._active&&hit(d,q));
  sc.textContent=c+"\uD3B8 \uCC3E\uC74C";
});

// Hierarchical tree view + color toggle
const activeSubs = new Set(); // active sub-categories
function buildTree(){
  const tree=document.getElementById("cat-tree");
  tree.innerHTML="";
  activeCats.clear(); activeSubs.clear();
  Object.keys(catColors).forEach(cat=>activeCats.add(cat));
  Object.keys(subColors).forEach(sub=>activeSubs.add(sub));

  Object.keys(catColors).forEach(cat=>{
    const item=document.createElement("div");
    item.className="cat-tree-item";

    const header=document.createElement("div");
    header.className="cat-tree-header";
    const arrow=document.createElement("span");
    arrow.className="cat-tree-arrow"; arrow.textContent="\u25B6";
    const dot=document.createElement("span");
    dot.className="cat-dot"; dot.style.background=catColors[cat];
    const txt=document.createTextNode(cat);
    const cnt=document.createElement("span");
    cnt.className="cat-count"; cnt.textContent=catCounts[cat]||0;
    header.appendChild(arrow); header.appendChild(dot); header.appendChild(txt); header.appendChild(cnt);

    const subsDiv=document.createElement("div");
    subsDiv.className="cat-tree-subs";

    const subs=catSubs[cat]||[];
    subs.forEach(sub=>{
      activeSubs.add(sub);
      const sel=document.createElement("div");
      sel.className="sub-toggle-item";
      const sdot=document.createElement("span");
      sdot.className="cat-dot"; sdot.style.background=subColors[sub]||"#999";
      const stxt=document.createTextNode(sub);
      const scnt=document.createElement("span");
      scnt.className="cat-count"; scnt.textContent=subCounts[sub]||0;
      sel.appendChild(sdot); sel.appendChild(stxt); sel.appendChild(scnt);
      sel.onclick=(e)=>{
        e.stopPropagation();
        if(activeSubs.has(sub)){activeSubs.delete(sub);sel.classList.add("off");}
        else{activeSubs.add(sub);sel.classList.remove("off");}
        render();
      };
      subsDiv.appendChild(sel);
    });

    // Click header: toggle category on/off
    header.onclick=(e)=>{
      if(e.shiftKey){
        // Shift+click: expand/collapse subs
        subsDiv.classList.toggle("open");
        arrow.textContent=subsDiv.classList.contains("open")?"\u25BC":"\u25B6";
      } else {
        if(activeCats.has(cat)){
          activeCats.delete(cat);
          header.classList.add("off");
          subs.forEach(s=>activeSubs.delete(s));
          subsDiv.querySelectorAll(".sub-toggle-item").forEach(s=>s.classList.add("off"));
        } else {
          activeCats.add(cat);
          header.classList.remove("off");
          subs.forEach(s=>activeSubs.add(s));
          subsDiv.querySelectorAll(".sub-toggle-item").forEach(s=>s.classList.remove("off"));
        }
        render();
      }
    };

    item.appendChild(header);
    item.appendChild(subsDiv);
    tree.appendChild(item);
  });
}
buildTree();

document.getElementById("sel-all").onclick=function(){
  Object.keys(catColors).forEach(c=>activeCats.add(c));
  Object.keys(subColors).forEach(s=>activeSubs.add(s));
  document.querySelectorAll(".cat-tree-header").forEach(h=>h.classList.remove("off"));
  document.querySelectorAll(".sub-toggle-item").forEach(s=>s.classList.remove("off"));
  render();
};
document.getElementById("sel-none").onclick=function(){
  activeCats.clear(); activeSubs.clear();
  document.querySelectorAll(".cat-tree-header").forEach(h=>h.classList.add("off"));
  document.querySelectorAll(".sub-toggle-item").forEach(s=>s.classList.add("off"));
  render();
};

document.getElementById("colorby-cat").onclick=function(){
  colorBy="cat";
  this.classList.add("active");
  document.getElementById("colorby-sub").classList.remove("active");
  render();
};
document.getElementById("colorby-sub").onclick=function(){
  colorBy="sub";
  this.classList.add("active");
  document.getElementById("colorby-cat").classList.remove("active");
  render();
};

// Year slider
const ymSlider=document.getElementById("year-min"), yxSlider=document.getElementById("year-max"), yLabel=document.getElementById("year-label");
function updateYear(){ yearMin=parseInt(ymSlider.value); yearMax=parseInt(yxSlider.value); if(yearMin>yearMax){const t=yearMin;yearMin=yearMax;yearMax=t;} yLabel.textContent=yearMin+" \u2014 "+yearMax; render(); }
ymSlider.addEventListener("input",updateYear);
yxSlider.addEventListener("input",updateYear);

// Highlight buttons
document.getElementById("hl-hub").onclick=function(){
  hlMode=hlMode==="hub"?null:"hub";
  document.querySelectorAll(".hl-btn").forEach(b=>b.classList.remove("active"));
  if(hlMode) this.classList.add("active");
  render();
};
document.getElementById("hl-bridge").onclick=function(){
  hlMode=hlMode==="bridge"?null:"bridge";
  document.querySelectorAll(".hl-btn").forEach(b=>b.classList.remove("active"));
  if(hlMode) this.classList.add("active");
  render();
};
document.getElementById("hl-reset").onclick=function(){
  hlMode=null; egoId=null;
  document.querySelectorAll(".hl-btn").forEach(b=>b.classList.remove("active"));
  info.classList.remove("open");
  render();
};

// Reset View: restore zoom/pan to the initial (identity) transform so the
// graph snaps back to the canonical layout regardless of how the user has
// zoomed, dragged or scrolled around. Covers both 2D SVG and 3D Three.js:
//   * 2D — animate svg zoom transform back to d3.zoomIdentity
//   * 3D — OrbitControls.reset() restores the camera position/target/zoom
//          captured when the controls were instantiated (position 0,0,160;
//          target 0,0,0). Safe to call even when not currently in 3D mode,
//          but guarded so we do not error before 3D is ever initialized.
document.getElementById("view-reset").onclick=function(){
  svg.transition().duration(500).call(zoomBehavior.transform, d3.zoomIdentity);
};

// Force controls
document.getElementById("f-charge").addEventListener("input",function(){
  sim.force("charge").strength(parseInt(this.value));
  sim.alpha(0.3).restart();
});
document.getElementById("f-dist").addEventListener("input",function(){
  sim.force("link").distance(parseInt(this.value));
  sim.alpha(0.3).restart();
});
document.getElementById("f-str").addEventListener("input",function(){
  sim.force("link").strength(parseInt(this.value)/100);
  sim.alpha(0.3).restart();
});
document.getElementById("f-grav").addEventListener("input",function(){
  const v=parseInt(this.value)/100;
  sim.force("x").strength(v);
  sim.force("y").strength(v);
  sim.alpha(0.3).restart();
});

// Theme toggle
document.getElementById("theme-dark").onclick=function(){
  document.body.classList.remove("light");
  this.classList.add("active");
  document.getElementById("theme-light").classList.remove("active");
  nodeG.selectAll("path.node").attr("stroke",d=>d.multi?"#666":getComputedStyle(document.documentElement).getPropertyValue('--node-stroke'));
  render();
};
document.getElementById("theme-light").onclick=function(){
  document.body.classList.add("light");
  this.classList.add("active");
  document.getElementById("theme-dark").classList.remove("active");
  nodeG.selectAll("path.node").attr("stroke",d=>d.multi?"#666":getComputedStyle(document.documentElement).getPropertyValue('--node-stroke'));
  render();
};

// Controls collapse/expand
const ctrlPanel = document.getElementById("controls");
const ctrlToggle = document.getElementById("controls-toggle");
ctrlToggle.addEventListener("click",function(e){
  e.stopPropagation();
  ctrlPanel.classList.toggle("collapsed");
  ctrlToggle.innerHTML = ctrlPanel.classList.contains("collapsed")?"&raquo;":"&laquo;";
});

// Info-hint / shortcuts popup
const shortcutsPopup = document.getElementById("shortcuts-popup");
document.getElementById("info-hint-btn").addEventListener("click",function(e){
  e.stopPropagation();
  shortcutsPopup.classList.toggle("open");
});
document.addEventListener("click",function(){ shortcutsPopup.classList.remove("open"); });
shortcutsPopup.addEventListener("click",function(e){ e.stopPropagation(); });

// Keyboard shortcuts
document.addEventListener("keydown",function(e){
  const tag = document.activeElement.tagName;
  if(tag==="INPUT"||tag==="TEXTAREA") {
    if(e.key==="Escape") document.activeElement.blur();
    return;
  }
  if(e.key==="Escape") {
    closeInfo();
    if(egoId){ egoId=null; render(); }
    shortcutsPopup.classList.remove("open");
  } else if(e.key==="/") {
    e.preventDefault();
    document.getElementById("search").focus();
  } else if(e.key==="?") {
    shortcutsPopup.classList.toggle("open");
  }
});


render();
})();
