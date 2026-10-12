#!/usr/bin/env python3
"""Development-only fetch of a *pinned* export; runtime asset management belongs to OnnxVoice.

Preserves Sopro's original manifest/common/profile layout for native ONNX session testing.
Never consumes the unpinned bootstrap catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile

from verify_catalog import verify


def artifacts_for_profile(catalog: dict, profile: str) -> list[dict]:
    verify(catalog)
    bundle = catalog['bundles']['v2-turbo']
    if profile not in bundle['profiles']:
        raise ValueError(f'Unknown profile {profile}; options: {sorted(bundle["profiles"])}')
    found: dict[str, dict] = {}
    for item in bundle['artifacts']:
        if item.get('profile') in (None, profile):
            other = found.get(item['path'])
            if other and (other['url'], other['sha256']) != (item['url'], item['sha256']):
                raise ValueError('inconsistent artifact path')
            found[item['path']] = item
    return [found[key] for key in sorted(found)]


def download(catalog: dict, destination: Path, profile: str = 'wasm-uint8') -> list[Path]:
    items = artifacts_for_profile(catalog, profile)
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output: list[Path] = []
    for item in items:
        path = destination / item['path']
        if not path.resolve().is_relative_to(destination):
            raise ValueError('unsafe output path')
        path.parent.mkdir(parents=True, exist_ok=True)
        expected = item.get('sha256')
        size = item.get('bytes')
        if path.is_file() and (size is None or path.stat().st_size == size):
            if expected is None or _sha256(path) == expected:
                output.append(path)
                continue
        request = urllib.request.Request(item['url'], headers={'User-Agent':'sopro-onnx-bundles/0'})
        temp_name = None
        try:
            with NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', suffix='.tmp', delete=False) as temp:
                temp_name = temp.name
                digest = hashlib.sha256()
                total = 0
                with urllib.request.urlopen(request, timeout=60) as response:
                    while block := response.read(1024 * 1024):
                        total += len(block)
                        digest.update(block)
                        temp.write(block)
                temp.flush()
                os.fsync(temp.fileno())
            if size is not None and total != size:
                raise ValueError(f'wrong byte size for {item["path"]}: {total} != {size}')
            if expected is not None and digest.hexdigest() != expected:
                raise ValueError(f'SHA256 mismatch for {item["path"]}')
            os.replace(temp_name, path)
            temp_name = None
        finally:
            if temp_name is not None:
                os.unlink(temp_name)
        output.append(path)
    return output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=Path('catalog/bundles.json'))
    parser.add_argument('--profile', default='wasm-uint8')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding='utf-8'))
    paths = download(catalog, args.output, args.profile)
    print(f'Fetched/verified {len(paths)} artifacts in {args.output}')


if __name__ == '__main__':
    main()
