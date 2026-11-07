"""Validate the public source catalog without private build dependencies."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.egern_hub.source_catalog import normalize

def validate(root):
    seen=set()
    paths=sorted((Path(root)/'catalog').glob('*.json'))
    if not paths:raise ValueError('catalog is empty')
    for path in paths:
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('version')!=2:raise ValueError('Only source-level catalog v2 is accepted')
        normalize(data)
        identity=data['repository'].casefold().rstrip('/')
        if identity in seen:raise ValueError('Duplicate source repository')
        seen.add(identity)
        for selected in data['discovery'].get('select',[]):
            if selected.startswith('/') or '\\' in selected or any(p in {'','.','..'} for p in selected.rstrip('/').split('/')):
                raise ValueError('Unsafe discovery.select path')
    return len(paths)
if __name__=='__main__':print('Validated',validate(Path(__file__).resolve().parents[1]),'source manifests')
