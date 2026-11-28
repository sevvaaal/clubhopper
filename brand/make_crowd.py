"""Pixel-art stadium crowd tiles for the site background.

Writes site/img/bg/crowd-night.png, a small tile of fans in rows of seats, and
floodlight.png, a floodlight tower. Both are drawn one pixel per "pixel" and scaled up in CSS with
image-rendering: pixelated. Standard library only.

    python make_crowd.py
"""

import random
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "site" / "img" / "bg"
W, H = 128, 64          # tile size in pixels; repeats seamlessly
COL, ROW = 4, 8         # one fan per 4 px column, one seat row per 8 px

THEMES = {
    "night": {
        "stand": (42, 38, 82), "step": (28, 25, 58), "seat": (74, 70, 133),
        "skin": [(150, 128, 120), (128, 104, 92), (98, 76, 66), (70, 54, 48)],
        "shirts": [(140, 40, 60), (140, 40, 60), (48, 64, 140), (48, 64, 140), (150, 150, 175),
                   (160, 140, 70), (60, 100, 70)],
        "empty": 0.35, "raise": 0.06,
    },
}


def tile(theme: dict, seed: int) -> list[list[tuple]]:
    rnd = random.Random(seed)
    px = [[theme["stand"]] * W for _ in range(H)]

    def put(x, y, c):
        px[y % H][x % W] = c

    for top in range(0, H, ROW):
        for x in range(W):
            put(x, top + 6, theme["step"])
            put(x, top + 7, theme["step"])
        for left in range(0, W, COL):
            # seat back, visible when the seat is empty
            for dx in range(3):
                for dy in (4, 5):
                    put(left + dx, top + dy, theme["seat"])
            if rnd.random() < theme["empty"]:
                continue
            skin, shirt = rnd.choice(theme["skin"]), rnd.choice(theme["shirts"])
            shift = rnd.choice((0, 0, 1))
            for dx in (1, 2):                       # head
                for dy in (1, 2):
                    put(left + dx + shift - 1, top + dy, skin)
            for dx in range(3):                     # shirt
                for dy in (3, 4, 5):
                    put(left + dx + shift - 1, top + dy, shirt)
            if rnd.random() < theme["raise"]:       # arms up
                put(left + shift - 1, top, skin)
                put(left + shift + 1, top, skin)
    return px


CLEAR = (0, 0, 0, 0)


def floodlight() -> list[list[tuple]]:
    """A 16x40 floodlight tower on a transparent background: a frame of lamps on a pole."""
    w, h = 16, 40
    frame, lamp, lamp_dim = (21, 18, 43, 255), (244, 241, 255, 255), (201, 195, 255, 255)
    pole, pole_light, brace = (108, 102, 176, 255), (143, 136, 214, 255), (58, 53, 112, 255)
    px = [[CLEAR] * w for _ in range(h)]
    for y in range(10):                          # lamp frame
        for x in range(w):
            px[y][x] = frame
    for j, y in enumerate((1, 4, 7)):            # 5 x 3 lamps, 2 px each
        for i, x in enumerate((1, 4, 7, 10, 13)):
            colour = lamp if (i + j) % 2 == 0 else lamp_dim
            for dx in (0, 1):
                for dy in (0, 1):
                    px[y + dy][x + dx] = colour
    for y in range(10, h):                       # pole with braces
        px[y][7], px[y][8] = pole_light, pole
        if y % 5 == 2:
            px[y][6], px[y][9] = brace, brace
    return px


def png(pixels: list[list[tuple]]) -> bytes:
    """RGB or RGBA (by the pixel tuples' length) PNG, no filtering."""
    height, width, channels = len(pixels), len(pixels[0]), len(pixels[0][0])
    raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in pixels)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 6 if channels == 4 else 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {f"crowd-{name}.png": tile(theme, seed=8) for name, theme in THEMES.items()}
    files["floodlight.png"] = floodlight()
    for name, pixels in files.items():
        path = OUT / name
        path.write_bytes(png(pixels))
        print(f"{path.name}: {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
