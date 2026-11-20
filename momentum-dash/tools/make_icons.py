"""Generate the extension icons (icons/icon16.png, icon48.png, icon128.png).

Developer tool, standard library only. The design: a dark rounded square with a
silver ring and a dark-green progress arc (the Pomodoro ring), drawn pixel by pixel
with 4x4 supersampling for smooth edges.

    python tools/make_icons.py      # from the momentum-dash folder
"""

import math
import struct
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "icons"
BG = (16, 26, 22)        # near-black green
TRACK = (110, 120, 124)  # dim silver
ARC = (90, 154, 130)     # green accent
SAMPLES = 4


def color_at(x: float, y: float) -> tuple[int, int, int, int]:
    """Colour of a point in a 1x1 unit square (0,0 = top-left)."""
    # rounded-square background
    r = 0.22
    dx = max(abs(x - 0.5) - (0.5 - r), 0)
    dy = max(abs(y - 0.5) - (0.5 - r), 0)
    if dx * dx + dy * dy > r * r:
        return (0, 0, 0, 0)

    # ring: radius 0.30, thickness 0.075
    dist = math.hypot(x - 0.5, y - 0.5)
    if abs(dist - 0.30) <= 0.0375:
        # angle measured clockwise from 12 o'clock; arc covers 0–270°
        angle = (math.degrees(math.atan2(x - 0.5, 0.5 - y)) + 360) % 360
        return (*ARC, 255) if angle <= 270 else (*TRACK, 255)
    return (*BG, 255)


def render(size: int) -> bytes:
    rows = []
    for py in range(size):
        row = bytearray([0])  # PNG filter type 0 for each scanline
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(SAMPLES):
                for sx in range(SAMPLES):
                    c = color_at((px + (sx + 0.5) / SAMPLES) / size, (py + (sy + 0.5) / SAMPLES) / size)
                    acc[0] += c[0] * c[3]
                    acc[1] += c[1] * c[3]
                    acc[2] += c[2] * c[3]
                    acc[3] += c[3]
            alpha = acc[3] / SAMPLES**2
            rgb = [round(v / acc[3]) if acc[3] else 0 for v in acc[:3]]
            row += bytes([*rgb, round(alpha)])
        rows.append(bytes(row))
    return b"".join(rows)


def png(size: int, raw: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for size in (16, 48, 128):
        path = OUT_DIR / f"icon{size}.png"
        path.write_bytes(png(size, render(size)))
        print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
