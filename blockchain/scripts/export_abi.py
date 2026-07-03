#!/usr/bin/env python3
"""
Export the compiled WatermarkRegistry ABI from Hardhat's build artifact
into the location the Python backend loads it from
(backend/watermark_engine/blockchain/abi/WatermarkRegistry.json).

Run this after `npx hardhat compile` any time WatermarkRegistry.sol
changes, so the Python-side ABI stays in sync with the actual compiled
contract.

Usage (from blockchain/):
    npx hardhat compile
    python3 scripts/export_abi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BLOCKCHAIN_DIR = Path(__file__).parent.parent
_ARTIFACT_PATH = (
    _BLOCKCHAIN_DIR
    / "artifacts"
    / "contracts"
    / "WatermarkRegistry.sol"
    / "WatermarkRegistry.json"
)
_OUTPUT_PATH = (
    _BLOCKCHAIN_DIR.parent
    / "backend"
    / "watermark_engine"
    / "blockchain"
    / "abi"
    / "WatermarkRegistry.json"
)


def main() -> int:
    if not _ARTIFACT_PATH.exists():
        print(
            f"Artifact not found at {_ARTIFACT_PATH}. "
            "Run `npx hardhat compile` first.",
            file=sys.stderr,
        )
        return 1

    with _ARTIFACT_PATH.open("r", encoding="utf-8") as fh:
        artifact = json.load(fh)

    abi = artifact["abi"]

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(abi, fh, indent=2)
        fh.write("\n")

    print(f"Exported {len(abi)} ABI entries to {_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
