"""Optional neural style transfer enhancement.

If torch is unavailable the apply() function prints a warning and returns the
input image unchanged so the geometric pipeline can continue without crashing.
"""

from __future__ import annotations

import numpy as np


def apply(image: np.ndarray) -> np.ndarray:
    """Apply Tiffany-style neural enhancement (requires torch).

    Falls back to identity transform when torch is not installed.
    """
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
        return _neural_transfer(image)
    except ImportError:
        print(
            "Neural enhancement unavailable (torch not found), "
            "using geometric pipeline"
        )
        return image


def _neural_transfer(image: np.ndarray) -> np.ndarray:
    """Lightweight gram-matrix style transfer (3-layer VGG-like conv)."""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torchvision import transforms, models

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    to_tensor = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    from PIL import Image as PILImage
    pil_img = PILImage.fromarray(image)
    content = to_tensor(pil_img).unsqueeze(0).to(device)

    vgg = models.vgg16(weights=None).features[:9].to(device).eval()
    for p in vgg.parameters():
        p.requires_grad_(False)

    output = content.clone().requires_grad_(True)
    optimizer = optim.Adam([output], lr=0.01)

    def gram(x: torch.Tensor) -> torch.Tensor:
        b, c, h, w = x.shape
        f = x.view(b, c, h * w)
        return torch.bmm(f, f.transpose(1, 2)) / (c * h * w)

    for _ in range(20):
        optimizer.zero_grad()
        c_feat = vgg(content)
        o_feat = vgg(output)
        loss = nn.functional.mse_loss(gram(o_feat), gram(c_feat))
        loss.backward()
        optimizer.step()

    out = output.detach().cpu().squeeze(0)
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    out = out * std + mean
    out = (out.permute(1, 2, 0).numpy() * 255).clip(0, 255).astype(np.uint8)
    return out
