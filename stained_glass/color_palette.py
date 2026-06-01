"""ColorPalette — color reduction helpers for stained glass patterns."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans


class ColorPalette:
    """Reduce an image to N dominant colors via KMeans."""

    def __init__(self, n_colors: int = 12, random_state: int = 42) -> None:
        self.n_colors = n_colors
        self.random_state = random_state

    def fit(self, image: np.ndarray) -> list[tuple[int, int, int]]:
        """Return list of (R, G, B) dominant colors from the image."""
        pixels = image.reshape(-1, 3).astype(np.float32)
        k = min(self.n_colors, len(pixels))
        km = KMeans(n_clusters=k, random_state=self.random_state, n_init="auto")
        km.fit(pixels)
        centers = np.clip(km.cluster_centers_, 0, 255).astype(int)
        return [(int(c[0]), int(c[1]), int(c[2])) for c in centers]
