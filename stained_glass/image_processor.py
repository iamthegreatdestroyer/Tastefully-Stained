"""ImageProcessor — PIL/numpy image load and save helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


class ImageProcessor:
    """Load and save images as RGB numpy arrays."""

    @staticmethod
    def load(path: str | Path) -> np.ndarray:
        """Load image from disk, return H×W×3 uint8 RGB array."""
        img = Image.open(path).convert("RGB")
        return np.array(img, dtype=np.uint8)

    @staticmethod
    def from_array(arr: np.ndarray) -> np.ndarray:
        """Ensure array is H×W×3 uint8 RGB."""
        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)
        return arr.astype(np.uint8)

    @staticmethod
    def save(image: np.ndarray, path: str | Path) -> None:
        """Save H×W×3 uint8 RGB array to disk."""
        Image.fromarray(image.astype(np.uint8)).save(path)

    @staticmethod
    def synthetic(width: int = 256, height: int = 256) -> np.ndarray:
        """Create a synthetic checkerboard+gradient RGB image for testing.

        The checkerboard ensures Canny always finds edges even at high sigma.
        """
        img = np.zeros((height, width, 3), dtype=np.uint8)
        # Gradient channels
        r = np.linspace(0, 255, width, dtype=np.uint8)
        g = np.linspace(255, 0, height, dtype=np.uint8)
        img[:, :, 0] = r[np.newaxis, :]
        img[:, :, 1] = g[:, np.newaxis]
        img[:, :, 2] = 128
        # 16×16 checkerboard overlay so edges are sharp and detectable
        block = max(1, width // 16)
        for iy in range(0, height, block):
            for ix in range(0, width, block):
                if ((iy // block) + (ix // block)) % 2 == 0:
                    img[iy:iy+block, ix:ix+block] = 255
        return img
