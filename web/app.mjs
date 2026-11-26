import {observations} from './model.mjs';
const $=id=>document.getElementById(id), base=new URL('.',import.meta.url);
async function read(path){const r=await fetch(new URL(path,base));if(!r.ok)throw new Error('Could not load this history.');return r.json();}
const provenance=read('series/provenance.json');
let seq=0,rows=[],visible=12;
function drawTable(){
  $('records').replaceChildren(...rows.slice(-visible).reverse().map(r=>{
    const tr=document.createElement('tr');
    for(const s of [r.date,r.issued,r.label]){const td=document.createElement('td');td.textContent=s;tr.append(td);}
    const td=document.createElement('td'),a=document.createElement('a');a.href=r.source;a.textContent='Source';td.append(a);tr.append(td);return tr;
  }));$('more').hidden=rows.length<=visible;
}
function plot(rows) {
  const numeric=rows.filter(r=>r.day!==null);$('plot').replaceChildren();if(numeric.length<2)return;
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
  const width=720,height=135,left=43,margin=12,dates=rows.map(r=>Date.parse(r.date)),first=dates[0],span=dates.at(-1)-first||1,peak=Math.max(...numeric.map(r=>r.day),1);
  svg.setAttribute('viewBox','0 0 '+width+' '+height);svg.setAttribute('role','img');svg.setAttribute('aria-label','Historical observations in days. Dots mark available dates. Exact values are in the table.');svg.style.width='100%';
  function add(tag,attrs,label){const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));if(label)el.textContent=label;svg.append(el);return el;}
  for(const tick of [0,peak]){const y=height-margin-(height-2*margin)*tick/peak;add('line',{x1:left,x2:width-margin,y1:y,y2:y,stroke:'#c6d0ca'});add('text',{x:2,y:tick?y+6:y,'font-size':12,fill:'#233e3b'},tick+'d');}
  for(const r of numeric)add('circle',{cx:left+(width-left-margin)*(Date.parse(r.date)-first)/span,cy:height-margin-(height-2*margin)*r.day/peak,r:2,fill:'#1c6e60'});
  $('plot').append(svg);
}
async function change(updateAddress) {
  const ticket=++seq,program=$('program').value,country=$('country').value;
  const path='series/'+program+'/'+country,params=new URLSearchParams({program,country});
  $('status').textContent='Loading selected history…';$('more').hidden=true;
  try{
    const [p,data]=await Promise.all([provenance,read('series/'+country+'.json')]);
    if(ticket!==seq)return;
    rows=observations(data[program],p,program);visible=12;
    const latest=rows.at(-1);$('estimate').textContent=latest.label;$('context').textContent=$('program').selectedOptions[0].text+' · '+$('country').selectedOptions[0].text;
    $('issued').textContent='IRCC source edition '+latest.issued+' · observed '+latest.date+' UTC';
    $('csv').href=new URL(path+'.csv',base);$('rss').href=new URL(path+'.rss',base);
    const url=new URL(base);url.search=params;$('share').href=url;
    if(updateAddress)history.replaceState(null,'',url);
    drawTable();plot(rows);$('status').textContent='';
  }catch{if(ticket===seq){$('status').textContent='The selected history could not be loaded. The figures below still show the last successful selection.';}}
}
const query=new URLSearchParams(location.search);
for(const key of ['program','country'])if([...$(key).options].some(opt=>opt.value===query.get(key)))$(key).value=query.get(key);
$('search').onchange=()=>change(true);$('more').onclick=()=>{visible+=50;drawTable();};
change(false);
