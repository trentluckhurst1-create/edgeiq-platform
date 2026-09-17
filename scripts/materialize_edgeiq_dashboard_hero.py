#!/usr/bin/env python3
"""Materialize public/assets/edgeiq-dashboard-hero.jpg from committed base64 text."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B64 = ROOT / "public" / "assets" / "edgeiq-dashboard-hero.jpg.b64"
OUT = ROOT / "public" / "assets" / "edgeiq-dashboard-hero.jpg"


def main() -> int:
    if not B64.is_file():
        print(f"MISSING base64 source: {B64}", file=sys.stderr)
        return 1
    raw = "".join(B64.read_text(encoding="utf-8").split())
    if not raw:
        print("EMPTY base64 payload", file=sys.stderr)
        return 1
    data = base64.b64decode(raw, validate=False)
    if len(data) < 8_000:
        print(f"DECODED payload too small ({len(data)} bytes)", file=sys.stderr)
        return 1
    if data[:3] != b"\xff\xd8\xff":
        print("DECODED payload is not a JPEG (missing SOI marker)", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    print(f"OK wrote {OUT} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
