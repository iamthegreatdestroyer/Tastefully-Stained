"""Tests for the stained glass pattern generation pipeline."""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from stained_glass.pattern_generator import PatternGenerator
from stained_glass.image_processor import ImageProcessor


@pytest.fixture(scope="module")
def synth_image() -> np.ndarray:
    return ImageProcessor.synthetic(128, 128)


@pytest.fixture(scope="module")
def pg() -> PatternGenerator:
    return PatternGenerator(random_state=0)


# ---------------------------------------------------------------------------
# test_segment
# ---------------------------------------------------------------------------

def test_segment_returns_list_of_masks(pg, synth_image):
    masks = pg.segment(synth_image, n_regions=20)
    assert isinstance(masks, list)
    assert len(masks) > 0
    for m in masks:
        assert isinstance(m, np.ndarray)
        assert m.dtype == bool
        assert m.shape == synth_image.shape[:2]


def test_segment_covers_full_image(pg, synth_image):
    masks = pg.segment(synth_image, n_regions=20)
    union = np.zeros(synth_image.shape[:2], dtype=bool)
    for m in masks:
        union |= m
    assert union.all(), "Voronoi masks must cover every pixel"


def test_segment_count_near_requested(pg, synth_image):
    masks = pg.segment(synth_image, n_regions=30)
    # We add 4 corner seeds so count can be up to n_regions + 4
    assert 1 <= len(masks) <= 34


# ---------------------------------------------------------------------------
# test_quantize_colors
# ---------------------------------------------------------------------------

def test_quantize_colors_returns_tuples(pg, synth_image):
    masks = pg.segment(synth_image, n_regions=10)
    colors = pg.quantize_colors(synth_image, masks, n_colors=8)
    assert len(colors) == len(masks)
    for c in colors:
        assert len(c) == 3
        r, g, b = c
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


def test_quantize_colors_palette_bounded(pg, synth_image):
    masks = pg.segment(synth_image, n_regions=15)
    colors = pg.quantize_colors(synth_image, masks, n_colors=4)
    unique = set(colors)
    assert len(unique) <= 4


# ---------------------------------------------------------------------------
# test_detect_edges
# ---------------------------------------------------------------------------

def test_detect_edges_returns_bool_array(pg, synth_image):
    edges = pg.detect_edges(synth_image)
    assert isinstance(edges, np.ndarray)
    assert edges.dtype == bool
    assert edges.shape == synth_image.shape[:2]


def test_detect_edges_has_some_edge_pixels(pg, synth_image):
    edges = pg.detect_edges(synth_image)
    assert edges.any(), "Gradient image must produce at least some edge pixels"


# ---------------------------------------------------------------------------
# test_to_svg
# ---------------------------------------------------------------------------

def test_to_svg_contains_required_tags(pg, synth_image):
    masks = pg.segment(synth_image, n_regions=10)
    colors = pg.quantize_colors(synth_image, masks, n_colors=6)
    edges = pg.detect_edges(synth_image)
    h, w = synth_image.shape[:2]
    svg = pg.to_svg(masks, colors, edges, width=w, height=h)
    assert "<svg" in svg
    assert "<polygon" in svg


def test_to_svg_polygon_count(pg, synth_image):
    n = 15
    masks = pg.segment(synth_image, n_regions=n)
    colors = pg.quantize_colors(synth_image, masks, n_colors=6)
    edges = pg.detect_edges(synth_image)
    h, w = synth_image.shape[:2]
    svg = pg.to_svg(masks, colors, edges, width=w, height=h)
    count = svg.count("<polygon")
    assert count >= 1


# ---------------------------------------------------------------------------
# test_full_pipeline
# ---------------------------------------------------------------------------

def test_full_pipeline_writes_svg(pg, synth_image):
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "test_output.svg")
        svg = pg.generate(synth_image, n_regions=20, n_colors=8, neural=False)
        with open(out, "w", encoding="utf-8") as f:
            f.write(svg)

        assert os.path.exists(out)
        size = os.path.getsize(out)
        assert size > 0, "SVG file must be non-empty"

        content = open(out, encoding="utf-8").read()
        assert "<svg" in content
        assert "<polygon" in content


def test_full_pipeline_neural_fallback(pg, synth_image):
    """Neural mode should not crash when torch is absent."""
    svg = pg.generate(synth_image, n_regions=10, n_colors=4, neural=True)
    assert "<svg" in svg
    assert "<polygon" in svg
