#!/usr/bin/env python3
"""Check schema, path safety, SHA pins, role uniqueness and selected profile maps."""
import argparse, json, re, sys
from pathlib import Path
from urllib.parse import urlsplit

SHA40=re.compile('^[0-9a-f]{40}$')
SHA64=re.compile('^[0-9a-f]{64}$')

def verify(raw: dict, *, allow_bootstrap: bool=False) -> None:
    if raw.get('schema')!=1 or raw.get('kind')!='sopro-onnx-bundle-catalog':
        raise ValueError('invalid catalog kind/schema')
    if raw.get('status')=='bootstrap':
        if not allow_bootstrap: raise ValueError('bootstrap catalog has no pinned ONNX assets; run refresh')
        return
    if raw.get('status')!='pinned': raise ValueError('bad catalog status')
    bundles=raw['bundles']
    if not isinstance(bundles,dict) or not bundles: raise ValueError('no bundles')
    for bundle in bundles.values():
        sha=bundle['source_commit']
        if not SHA40.fullmatch(sha): raise ValueError('revision not pinned')
        profiles=bundle['profiles']
        if not profiles: raise ValueError('missing profiles')
        seen=set(); by_profile={name:set() for name in profiles}
        for a in bundle['artifacts']:
            path=a['path']
            if path.startswith('/') or any(part in ('','.','..') for part in path.split('/')):
                raise ValueError('unsafe artifact path')
            url=urlsplit(a['url'])
            if url.scheme!='https' or url.hostname!='huggingface.co' or f'/resolve/{sha}/' not in url.path:
                raise ValueError('unpinned artifact URL')
            key=(a['role'],a.get('component'),a.get('profile'))
            if key in seen: raise ValueError('duplicate role/profile')
            seen.add(key)
            if a['role'] in ('graph','shard'):
                if not SHA64.fullmatch(a.get('sha256','')) or not isinstance(a.get('bytes'),int) or a['bytes']<=0:
                    raise ValueError('missing graph/shard integrity metadata')
                by_profile[a['profile']].add((a['role'],a['component'],path))
        for profile, entries in profiles.items():
            for category, singular in (('graphs','graph'),('shards','shard')):
                for role,path in entries[category].items():
                    if (singular,role,path) not in by_profile[profile]:
                        raise ValueError(f'missing {profile} {singular} {role}')
        if ('manifest',None,None) not in seen or ('tokenizer',None,None) not in seen:
            raise ValueError('missing manifest or tokenizer')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('path',type=Path)
    p.add_argument('--allow-bootstrap',action='store_true')
    a=p.parse_args()
    try: verify(json.loads(a.path.read_text()),allow_bootstrap=a.allow_bootstrap)
    except (ValueError,KeyError,TypeError) as exc:
        sys.exit(f'INVALID: {exc}')
    print('Catalog verified')

if __name__=='__main__': main()
