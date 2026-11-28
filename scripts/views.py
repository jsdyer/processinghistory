from collections import defaultdict
import csv
from datetime import datetime
from email.utils import format_datetime
from html import escape
import json
from pathlib import Path
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from search_metadata import add_search_metadata
from country_guides import build_country, directory
from collect import OFFICIAL,PROGRAMS,read_json,write_json

def option(k,v,selected):
    return f'<option value="{escape(k,quote=True)}"'+(' selected' if selected else '')+'>'+escape(v)+'</option>'

def describe(s):
    return s['label'] if s['label'] is not None else 'No row in this capture'

def export_series(stage,tool,program,code,name,rows):
    folder=stage/'series'/program
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/(code+'.csv')).open('w',newline='') as out:
        w=csv.writer(out);w.writerow(['application','country_code','source_edition','observed_at_utc','published_value','evidence_url','source_sha256'])
        w.writerows([program,code,r['issued'],r['observed'],describe(r),r['evidence'],r['hash']] for r in rows)
    label=PROGRAMS[program]+' · '+name
    base='https://coolcode.ca'+tool['url']
    link=base+'?'+urlencode({'program':program,'country':code})
    root=ET.Element('rss',version='2.0');channel=ET.SubElement(root,'channel')
    for tag,value in [('title',label+' | IRCC estimate changes'),('link',link),('description','Changes in published IRCC figures observed by CoolCode.')]:
        ET.SubElement(channel,tag).text=value
    changes=[r for i,r in enumerate(rows) if i==0 or rows[i-1]['label']!=r['label']]
    for r in reversed(changes[-12:]):
        item=ET.SubElement(channel,'item')
        for tag,value in [('title',label+' · '+describe(r)),('link',r['evidence']),('description','Observed '+r['observed']+'. IRCC edition '+(r['issued'] or 'unavailable')+'.'),('pubDate',format_datetime(datetime.fromisoformat(r['observed'].replace('Z','+00:00'))))]:
            ET.SubElement(item,tag).text=value
        ET.SubElement(item,'guid',isPermaLink='false').text=f'{program}/{code}/{r["observed"]}'
    ET.ElementTree(root).write(folder/(code+'.rss'),encoding='utf-8',xml_declaration=True)

def render_views(stage,template,tool):
    raw=stage/'data';index=read_json(raw/'index.json',None)
    if not index:raise ValueError('No verified processing-time captures')
    countries=read_json(raw/'countries.json',{})
    snapshots=[]
    for path in sorted((raw/'history').glob('*.json')):snapshots.extend(read_json(path,[]))
    snapshots.sort(key=lambda s:s['observedAt'])
    if len(snapshots)!=index['captureCount']:raise ValueError('Capture index disagrees with history')
    examples=read_json(stage/'examples.json',[])
    catalog=defaultdict(dict)
    # Store provenance once per capture and values once per country. One lookup
    # downloads just the selected country and the shared evidence list.
    provenance=[{'observed':s['observedAt'],'evidence':s['evidence'],'hash':s['sha256'],'issued':{k:r['issued'] for k,r in s['programs'].items()}} for s in snapshots]
    write_json(stage/'series/provenance.json',provenance)
    used=sorted(set.union(*(set(s['countries']) for s in snapshots)))
    for s in snapshots:
        s['positions']={c:i for i,c in enumerate(s['countries'])}
    profiles = []
    for code in used:
        country_rows = {}
        compact={}
        for program in PROGRAMS:
            rows=[]
            values=[]
            for i,s in enumerate(snapshots):
                pos=s['positions'].get(code);record=s['programs'][program]
                value=s['dictionary'][record['values'][pos]] if pos is not None else None
                p=provenance[i]
                values.append(value)
                rows.append({'label':value,'issued':p['issued'][program],'observed':p['observed'],'evidence':p['evidence'],'hash':p['hash']})
            compact[program]=values
            country_rows[program] = rows
            export_series(stage,tool,program,code,countries.get(code,code),rows)
            if any(e['program']==program and e['country']==code for e in examples):
                catalog[program][code]=rows
        write_json(stage/'series'/(code+'.json'),compact)
        profile = build_country(stage, tool, code, countries.get(code, code), country_rows, index['checkedAt'])
        if profile:
            profiles.append(profile)
    directory(stage, tool, profiles, index['checkedAt'])
    profile_codes = {p['code'] for p in profiles}
    for slug,e in [('',examples[0]),*[(e['slug'],e) for e in examples]]:
        base='../' if slug else './';folder=stage/slug;folder.mkdir(exist_ok=True)
        program,code=e['program'],e['country'];rows=catalog[program][code];latest=rows[-1]
        title=e['title'] if slug else tool['title']
        description=(f'Follow IRCC’s published {PROGRAMS[program].lower()} estimates for {countries.get(code,code)} over time, with original evidence and a CSV download.' if slug else tool['description'])
        view=dict(tool,title=title,description=description,url=tool['url']+(slug+'/' if slug else ''))
        p=template.replace('ASSET_BASE',base)
        if slug:p=p.replace(escape(tool['title']),escape(title)).replace(escape(tool['description']),escape(description))
        country_options=''.join(option(c,countries.get(c,c),c==code) for c in sorted(used,key=lambda c:countries.get(c,c)))
        program_options=''.join(option(k,v,k==program) for k,v in PROGRAMS.items())
        top=''.join(f'<tr><td>{r["observed"][:10]}</td><td>{escape(r["issued"] or "Unavailable")}</td><td>{escape(describe(r))}</td><td><a href="{escape(r["evidence"],quote=True)}">Source</a></td></tr>' for r in reversed(rows[-6:]))
        fields={'APP_TITLE':escape(tool['title'],quote=True),'APP_DESCRIPTION':escape(tool['description'],quote=True),'START_PROGRAM':program,'START_COUNTRY':code,'COUNTRY_OPTIONS':country_options,'PROGRAM_OPTIONS':program_options,'HEADLINE':escape(describe(latest)),'ASOF':escape(latest['issued'] or 'date unavailable'),'CONTEXT':escape(PROGRAMS[program]+' · '+countries[code]),'INITIAL_ROWS':top,'FIRST_DATE':provenance[0]['observed'][:10],'OBSERVATIONS':str(index['captureCount']),'CHECKED':escape(index['checkedAt']),'CSV_PATH':base+'series/'+program+'/'+code+'.csv','RSS_PATH':base+'series/'+program+'/'+code+'.rss','PRESET_LINKS':''.join(f'<a data-program="{escape(example["program"],quote=True)}" data-country="{escape(example["country"],quote=True)}" href="{base}{example["slug"]}/">{escape(example["title"])}</a>' for example in examples)}
        fields['PROFILE_CODES'] = ' '.join(sorted(profile_codes))
        fields['PROFILE_PATH'] = base + ('records/' + code.lower() + '/' if code in profile_codes else 'records/')
        fields['PROFILE_LABEL'] = escape('Compare all four application types for ' + countries[code] if code in profile_codes else 'Browse country comparisons')
        for token,value in fields.items():p=p.replace(token,value)
        (folder/'index.html').write_text(add_search_metadata(p,view))
