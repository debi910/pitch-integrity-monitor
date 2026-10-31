"""Shared style, fonts, easing and drawing helpers for the video renderer.

Frames are drawn at 2x (3840x2160) and box-reduced to 1920x1080 for antialiasing.
"""
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
VID = ROOT / "video"
FONTS = VID / "fonts"
IMG = ROOT / "web" / "img"
BUILD = VID / "build"

W, H, S = 1920, 1080, 2          # output size, supersample factor
FPS = 30

CREAM = (247, 244, 238)
CREAM2 = (239, 234, 224)
INK = (22, 24, 28)
INK2 = (88, 92, 100)
MUTED = (150, 146, 138)
RED = (200, 50, 43)
AMBER = (217, 134, 11)
GREEN = (46, 125, 91)
GRASS = (205, 219, 196)
GRASS2 = (194, 210, 184)
DIRT = (226, 199, 163)
LINE = (222, 216, 204)


@lru_cache(None)
def font(kind, size, weight=None):
    """kind: serif | serif-i | sans | mono. size in OUTPUT pixels (scaled by S here)."""
    path = {"serif": "InstrumentSerif-Regular.ttf", "serif-i": "InstrumentSerif-Italic.ttf",
            "sans": "Inter[opsz,wght].ttf", "mono": "JetBrainsMono[wght].ttf"}[kind]
    f = ImageFont.truetype(str(FONTS / path), int(size * S))
    if weight and kind in ("sans", "mono"):
        try:
            axes = f.get_variation_axes()
            vals = []
            for a in axes:
                name = a.get("name", b"")
                name = name.decode() if isinstance(name, bytes) else str(name)
                if "eight" in name or name.lower() == "wght":
                    vals.append(weight)
                elif "ptical" in name or name.lower() == "opsz":
                    vals.append(max(a["minimum"], min(a["maximum"], size * 0.75)))
                else:
                    vals.append(a["default"])
            f.set_variation_by_axes(vals)
        except Exception:
            pass
    return f


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):  # easeInOutCubic
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):  # easeOutQuart
    x = clamp(x)
    return 1 - (1 - x) ** 4


def spring(x):  # easeOutBack, small overshoot
    x = clamp(x)
    c1, c3 = 1.4, 2.4
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def prog(t, start, dur):
    return clamp((t - start) / dur)


def lerp(a, b, x):
    return a + (b - a) * x


def mix(c1, c2, x):
    return tuple(int(round(lerp(a, b, x))) for a, b in zip(c1, c2))


def canvas(color=CREAM):
    return Image.new("RGB", (W * S, H * S), color)


def finish(im):
    return im.reduce(S) if im.size[0] == W * S else im


def text(d, xy, s, f, fill=INK, anchor="la", alpha=1.0, bg=CREAM):
    """Draw text at OUTPUT coords; alpha fades toward bg colour (cheap, no RGBA)."""
    if alpha <= 0:
        return
    col = mix(bg, fill, alpha) if alpha < 1 else fill
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=col, anchor=anchor)


def text_w(s, f):
    return f.getlength(s) / S


def rise(d, xy, s, f, t, start, fill=INK, anchor="la", dur=0.6, dy=18, bg=CREAM):
    """Fade + rise-in text (Emil-style: short, eased, small distance)."""
    p = ease_out(prog(t, start, dur))
    if p <= 0:
        return
    text(d, (xy[0], xy[1] + (1 - p) * dy), s, f, fill, anchor, p, bg)


def rect(d, box, fill=None, outline=None, width=1, radius=0):
    b = [v * S for v in box]
    if radius:
        d.rounded_rectangle(b, radius * S, fill=fill, outline=outline, width=int(width * S))
    else:
        d.rectangle(b, fill=fill, outline=outline, width=int(width * S))


def circle(d, c, r, fill=None, outline=None, width=1):
    x, y = c
    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill, outline=outline,
              width=max(1, int(width * S)))


def line(d, pts, fill=INK, width=1):
    d.line([(x * S, y * S) for x, y in pts], fill=fill, width=max(1, int(width * S)), joint="curve")


def poly(d, pts, fill=None, outline=None):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill, outline=outline)


@lru_cache(None)
def photo(name):
    return Image.open(IMG / name).convert("RGB")


def cover(img, w, h, zoom=1.0, cx=0.5, cy=0.5):
    """Crop-to-fill at given zoom around (cx, cy) fractional focus; returns w x h image."""
    iw, ih = img.size
    scale = max(w / iw, h / ih) * zoom
    cw, ch = w / scale, h / scale
    x0 = clamp(cx * iw - cw / 2, 0, iw - cw)
    y0 = clamp(cy * ih - ch / 2, 0, ih - ch)
    return img.resize((w, h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def ball(d, c, r, rot=0.0, shadow=True):
    """A baseball: white disc, two red stitch seams (output coords)."""
    x, y = c
    if shadow:
        circle(d, (x + r * 0.12, y + r * 0.16), r, fill=(214, 208, 196))
    circle(d, (x, y), r, fill=(252, 251, 248), outline=(205, 200, 190), width=max(1, r / 22))
    for side in (-1, 1):
        pts = []
        for k in range(15):
            a = -1.0 + 2.0 * k / 14
            px = side * r * (0.55 + 0.18 * math.cos(a * 1.5)) * math.cos(a * 0.9)
            py = r * 0.78 * math.sin(a * 1.2)
            ca, sa = math.cos(rot), math.sin(rot)
            pts.append((x + px * ca - py * sa, y + px * sa + py * ca))
        line(d, pts, RED, max(1, r / 14))
        if r > 14:
            for k in range(1, 14, 2):
                (x1, y1), (x2, y2) = pts[k - 1], pts[k + 1]
                mx, my = pts[k]
                nx, ny = -(y2 - y1), (x2 - x1)
                n = math.hypot(nx, ny) or 1
                L = r * 0.07
                line(d, [(mx - nx / n * L, my - ny / n * L), (mx + nx / n * L, my + ny / n * L)], RED,
                     max(1, r / 22))


def fmt(n):
    return f"{n:,.0f}"
