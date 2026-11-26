"""Import verifiable historical captures into the same schema as direct observations."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import subprocess
from collect import DATA, OFFICIAL, pack, retain
MIRROR='https://github.com/suhaibmujahid/cic-processing-times'

def import_archives(repo,wayback):
    counts={'wayback':0,'mirror':0}
    for path in sorted(wayback.glob('*.json')):
        stamp=path.stem
        observed=datetime.strptime(stamp,'%Y%m%d%H%M%S').replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z')
        link=f'https://web.archive.org/web/{stamp}id_/{OFFICIAL}'
        counts['wayback']+=retain(DATA,pack(path.read_bytes(),observed,link))
    def git(*args):
        return subprocess.check_output(['git','-C',str(repo),*args])
    if git('remote','get-url','origin').decode().strip().removesuffix('.git')!=MIRROR:raise ValueError('Unexpected source repository')
    path='data-ptime-en.json'
    revisions=git('log','--reverse','--format=%H %aI','--',path).decode().splitlines()
    for revision in revisions:
        sha,timestamp=revision.split()
        raw=git('show',f'{sha}:{path}')
        observed=datetime.fromisoformat(timestamp).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
        counts['mirror']+=retain(DATA,pack(raw,observed,f'{MIRROR}/blob/{sha}/{path}'))
    return counts
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mirror_checkout',type=Path)
    parser.add_argument('wayback_capture_directory',type=Path)
    args=parser.parse_args()
    print(import_archives(args.mirror_checkout,args.wayback_capture_directory))
