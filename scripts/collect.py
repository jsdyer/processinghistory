"""Validate and store observations of IRCC's country-based processing time feed."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'web/data'
OFFICIAL = 'https://www.canada.ca/content/dam/ircc/documents/json/data-ptime-en.json'
COUNTRIES = 'https://www.canada.ca/content/dam/ircc/documents/json/data-country-name-en.json'
PROGRAMS = {'visitor-outside-canada':'Visitor visa from outside Canada', 'supervisa':'Super visa', 'study':'Study permit', 'work':'Work permit'}

def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    tmp.replace(path)

def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default

def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'CoolCode-ProcessingHistory/1.0 (+https://coolcode.ca/processinghistory/)'}),timeout=35) as response:
        body=response.read(2_000_001)
        if len(body)>2_000_000: raise ValueError('Unexpectedly large IRCC source')
        return body

def source_date(value):
    return datetime.strptime(value.strip(),'%B %d, %Y').date().isoformat()

def pack(raw, captured, evidence):
    payload=json.loads(raw.decode('utf-8-sig'))
    country_codes=sorted({c for key in PROGRAMS for c in payload[key] if re.fullmatch('[A-Z]{2}',c)})
    if len(country_codes)<100:raise ValueError('Unexpectedly sparse country coverage')
    dictionary=[None]
    value_ids={None:0}
    records={}
    for key in PROGRAMS:
        row=payload[key]
        updated=source_date(row['lastupdated']) if row.get('lastupdated','').strip() else None
        if updated and updated>captured[:10]:raise ValueError('Source date later than observation')
        values=[]
        for code in country_codes:
            value=row.get(code)
            if value is not None and (not isinstance(value,str) or len(value)>160): raise ValueError(f'Unexpected estimate in {key}/{code}')
            if value not in value_ids:
                value_ids[value]=len(dictionary)
                dictionary.append(value)
            values.append(value_ids[value])
        if sum(isinstance(v,str) and re.search(r'\d',v) is not None for v in row.values())<10:raise ValueError(f'No usable estimates for {key}')
        records[key]={'issued':updated,'values':values}
    return {'observedAt':captured,'evidence':evidence,'sha256':sha256(raw).hexdigest(),'countries':country_codes,'dictionary':dictionary,'programs':records}

def retain(data, snap):
    day=snap['observedAt'][:10]
    path=data/'history'/(day[:7]+'.json')
    observations=read_json(path,[])
    # Store new editions and same-edition corrections. A fresh fetch is recorded
    # in index.json even when the normalized data has not changed.
    if any(o['sha256']==snap['sha256'] for o in observations): return False
    if any(o['observedAt']==snap['observedAt'] for o in observations):
        raise ValueError('Different source data for an existing capture timestamp')
    observations.append(snap)
    write_json(path,sorted(observations,key=lambda r:r['observedAt']))
    return True

def update(data=DATA):
    now=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    raw=fetch(OFFICIAL)
    snap=pack(raw,now,OFFICIAL)
    names=json.loads(fetch(COUNTRIES).decode('utf-8-sig'))['country-name']
    if not isinstance(names,dict) or not all(isinstance(n,str) for n in names.values()) or len(names)<100:raise ValueError('Incomplete country name lookup')
    # The feed includes Greenland (GL), absent from IRCC's separate label list.
    names.setdefault('GL','Greenland')
    prior=read_json(data/'index.json',{})
    if not all(series['issued'] for series in snap['programs'].values()):raise ValueError('Current source edition date missing')
    if prior.get('latestObservedAt') and snap['programs']['visitor-outside-canada']['issued'] < prior['latestSourceDate']:
        raise ValueError('IRCC returned an older source edition')
    changed=prior.get('latestHash')!=snap['sha256']
    if changed:retain(data,snap)
    write_json(data/'countries.json',names)
    files=sorted((data/'history').glob('*.json'))
    count=sum(len(read_json(f,[])) for f in files)
    recent=max(r['observedAt'] for r in read_json(files[-1],[]))
    index={'checkedAt':now,'latestObservedAt':recent,'latestSourceDate':snap['programs']['visitor-outside-canada']['issued'],'latestHash':snap['sha256'],'captureCount':count,'seriesCount':sum(sum(i!=0 for i in r['values']) for r in snap['programs'].values()),'programs':PROGRAMS}
    write_json(data/'index.json',index)
    return index

if __name__=='__main__':
    print(json.dumps(update(),indent=2))
