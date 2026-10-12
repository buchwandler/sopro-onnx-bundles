#!/usr/bin/env python3
"""Build normalized Sopro catalog from a pinned Hugging Face upstream manifest."""
from __future__ import annotations
import argparse
import json
import posixpath
import re
import urllib.request
from pathlib import Path
from urllib.parse import quote

REPOSITORY = 'samuel-vitorino/sopro-v2-turbo-onnx'
HF_API = 'https://huggingface.co/api/models/' + REPOSITORY + '/revision/'
_SHA = re.compile(r'^[0-9a-f]{40}$')
_HASH = re.compile(r'^[0-9a-f]{64}$')

def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent':'sopro-onnx-bundles/0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def source_url(commit: str, path: str) -> str:
    # Do not treat untrusted manifest names as URL schemes or hostnames.
    if not _SHA.fullmatch(commit): raise ValueError('commit must be 40 hex characters')
    parts = path.split('/')
    if not parts or any(part in ('','.','..') for part in parts) or chr(92) in path:
        raise ValueError('unsafe artifact path: ' + path)
    return f'https://huggingface.co/{REPOSITORY}/resolve/{commit}/' + '/'.join(quote(p,safe='') for p in parts) + '?download=true'

def from_manifest(manifest: dict, commit: str) -> dict:
    if manifest.get('format') != 1 or not isinstance(manifest.get('profiles'),dict):
        raise ValueError('Unsupported upstream manifest schema')
    profiles={}
    artifacts = []
    referenced: dict[str, tuple[str|None,int|None]]={}
    for profile, record in sorted(manifest['profiles'].items()):
        if not re.fullmatch('[a-z0-9][a-z0-9-]*',profile): raise ValueError('unsafe profile')
        roles = {'graphs': {}, 'shards': {}}
        for category, singular in (('graphs','graph'),('shards','shard')):
            for role, item in sorted(record.get(category,{}).items()):
                if not re.fullmatch('[a-z][a-z0-9_]*',role):
                    raise ValueError('unsafe graph/shard role')
                raw = item.get('url') or item['file']
                if not isinstance(raw,str) or raw.startswith('/') or chr(92) in raw or '://' in raw:
                    raise ValueError('unsafe artifact link')
                # '../common' is a deliberate part of the official export.
                path = posixpath.normpath(posixpath.join(profile,raw))
                if path.startswith('../') or path in ('.','..') or path.startswith('/'):
                    raise ValueError('path escapes bundle root')
                sha, size = item.get('sha256'), item.get('bytes')
                if not isinstance(sha,str) or not _HASH.fullmatch(sha):
                    raise ValueError(f'missing upstream sha256 for {path}')
                if not isinstance(size,int) or size<=0:
                    raise ValueError(f'missing upstream byte size for {path}')
                if path in referenced and referenced[path] != (sha,size):
                    raise ValueError('conflicting duplicate artifact path: ' + path)
                referenced[path]=(sha,size)
                roles[category][role]=path
                artifacts.append({'role':singular, 'component':role, 'profile':profile,
                                  'path':path, 'filename':item['file'], 'sha256':sha,
                                  'bytes':size, 'url':source_url(commit,path),
                                  'provider':item.get('provider'),'dtype':item.get('dtype')})
        profiles[profile]={'provider':record.get('provider'), 'dtype':record.get('dtype'), **roles}
    tokenizer=manifest.get('tokenizer')
    if not isinstance(tokenizer,str) or not re.fullmatch('[a-zA-Z0-9_.-]+',tokenizer):
        raise ValueError('unexpected tokenizer path')
    artifacts.insert(0,{'role':'tokenizer','component':None,'profile':None,'path':tokenizer,
                        'filename':tokenizer,'sha256':None,'bytes':None,'url':source_url(commit,tokenizer)})
    artifacts.insert(0,{'role':'manifest','component':None,'profile':None,'path':'manifest.json',
                        'filename':'manifest.json','sha256':None,'bytes':None,
                        'url':source_url(commit,'manifest.json')})
    return {'schema':1, 'kind':'sopro-onnx-bundle-catalog', 'status':'pinned',
            'bundles':{'v2-turbo':{'id':'v2-turbo','ref':'sopro:v2-turbo',
               'aliases':['turbo'],'model':REPOSITORY,
               'revision':manifest.get('revision'), 'source_commit':commit,
               'sample_rate':manifest['sampleRate'], 'languages':['en','pt','fr','de'],
               'steps':manifest.get('steps'), 'profiles':profiles,'artifacts':artifacts}}}

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--revision',default='main', help='HF branch/tag/commit resolved to a pinned SHA')
    p.add_argument('--manifest-file',type=Path,help='offline manifest fixture; requires --commit')
    p.add_argument('--commit',default=None,help='40-char upstream HF commit for offline mode')
    p.add_argument('--output',type=Path,default=Path('catalog/bundles.json'))
    p.add_argument('--source-output',type=Path,default=Path('catalog/source.json'))
    a=p.parse_args()
    if a.manifest_file:
        if not a.commit or not _SHA.fullmatch(a.commit): p.error('--manifest-file requires --commit SHA')
        commit=a.commit
        manifest=json.loads(a.manifest_file.read_text(encoding='utf-8'))
    else:
        info=get_json(HF_API+quote(a.revision,safe=''))
        commit=info['sha']
        if not _SHA.fullmatch(commit): raise ValueError('Hugging Face did not return a commit SHA')
        manifest=get_json(source_url(commit,'manifest.json'))
    catalog=from_manifest(manifest,commit)
    source={'schema':1,'kind':'sopro-source','status':'pinned',
            'repository':REPOSITORY,'resolved_revision':commit,
            'manifest_revision':manifest.get('revision')}
    for path, data in ((a.output,catalog),(a.source_output,source)):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True)+chr(10),encoding='utf-8')
    print(f"Pinned {REPOSITORY}@{commit}; {len(catalog['bundles']['v2-turbo']['artifacts'])} artifacts")

if __name__=='__main__': main()
