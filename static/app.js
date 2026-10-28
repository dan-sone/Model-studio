const $ = id => document.getElementById(id);
let state = null, busy = false;
const names = {activity:'Aktivitet', decision:'Beslut', role:'Roll', system:'System', flow:'Flöde', supports:'Stödjer', responsible_for:'Ansvarar för'};
function status(text, error=false) { $('status').textContent=text; $('status').classList.toggle('error',error); }
function controls() { $('send').disabled=busy || !state?.configured; $('undo').disabled=busy || !state?.canUndo; $('reload').disabled=busy; }
async function api(path, data) {
  const response=await fetch(path, data ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)} : {});
  const result=await response.json();
  if (!response.ok) { if(response.status===401) $('login').hidden=false; throw Error(result.error || 'Begäran misslyckades.'); }
  return result;
}
function render(next) {
  state=next; $('login').hidden=true; $('version').textContent=`Version ${state.version}`;
  $('messages').replaceChildren();
  for(const m of state.conversation) {
    const item=document.createElement('div'); item.className=`message ${m.role}`;
    const who=document.createElement('span'); who.className='speaker'; who.textContent=m.role==='user'?'DU':'MODEL STUDIO';
    item.append(who,document.createTextNode(m.content)); $('messages').append(item);
  }
  $('messages').scrollTop=$('messages').scrollHeight;
  $('history').replaceChildren();
  for(const h of state.history) {const li=document.createElement('li');li.textContent=`Version ${h.version} · ${h.summary}`;$('history').append(li);}
  $('modeltext').replaceChildren();
  const labels=new Map(state.model.nodes.map(n=>[n.id,n.label]));
  for(const n of state.model.nodes) {const p=document.createElement('p');p.textContent=`${names[n.type]}: ${n.label} (${n.id}) · ${n.knowledge==='verified'?'Verifierat: '+n.source:'Förslag'}`;$('modeltext').append(p);}
  for(const r of state.model.relations) {const p=document.createElement('p');p.textContent=`${labels.get(r.source)} → ${labels.get(r.target)}: ${names[r.type]} ${r.label} · ${r.knowledge==='verified'?'Verifierat':'Förslag'}`;$('modeltext').append(p);}
  draw(state.model);
  status(state.configured?'AI är konfigurerad på servern.':'AI är inte konfigurerad. Ange OPENAI_API_KEY och OPENAI_MODEL på servern.',!state.configured);
  controls();
}
// Deterministic layered layout. Flow cycles use strongly connected components.
export function layout(model) {
  const process=model.nodes.filter(n=>['activity','decision'].includes(n.type));
  const adjacent=new Map(process.map(n=>[n.id,[]]));
  for(const r of model.relations.filter(r=>r.type==='flow')) adjacent.get(r.source)?.push(r.target);
  let serial=0; const index=new Map(), low=new Map(), stack=[], on=new Set(), components=[];
  function visit(v) {
    index.set(v,serial);low.set(v,serial++);stack.push(v);on.add(v);
    for(const w of adjacent.get(v)||[]) {if(!index.has(w)){visit(w);low.set(v,Math.min(low.get(v),low.get(w)));}else if(on.has(w))low.set(v,Math.min(low.get(v),index.get(w)));}
    if(low.get(v)===index.get(v)){const group=[];let w;do{w=stack.pop();on.delete(w);group.push(w);}while(w!==v);components.push(group);}
  }
  for(const n of process)if(!index.has(n.id))visit(n.id);
  const groupOf=new Map();components.forEach((g,i)=>g.forEach(id=>groupOf.set(id,i)));
  const levels=components.map(()=>0);
  for(let i=0;i<components.length;i++)for(const [a,list] of adjacent)for(const b of list)if(groupOf.get(a)!==groupOf.get(b))levels[groupOf.get(b)]=Math.max(levels[groupOf.get(b)],levels[groupOf.get(a)]+1);
  const rows=new Map(), pos=new Map();
  for(const n of process){const level=levels[groupOf.get(n.id)];const row=rows.get(level)||0;rows.set(level,row+1);pos.set(n.id,{x:35+level*245,y:160+row*155});}
  let role=0,system=0;
  const bottom=200+Math.max(1,...rows.values())*155;
  for(const n of model.nodes){if(n.type==='role')pos.set(n.id,{x:35+role++*245,y:35});if(n.type==='system')pos.set(n.id,{x:35+system++*245,y:bottom});}
  return pos;
}
const NS='http://www.w3.org/2000/svg';
function svgElement(tag,attrs={},text) {const el=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))el.setAttribute(k,v);if(text!==undefined)el.textContent=text;return el;}
function draw(model) {
  if(!model.nodes.length){$('diagram').replaceChildren();const p=document.createElement('p');p.className='empty';p.textContent='Beskriv en process i dialogen för att skapa din första modell.';$('diagram').append(p);return;}
  const pos=layout(model),width=Math.max(680,...[...pos.values()].map(p=>p.x+220)),height=Math.max(400,...[...pos.values()].map(p=>p.y+115));
  const svg=svgElement('svg',{width,height,viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':`Modell med ${model.nodes.length} objekt och ${model.relations.length} relationer`});
  const defs=svgElement('defs'),marker=svgElement('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});marker.append(svgElement('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#617b70'}));defs.append(marker);svg.append(defs);
  const backwards=new Map();
  for(const r of model.relations){const a=pos.get(r.source),b=pos.get(r.target);let d,lx,ly;
    if(r.type==='flow' && b.x>a.x){d=`M ${a.x+190} ${a.y+42} C ${a.x+218} ${a.y+42}, ${b.x-28} ${b.y+42}, ${b.x} ${b.y+42}`;lx=(a.x+190+b.x)/2;ly=(a.y+b.y)/2+30;}
    else if(r.type==='flow'){const key=a.x;const lane=backwards.get(key)||0;backwards.set(key,lane+1);const via=Math.max(a.x,b.x)+210+lane*8;d=`M ${a.x+190} ${a.y+42} C ${via} ${a.y+42}, ${via} ${b.y+100}, ${b.x+95} ${b.y+84}`;lx=via-25;ly=(a.y+b.y)/2+80;}
    else{const ay=a.y+42,by=b.y-20;const gutter=15;d=`M ${a.x} ${ay} L ${gutter} ${ay} L ${gutter} ${by} L ${b.x+95} ${by} L ${b.x+95} ${b.y}`;lx=b.x+100;ly=by-7;}
    svg.append(svgElement('path',{d,class:`edge ${r.type}`,'marker-end':'url(#arrow)','stroke-dasharray':r.type==='flow'?'none':'5 4'}));
    svg.append(svgElement('text',{x:lx,y:ly,class:'branch-label'},r.label||names[r.type]));
  }
  const colors={activity:'#e7efe8',decision:'#fff1cc',role:'#e9eef8',system:'#ede8f6'};
  for(const n of model.nodes){const p=pos.get(n.id),g=svgElement('g');g.append(svgElement('title',{},`${n.label} · ${names[n.type]} · ${n.knowledge==='proposed'?'Förslag':n.source}`));
    if(n.type==='decision')g.append(svgElement('polygon',{points:`${p.x+95},${p.y} ${p.x+190},${p.y+42} ${p.x+95},${p.y+84} ${p.x},${p.y+42}`,fill:colors[n.type],stroke:'#b4bfae'}));
    else g.append(svgElement('rect',{x:p.x,y:p.y,width:190,height:84,rx:n.type==='system'?3:14,fill:colors[n.type],stroke:'#b4c5b9'}));
    const text=svgElement('text',{x:p.x+95,y:p.y+28,'text-anchor':'middle'});
    const words=n.label.match(/.{1,23}(?:\s|$)|.{1,23}/g)||[n.label];
    words.slice(0,2).forEach((word,i)=>text.append(svgElement('tspan',{x:p.x+95,dy:i?17:0},word.trim())));
    g.append(text,svgElement('text',{x:p.x+95,y:p.y+69,'text-anchor':'middle','font-size':10},`${names[n.type]} · ${n.knowledge==='proposed'?'förslag':'verifierat'}`));svg.append(g);
  }
  $('diagram').replaceChildren(svg);
}
async function load(){try{render(await api('/api/state'));}catch(e){status(e.message,true);}finally{controls();}}
$('login').addEventListener('submit',async e=>{e.preventDefault();try{await api('/api/login',{password:$('password').value});$('password').value='';await load();}catch(e){status(e.message,true);}});
async function mutate(path,message){busy=true;controls();status(path==='/api/chat'?'AI arbetar med modellen…':'Ångrar ändringen…');try{const next=await api(path,{message,version:state.version,revision:state.revision,requestId:crypto.randomUUID()});render(next);if(path==='/api/chat')$('message').value='';}catch(e){status(e.message+' Texten finns kvar för ett nytt försök. Använd Läs in om modellen har ändrats.',true);}finally{busy=false;controls();}}
$('chat').addEventListener('submit',e=>{e.preventDefault();if(!busy&&state?.configured)mutate('/api/chat',$('message').value);});
$('undo').addEventListener('click',()=>mutate('/api/undo'));
$('reload').addEventListener('click',load);
controls();load();
