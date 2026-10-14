import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from refresh_catalog import from_manifest, source_url
from verify_catalog import verify

REV='a'*40
HASH='b'*64

def fixture():
    return {'format':1,'sampleRate':24000,'revision':'revision-hash','tokenizer':'tokenizer.json','steps':2,
            'profiles':{'wasm-uint8':{
                'provider':'wasm','dtype':'float32',
                'graphs':{'reference':{'file':'reference.onnx','url':'../common/reference.onnx', 'sha256':HASH,'bytes':50}},
                'shards':{'reference':{'file':'weights-reference.bin','url':'../common/weights-reference.bin', 'sha256':HASH,'bytes':500}}
            }}}

def test_bootstrap_is_rejected_by_default():
    with pytest.raises(ValueError, match='bootstrap'):
        verify({'schema': 1, 'kind': 'sopro-onnx-bundle-catalog', 'status': 'bootstrap'})


def test_build_verify():
    cat=from_manifest(fixture(),REV)
    verify(cat)
    assert len(cat['bundles']['v2-turbo']['artifacts'])==4
    assert cat['bundles']['v2-turbo']['profiles']['wasm-uint8']['graphs']['reference']=='common/reference.onnx'
    assert set(cat['bundles']['v2-turbo']['profiles']) == {'wasm-uint8'}
    assert 'cpu-fp32' not in cat['bundles']['v2-turbo']['profiles']


def test_pinned_catalog_lists_only_known_published_profiles():
    path = Path(__file__).resolve().parents[1] / 'catalog' / 'bundles.json'
    catalog = json.loads(path.read_text(encoding='utf-8'))
    verify(catalog)
    bundle = catalog['bundles']['v2-turbo']
    assert set(bundle['profiles']) == {'wasm-uint8', 'webgpu-fp16'}
    assert bundle['profiles']['wasm-uint8']['provider'] == 'wasm'
    assert bundle['profiles']['webgpu-fp16']['provider'] == 'webgpu'
    assert 'cpu-fp32' not in bundle['profiles']
    assert not any(item.get('profile') == 'cpu-fp32' for item in bundle['artifacts'])


def test_rejects_unpinned():
    cat=from_manifest(fixture(),REV)
    cat['bundles']['v2-turbo']['artifacts'][2]['url']='https://evil.example/x'
    with pytest.raises(ValueError): verify(cat)

def test_rejects_escape():
    m=fixture()
    m['profiles']['wasm-uint8']['graphs']['reference']['url']='../../escape.onnx'
    with pytest.raises(ValueError): from_manifest(m,REV)
    with pytest.raises(ValueError): source_url(REV,'../escape')


def test_artifact_selection_by_profile():
    from download_bundle import artifacts_for_profile
    c=from_manifest(fixture(),REV)
    paths=[a['path'] for a in artifacts_for_profile(c,'wasm-uint8')]
    assert paths==['common/reference.onnx','common/weights-reference.bin','manifest.json','tokenizer.json']


def test_download_rejects_bootstrap(tmp_path):
    from download_bundle import download
    with pytest.raises(ValueError,match='bootstrap'):
        download({'schema':1,'kind':'sopro-onnx-bundle-catalog','status':'bootstrap'},tmp_path)
