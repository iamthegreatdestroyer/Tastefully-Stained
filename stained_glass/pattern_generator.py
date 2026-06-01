"""PatternGenerator — 4-stage stained glass pipeline.

Stages:
  1. Voronoi segmentation  → list of boolean polygon masks
  2. KMeans color quantization per region  → (R, G, B) per mask
  3. Canny edge detection  → binary lead-line mask
  4. SVG export  → complete SVG string
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Tuple

import numpy as np
from scipy.spatial import Voronoi
from sklearn.cluster import KMeans
from skimage.feature import canny
from skimage.color import rgb2gray


class PatternGenerator:
    """Generate a stained-glass SVG from an RGB image."""

    def __init__(self, random_state: int = 42) -> None:
        self._rng = np.random.default_rng(random_state)

    # ------------------------------------------------------------------
    # Stage 1: Voronoi segmentation
    # ------------------------------------------------------------------

    def segment(
        self, image: np.ndarray, n_regions: int = 50
    ) -> List[np.ndarray]:
        """Divide image into Voronoi regions.

        Returns a list of H×W boolean masks, one per region.
        Regions that fall outside the convex hull of seeds are merged into
        a single "remainder" mask so the entire image is covered.
        """
        h, w = image.shape[:2]

        # Sample seed points; add corner seeds so Voronoi is bounded
        seeds = self._rng.uniform(0, 1, size=(n_regions, 2))
        seeds[:, 0] *= w
        seeds[:, 1] *= h
        corners = np.array([[0, 0], [w, 0], [0, h], [w, h]], dtype=float)
        all_seeds = np.vstack([seeds, corners])

        # Build pixel coordinate grid
        ys, xs = np.mgrid[0:h, 0:w]
        coords = np.column_stack([xs.ravel(), ys.ravel()])  # (H*W, 2)

        # Assign each pixel to its nearest seed via brute-force KD-like
        # broadcast (fast for small n_regions; scipy.cKDTree for large)
        diffs = coords[:, np.newaxis, :] - all_seeds[np.newaxis, :, :]  # (N,K,2)
        dists = np.sum(diffs ** 2, axis=2)  # (N,K)
        labels = np.argmin(dists, axis=1).reshape(h, w)

        masks: List[np.ndarray] = []
        for idx in range(len(all_seeds)):
            mask = labels == idx
            if mask.any():
                masks.append(mask)

        return masks

    # ------------------------------------------------------------------
    # Stage 2: Color quantization
    # ------------------------------------------------------------------

    def quantize_colors(
        self,
        image: np.ndarray,
        masks: List[np.ndarray],
        n_colors: int = 12,
    ) -> List[Tuple[int, int, int]]:
        """Get dominant color per region via KMeans(k=1).

        Returns list of (R, G, B) tuples in [0, 255], one per mask.
        """
        # First pass: assign each region a raw mean color
        raw_colors: List[np.ndarray] = []
        for mask in masks:
            pixels = image[mask]  # (P, 3)
            if len(pixels) == 0:
                raw_colors.append(np.array([128, 128, 128], dtype=float))
                continue
            # KMeans(1) == mean for a single cluster, but using it to match
            # the spec signature; fall back to mean for tiny regions
            if len(pixels) < 2:
                raw_colors.append(pixels[0].astype(float))
            else:
                km = KMeans(n_clusters=1, n_init="auto", random_state=0)
                km.fit(pixels.astype(float))
                raw_colors.append(km.cluster_centers_[0])

        # Second pass: quantize the region colors to n_colors palette
        color_arr = np.array(raw_colors, dtype=float)  # (M, 3)
        k = min(n_colors, len(color_arr))
        km_pal = KMeans(n_clusters=k, n_init="auto", random_state=0)
        km_pal.fit(color_arr)
        palette = km_pal.cluster_centers_
        assignments = km_pal.predict(color_arr)

        result: List[Tuple[int, int, int]] = []
        for idx in assignments:
            c = np.clip(palette[idx], 0, 255).astype(int)
            result.append((int(c[0]), int(c[1]), int(c[2])))
        return result

    # ------------------------------------------------------------------
    # Stage 3: Edge detection
    # ------------------------------------------------------------------

    def detect_edges(self, image: np.ndarray) -> np.ndarray:
        """Run Canny edge detector on grayscale image.

        Returns H×W boolean array where True = lead line pixel.
        """
        gray = rgb2gray(image)  # float64 [0,1]
        edges = canny(gray, sigma=1.5)
        return edges.astype(bool)

    # ------------------------------------------------------------------
    # Stage 4: SVG output
    # ------------------------------------------------------------------

    def to_svg(
        self,
        masks: List[np.ndarray],
        colors: List[Tuple[int, int, int]],
        edges: np.ndarray,
        width: int,
        height: int,
    ) -> str:
        """Build complete SVG string.

        - One <polygon> per region (filled with quantized color)
        - Lead lines rendered as a black <path> tracing edge pixels
        """
        svg = ET.Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "width": str(width),
                "height": str(height),
                "viewBox": f"0 0 {width} {height}",
            },
        )

        # --- polygons ---
        for mask, (r, g, b) in zip(masks, colors):
            points = self._mask_to_polygon_points(mask)
            if not points:
                continue
            pts_str = " ".join(f"{x},{y}" for x, y in points)
            ET.SubElement(
                svg,
                "polygon",
                {
                    "points": pts_str,
                    "fill": f"rgb({r},{g},{b})",
                    "stroke": "none",
                },
            )

        # --- lead lines ---
        edge_path = self._edges_to_path(edges)
        if edge_path:
            ET.SubElement(
                svg,
                "path",
                {
                    "d": edge_path,
                    "stroke": "black",
                    "stroke-width": "1.5",
                    "fill": "none",
                    "stroke-linecap": "round",
                },
            )

        return ET.tostring(svg, encoding="unicode")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mask_to_polygon_points(
        mask: np.ndarray,
    ) -> List[Tuple[int, int]]:
        """Approximate a boolean mask as a convex-hull polygon.

        Returns a list of (x, y) vertices. Falls back to bounding-box
        rectangle for very small regions.
        """
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return []

        coords = np.column_stack([xs, ys])

        if len(coords) < 4:
            # Tiny region — use bounding box
            x0, y0 = int(coords[:, 0].min()), int(coords[:, 1].min())
            x1, y1 = int(coords[:, 0].max()), int(coords[:, 1].max())
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

        # Convex hull (Graham scan via scipy)
        try:
            from scipy.spatial import ConvexHull
            hull = ConvexHull(coords.astype(float))
            verts = coords[hull.vertices]
            return [(int(v[0]), int(v[1])) for v in verts]
        except Exception:
            # Degenerate — bounding box fallback
            x0, y0 = int(coords[:, 0].min()), int(coords[:, 1].min())
            x1, y1 = int(coords[:, 0].max()), int(coords[:, 1].max())
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    @staticmethod
    def _edges_to_path(edges: np.ndarray) -> str:
        """Convert edge boolean mask to an SVG path string.

        Samples up to 4000 edge pixels and emits M x,y L x,y segments.
        """
        ys, xs = np.where(edges)
        if len(xs) == 0:
            return ""

        # Subsample for SVG size
        limit = 4000
        if len(xs) > limit:
            idx = np.linspace(0, len(xs) - 1, limit, dtype=int)
            xs, ys = xs[idx], ys[idx]

        parts: List[str] = []
        for x, y in zip(xs.tolist(), ys.tolist()):
            parts.append(f"M {x},{y} L {x+1},{y}")
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Full pipeline convenience
    # ------------------------------------------------------------------

    def generate(
        self,
        image: np.ndarray,
        n_regions: int = 50,
        n_colors: int = 12,
        neural: bool = False,
    ) -> str:
        """Run full pipeline and return SVG string."""
        if neural:
            from stained_glass import neural as neural_mod
            image = neural_mod.apply(image)

        h, w = image.shape[:2]
        masks = self.segment(image, n_regions=n_regions)
        colors = self.quantize_colors(image, masks, n_colors=n_colors)
        edges = self.detect_edges(image)
        return self.to_svg(masks, colors, edges, width=w, height=h)
