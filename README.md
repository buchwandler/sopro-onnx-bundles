# sopro-onnx-bundles

Metadata-only catalog for the official [Sopro V2 Turbo ONNX exports](https://huggingface.co/samuel-vitorino/sopro-v2-turbo-onnx).
Companion to SoproSynth/OnnxVoice. **Not a Python package, model mirror or runtime.**

## Build current pinned catalog

```bash
python tools/refresh_catalog.py --output catalog/bundles.json --source-output catalog/source.json
python tools/verify_catalog.py catalog/bundles.json
```

The builder fetches upstream `manifest.json` at a **resolved 40-character HF commit**,
normalizes file URLs and includes exported graph/shard SHA256 + byte sizes. All generated
file URLs pin that exact commit. The checked-in `catalog/bundles.json` is pinned to a resolved upstream revision. Normal verification rejects bootstrap catalogs; reserve `--allow-bootstrap` for explicitly named development fixtures only.

The pinned upstream manifest currently lists two published export profiles: `wasm-uint8` (portable/quantized, `wasm` provider) and `webgpu-fp16` (float16, `webgpu` provider). These are source-published export tiers, not evidence of native inference or parity. SoproSynth's Python runtime currently accepts only `wasm-uint8` on CPU; consumers must use the provider declared by each profile.

There is no `cpu-fp32` profile or artifact in this catalog. Do not invent or advertise that tier until upstream supplies pinned FP32 graph/shard exports and direct FP32 oracle comparisons are available. Native-versus-ONNX perceptual evaluation also remains blocked on a licensed listening corpus.
The catalog has one model identity: `sopro:v2-turbo`. Do not create language-specific
bundles for the same multilingual weights.

## Dynamic versioning

This is a metadata repository. **No static Python project version and no src/ layer.**
Compatibility uses catalog `schema: 1`; use Git release tags (`v0.1.0`, etc.) for
repository releases. Model/export `revision` is **upstream-provided**, independent of
repository tag. CI can update the catalog daily via workflow. Preserve SHA pins.

## Fetch a profile for OnnxVoice testing

After refreshing the pinned catalog, download a **single selected profile** while
preserving ONNX external-weight paths:

```bash
python tools/download_bundle.py --profile wasm-uint8 --output ../sopro-onnx-model
# Then from the soprosynth repository:
python -m soprosynth inspect ../sopro-onnx-model --profile wasm-uint8
```

This is only a development helper. Long-term artifact acquisition, verified cache
and installation ownership should move to the OnnxVoice `install()` path.

## Installation and integrity

`graph.url` / `shard.url` are pinned, full Hugging Face artifact URLs. Upstream ONNX
external weights are relative to the graph location, so an installer must keep
`common/` and `<profile>/` folder layout. A complete downloader/install operation belongs
in OnnxVoice; the catalog does not download weights.

Upstream model artifacts and tokenizer are Apache-2.0; retain their own provenance.
This project has no rights to change their license.
