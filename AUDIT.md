# AUDIT.md — Tastefully Stained Sprint 1 Audit

**Date:** 2026-05-31  
**Auditor:** @APEX

---

## Architecture Reality

The repo is a **C2PA/watermarking service** (FastAPI + blockchain), not the stained glass
pattern generator described in CLAUDE.md. The CLAUDE.md sprint plan is additive — it builds
new `stained_glass/` tooling on top of the existing backend.

---

## Existing Components

### `backend/watermark_engine/core/`

| Class | File | Status |
|---|---|---|
| `DCTWatermarker` | `dct_processor.py` | **STUB** — `embed_watermark` / `extract_watermark` raise `NotImplementedError` |
| `DWTWatermarker` | `dwt_processor.py` | **STUB** — same pattern |
| `HybridAlgorithm` | `hybrid_algorithm.py` | **STUB** |

### `backend/watermark_engine/utils/`

| Class | File | Status |
|---|---|---|
| `ImageLoader` | `image_loader.py` | **PARTIAL** — `load`, `load_from_bytes`, `save` are stubs; `to_float`/`to_uint8` static helpers **DONE** |
| Config | `config.py` | **DONE** |
| Logger | `logger.py` | **DONE** |

### `backend/watermark_engine/`

| Module | Status |
|---|---|
| `api/routes.py` | **PARTIAL** — router wired, auth routes in `api/routes/auth.py` |
| `blockchain/ethereum_anchor.py` | **STUB** |
| `blockchain/ipfs_handler.py` | **STUB** |
| `c2pa/manifest_builder.py` | **STUB** |
| `c2pa/validation.py` | **STUB** |
| `db/models.py`, `db/session.py` | **DONE** (ORM models exist) |

### Tests (`backend/tests/`)

| File | Status |
|---|---|
| `conftest.py` | **DONE** — sample fixtures for 256×256 images |
| `test_dct.py`, `test_dwt.py` | Exist but test **stubs** — all skip/xfail expected |
| `test_hybrid.py`, `test_c2pa.py`, `test_blockchain.py` | Exist |
| `test_api.py` | Exists |

---

## Sprint 2–3 Additions (New — Not Previously Existing)

The following are **net-new** components built in Sprints 2–3:

| Path | Description |
|---|---|
| `stained_glass/__init__.py` | Module init |
| `stained_glass/pattern_generator.py` | `PatternGenerator` — Voronoi segmentation, KMeans color quantization, Canny edge detection, SVG export |
| `stained_glass/image_processor.py` | `ImageProcessor` — PIL/numpy image load/save helpers |
| `stained_glass/color_palette.py` | `ColorPalette` — color reduction helpers |
| `stained_glass/neural.py` | Neural style transfer stub (prints warning when torch absent) |
| `stained_glass/cli.py` | `main.py` CLI — `generate` subcommand |
| `main.py` (root) | CLI entry point |
| `tests/test_pattern.py` | 5 tests covering the full pipeline |

---

## Dependencies

| Package | Status |
|---|---|
| numpy, scipy, Pillow | Installed in `.venv` |
| scikit-learn | **Installed** (Sprint 1) |
| scikit-image | **Installed** (Sprint 1) |
| torch / torchvision | **Not available** — neural path uses graceful fallback |
| fastapi, uvicorn, sqlalchemy, etc. | Installed |
