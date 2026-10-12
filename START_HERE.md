# Getting started with Sopro ONNX bundle catalog

This is a **metadata-only Git repository**; it has no Python package version.
Use Git tags for repo releases and `schema` for catalog compatibility.

```bash
python -m pip install pytest
pytest -q
python tools/refresh_catalog.py
python tools/verify_catalog.py catalog/bundles.json
python tools/download_bundle.py --profile wasm-uint8 --output ../onnx-model
```

Refreshing requires network access to Hugging Face. The bundled bootstrap catalog
contains no pinned weight metadata; it deliberately fails normal verification until
refreshed. The source snapshot is a project starter, not a model mirror.
