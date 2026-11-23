"""Génère src/hellowork_mcp/assets/icon.png (256 x 256) sans dépendance externe.

Icône originale du projet (fond indigo arrondi, lettre H, point jaune). Elle ne reprend pas le logo
officiel Hellowork : ce projet est indépendant de Hellowork.

Usage : python scripts/make_icon.py
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 256
BG = (49, 46, 129)
FG = (255, 255, 255)
ACCENT = (250, 204, 21)


def inside_rounded(x: int, y: int, radius: int) -> bool:
    cx = min(max(x, radius), SIZE - 1 - radius)
    cy = min(max(y, radius), SIZE - 1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def pixel(x: int, y: int) -> tuple[int, int, int, int]:
    if not inside_rounded(x, y, 48):
        return (0, 0, 0, 0)
    # Lettre H
    if (64 <= x < 100 or 156 <= x < 192) and 56 <= y < 200:
        return (*FG, 255)
    if 100 <= x < 156 and 112 <= y < 144:
        return (*FG, 255)
    # Point d'accent
    if (x - 200) ** 2 + (y - 200) ** 2 <= 18**2:
        return (*ACCENT, 255)
    return (*BG, 255)


def png_bytes() -> bytes:
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)
        for x in range(SIZE):
            raw.extend(pixel(x, y))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data = png_bytes()
    for target in (root / "src" / "hellowork_mcp" / "assets" / "icon.png", root / "icon.png"):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print(f"{target} ({len(data)} octets)")


if __name__ == "__main__":
    main()
