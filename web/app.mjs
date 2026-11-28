import {observations} from './model.mjs';
const $=id=>document.getElementById(id), base=new URL('.',import.meta.url);
async function read(path){const r=await fetch(new URL(path,base));if(!r.ok)throw new Error('Could not load this history.');return r.json();}
const profileCodes = new Set($('main').dataset.countryProfiles.split(' '));
$('all-profiles').href = new URL('records/', base);
function showCountryProfile(country) {
  const a = $('country-profile');
  a.hidden = !profileCodes.has(country);
  if (!a.hidden) {
    a.href = new URL('records/' + country.toLowerCase() + '/', base);
    a.textContent = 'Compare all four application types for ' + $('country').selectedOptions[0].text;
  }
}
const cache = new Map();
function historyData(path) {
  if (!cache.has(path)) {
    cache.set(path, read(path).catch(error => {
      cache.delete(path);
      throw error;
    }));
  }
  return cache.get(path);
}
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
const programNames = {
  'visitor-outside-canada': 'Canada Visitor Visa Processing Time',
  supervisa: 'Canada Super Visa Processing Time',
  study: 'Canada Study Permit Processing Time',
  work: 'Canada Work Permit Processing Time',
};
const presets = [...$('presets').querySelectorAll('a')].map(link => {
  // Resolve once while the document still has its original published path.
  const url = new URL(link.getAttribute('href'), location.href);
  link.href = url.href;
  return {program: link.dataset.program, country: link.dataset.country, title: link.textContent, url};
});
const canonicalLink = document.querySelector('link[rel="canonical"]');
const publicBase = canonicalLink ? new URL(location.pathname === base.pathname ? '.' : '..', canonicalLink.href) : null;
const initial = {program: $('program').value, country: $('country').value};
let shown = initial;
function selectionFromAddress() {
  const address = new URL(location.href);
  const preset = presets.find(p => p.url.pathname === address.pathname) || presets[0];
  for (const key of ['program', 'country']) {
    const value = address.searchParams.get(key);
    $(key).value = [...$(key).options].some(option => option.value === value) ? value : preset[key];
  }
}
function describeSelection(program, country, rootLanding) {
  const preset = presets.find(p => p.program === program && p.country === country);
  const countryName = $('country').selectedOptions[0].text;
  const programName = $('program').selectedOptions[0].text;
  const context = programName + ' · ' + countryName;
  const title = rootLanding ? $('main').dataset.title :
    (preset?.title || (programNames[program] || programName) + ' · ' + countryName);
  const description = rootLanding ? $('main').dataset.description :
    'Follow IRCC’s published ' + programName.toLowerCase() + ' estimates for ' +
    countryName + ' over time, with original evidence and a CSV download.';
  const share = new URL(preset?.url || base);
  if (!preset) share.search = new URLSearchParams({program, country});
  return {context, title, description, share, canonical: rootLanding ? base : (preset?.url || base)};
}
function renderHeading({title, description, canonical, context}) {
  $('heading').textContent = title;
  $('lead').textContent = description;
  document.title = title + ' · CoolCode';
  $('context').textContent = context;
  $('history-title').textContent = 'Recorded history · ' + context;
  document.querySelector('meta[name="description"]').content = description;
  document.querySelector('meta[property="og:title"]').content = document.title;
  document.querySelector('meta[property="og:description"]').content = description;
  if (publicBase) {
    const canonicalURL = new URL(canonical.pathname.slice(base.pathname.length), publicBase);
    canonicalLink.href = canonicalURL;
    document.querySelector('meta[property="og:url"]').content = canonicalURL.href;
    const schema = document.querySelector('script[type="application/ld+json"]');
    const graph = JSON.parse(schema.textContent);
    const app = graph['@graph'][0];
    Object.assign(app, {name:title, description, url:canonicalURL.href, '@id':canonicalURL.href+'#application'});
    schema.textContent = JSON.stringify(graph);
  }
}
async function change(pushAddress = false) {
  const ticket = ++seq, program = $('program').value, country = $('country').value;
  const rootLanding = !pushAddress && location.pathname === base.pathname &&
    !['program','country'].some(key => new URLSearchParams(location.search).has(key));
  const view = describeSelection(program, country, rootLanding);
  renderHeading(view);
  showCountryProfile(country);
  $('share').href = view.share;
  if (pushAddress && location.href !== view.share.href) history.pushState(null, '', view.share);
  const path = 'series/' + program + '/' + country;
  $('csv').href = new URL(path + '.csv',base);
  $('rss').href = new URL(path + '.rss',base);
  $('retry').hidden = true;
  $('more').hidden = true;
  $('status').textContent = 'Loading history for ' + view.context + '…';
  $('result').setAttribute('aria-busy', 'true');
  if (shown?.program !== program || shown?.country !== country) {
    shown = null;
    rows = [];
    $('estimate').textContent = 'Loading…';
    $('issued').textContent = '';
    $('records').replaceChildren();
    $('plot').replaceChildren();
  }
  try {
    const [provenance, data] = await Promise.all([
      historyData('series/provenance.json'), historyData('series/' + country + '.json')
    ]);
    if (ticket !== seq) return;
    rows = observations(data[program], provenance, program);
    const latest = rows.at(-1);
    $('estimate').textContent = latest.label;
    $('issued').textContent = 'IRCC source edition ' + latest.issued + ' · observed ' + latest.date + ' UTC';
    visible = 12;
    shown = {program, country};
    drawTable();
    plot(rows);
    $('status').textContent = '';
  } catch {
    if (ticket !== seq) return;
    if (!shown) $('estimate').textContent = 'History unavailable';
    $('status').textContent = 'Could not load the full history for ' + view.context + '.';
    $('retry').hidden = false;
  } finally {
    if (ticket === seq) $('result').setAttribute('aria-busy', 'false');
  }
}
for (const selector of [$('program'), $('country')]) {
  selector.addEventListener('change', () => change(true));
}
addEventListener('popstate', () => { selectionFromAddress(); change(); });
$('more').onclick = () => { visible += 50; drawTable(); };
$('retry').onclick = () => change();
selectionFromAddress();
change();
