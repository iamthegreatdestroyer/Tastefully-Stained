"""Tastefully Stained — CLI entry point.

Usage:
  python main.py generate --input photo.jpg --output design.svg --colors 12
  python main.py generate --input photo.jpg --output design.svg --neural
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_generate(args: argparse.Namespace) -> None:
    from stained_glass.image_processor import ImageProcessor
    from stained_glass.pattern_generator import PatternGenerator

    if args.input:
        image = ImageProcessor.load(args.input)
    else:
        # Synthetic 256×256 gradient for quick testing
        image = ImageProcessor.synthetic(256, 256)

    pg = PatternGenerator()
    svg = pg.generate(
        image,
        n_regions=args.regions,
        n_colors=args.colors,
        neural=args.neural,
    )

    out_path = Path(args.output)
    out_path.write_text(svg, encoding="utf-8")
    print(f"SVG written to {out_path}  ({svg.count('<polygon')} polygons)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tastefully-stained",
        description="AI-powered stained glass pattern generator",
    )
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Generate a stained glass SVG")
    gen.add_argument("--input", "-i", default=None, help="Input image path (omit for synthetic test)")
    gen.add_argument("--output", "-o", default="output.svg", help="Output SVG path")
    gen.add_argument("--colors", "-c", type=int, default=12, help="Number of colors (default 12)")
    gen.add_argument("--regions", "-r", type=int, default=50, help="Number of Voronoi regions (default 50)")
    gen.add_argument("--neural", action="store_true", default=False, help="Apply neural style transfer (requires torch)")
    gen.add_argument("--no-neural", dest="neural", action="store_false", help="Skip neural enhancement (default)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
