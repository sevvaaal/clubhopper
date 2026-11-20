"""Draws Clubhopper's own pixel football, the logo and the tab icon (SVG).

The ball is rasterised from simple geometry (a circle with a centre pentagon
and five edge patches) onto a small pixel grid, so it's an original drawing in
the same pixel style as Starlinked's stars.

    python3 make_logo.py
"""

import math
from pathlib import Path

N = 20  # pixel grid
INK, WHITE, SHADE, PATCH = "#2e2b3f", "#f8f3e8", "#d9d2c2", "#2e2b3f"


def pentagon(cx, cy, r, rot):
    return [(cx + r * math.cos(rot + i * 2 * math.pi / 5), cy + r * math.sin(rot + i * 2 * math.pi / 5)) for i in range(5)]


def inside(poly, x, y):
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def ball_grid():
    c, R = N / 2, N / 2 - 0.6
    centre = pentagon(c, c - 0.3, R * 0.36, -math.pi / 2)
    edges = [pentagon(c + R * 0.92 * math.cos(a), c - 0.3 + R * 0.92 * math.sin(a), R * 0.34, a + math.pi)
             for a in [-math.pi / 2 + k * 2 * math.pi / 5 + math.pi / 5 for k in range(5)]]
    grid = [["." for _ in range(N)] for _ in range(N)]
    for y in range(N):
        for x in range(N):
            px, py = x + 0.5, y + 0.5
            d = math.hypot(px - c, py - c)
            if d > R:
                continue
            if d > R - 1.05:
                grid[y][x] = "O"
            elif inside(centre, px, py) or any(inside(e, px, py) for e in edges):
                grid[y][x] = "B"
            elif (px - c) * 0.55 + (py - c) * 0.85 > R * 0.45:
                grid[y][x] = "S"  # shading towards the bottom right
            else:
                grid[y][x] = "W"
    return grid


COLORS = {"O": INK, "B": PATCH, "W": WHITE, "S": SHADE}


def rects(grid, x0, y0, cell):
    out = []
    for y, row in enumerate(grid):
        x = 0
        while x < len(row):
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            end = x
            while end < len(row) and row[end] == ch:
                end += 1
            out.append(f'<rect x="{x0 + x * cell:g}" y="{y0 + y * cell:g}" width="{(end - x) * cell:g}" height="{cell:g}" fill="{COLORS[ch]}"/>')
            x = end
    return "".join(out)


# Starlinked's two chain links (drawn from scratch there too), with a dark edge.
LEFT = "M300 258 C300 190 250 140 190 140 L165 140 C100 140 50 190 50 250 C50 310 100 360 160 360"
RIGHT = "M212 242 C212 310 262 360 322 360 L347 360 C412 360 462 310 462 250 C462 190 412 140 352 140"
CHAIN = "".join(
    f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="54" stroke-linecap="round"/>'
    f'<path d="{d}" fill="none" stroke="{WHITE}" stroke-width="40" stroke-linecap="round"/>'
    for d in (LEFT, RIGHT)
)

grid = ball_grid()
print("\n".join("".join(r) for r in grid))

cell = 9
size = N * cell


def ball_at(cx, cy, scale=1.0):
    return f'<g shape-rendering="crispEdges">{rects(grid, cx - size * scale / 2, cy - size * scale / 2, cell * scale)}</g>'


def svg(body, viewbox="24 30 464 414"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" fill="none">{body}</svg>\n'


Path("ball.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {N} {N}" shape-rendering="crispEdges">{rects(grid, 0, 0, 1)}</svg>\n')
# The logo: the two links with a ball at each end (draft B, the user's pick).
LOGO = CHAIN + ball_at(50, 250, 0.75) + ball_at(462, 250, 0.75)
LOGO_BOX = "-40 30 592 414"
Path("logo.svg").write_text(svg(LOGO, LOGO_BOX))
# Tab icon: same art on a dark rounded square, so it reads on light and dark tabs.
Path("favicon.svg").write_text(
    svg(f'<rect x="-50" y="-59" width="612" height="612" rx="128" fill="#383c60"/>{LOGO}', "-50 -59 612 612")
)
print("wrote ball.svg, logo.svg and favicon.svg")
