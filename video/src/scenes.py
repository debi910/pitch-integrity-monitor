"""The nine scenes + end card. Each takes scene-local time t (s) and duration D and returns a 2x canvas."""
import json
import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from common import *  # noqa: F401,F403
from field3d import Camera, lerp_cam, trajectory, field_polys, PLATE, RUBBER, PLATE_Y, BALL_R
from timeline import cue

DATA = json.loads((BUILD / "data.json").read_text())
FIELD_COL = {"grass": GRASS, "grass2": GRASS2, "dirt": DIRT}


# ---------------------------------------------------------------- photos

@lru_cache(None)
def stadium():
    """Hero photo, 16:9, tilt-shift: everything outside the diamond (signage, scoreboard, logos) blurred out."""
    im = photo("hero.jpg")
    im = im.crop((0, 150, 1800, 1162))
    sharp = im
    soft = im.filter(ImageFilter.GaussianBlur(22))
    mask = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([600, 560, 1520, 990], fill=255)          # the diamond (in crop coords)
    mask = mask.filter(ImageFilter.GaussianBlur(70))
    out = Image.composite(sharp, soft, mask)
    out = ImageEnhance.Color(out).enhance(0.85)
    return out


def photo_frame(name_img, t, D, z0=1.0, z1=1.12, cx=0.58, cy=0.66, dark=0.45):
    z = lerp(z0, z1, ease(t / D))
    im = cover(name_img, W * S, H * S, z, cx, cy)
    shade = Image.new("RGB", im.size, INK)
    grad = Image.linear_gradient("L").resize(im.size)              # 0 top -> 255 bottom
    grad = grad.point(lambda v: int(dark * 255 * (0.35 + 0.65 * v / 255)))
    return Image.composite(shade, im, grad)


# ---------------------------------------------------------------- S1  opener over the ballpark

def s1(t, D):
    im = photo_frame(stadium(), t, D, 1.0, 1.14, 0.6, 0.72, 0.62)
    d = ImageDraw.Draw(im)
    bg = INK
    rise(d, (120, 170), "OCTOBER 5, 2024  ·  ALDS GAME 1  ·  CLEVELAND", font("mono", 26, 500), t, 0.3,
         fill=(240, 200, 120), bg=bg)
    c1 = cue("s1", "ninth", default=3.0)
    rise(d, (114, 230), "Ninth inning.", font("serif", 132), t, c1 - 0.2, fill=CREAM, bg=bg, dy=26)
    rise(d, (114, 370), "Seven to nothing.", font("serif-i", 132), t, cue("s1", "seven", default=4) - 0.1,
         fill=(236, 226, 206), bg=bg, dy=26)
    # score chip
    p = ease_out(prog(t, cue("s1", "seven", default=4) + 0.4, 0.5))
    if p > 0:
        x, y = 120, 560 + (1 - p) * 14
        rect(d, (x, y, x + 300, y + 64), fill=mix(bg, (36, 38, 44), p), radius=12)
        text(d, (x + 24, y + 32), "CLE  7", font("mono", 30, 600), CREAM, "lm", p, bg)
        text(d, (x + 160, y + 32), "DET  0", font("mono", 30, 400), (170, 170, 170), "lm", p, bg)
    c2 = cue("s1", "first", default=6.5)
    rise(d, (120, 680), "Clase, first pitch to Matt Vierling.", font("sans", 40, 500), t, c2 - 0.1,
         fill=CREAM, bg=bg)
    c3 = cue("s1", "dirt", default=9)
    p = ease_out(prog(t, c3 - 0.2, 0.5))
    if p > 0:
        rect(d, (120, 744, 120 + 380 * p, 750), fill=RED)
        rise(d, (120, 770), "93.1 mph slider  ·  in the dirt", font("mono", 28, 500), t, c3, fill=(240, 160, 150),
             bg=bg)
    c4 = cue("s1", "nobody", default=10.5)
    rise(d, (120, 830), "Nobody blinks.", font("serif-i", 64), t, c4, fill=(240, 200, 120), bg=bg)
    return im


# ---------------------------------------------------------------- S2  the 3D pitch from Statcast

TRAJ = trajectory(DATA["vierling"], 140, bounce=True)
GHOSTS = [trajectory(g, 60)[1] for g in DATA["ghosts"]]
CAM_A = ((-46, 8, 24), (0, 34, 2))
CAM_B = ((1.2, -19, 6.2), (0.2, 22, 0.6))


def draw_field(d, cam):
    for pts, key in field_polys():
        sp = cam.poly(pts)
        if sp:
            poly(d, sp, fill=FIELD_COL[key])
    # foul lines
    for sx in (-1, 1):
        a = cam.project([(0, 0, 0.01), (sx * 160, 160, 0.01)])
        line(d, [tuple(a[0]), tuple(a[1])], (250, 248, 242), 2)
    for shape, col in ((PLATE, (252, 251, 248)), (RUBBER, (252, 251, 248))):
        sp = cam.poly(shape)
        if sp:
            poly(d, sp, fill=col)


def zone_box(k):
    return [(-0.83, 0.708, k["sz_bot"]), (0.83, 0.708, k["sz_bot"]), (0.83, 0.708, k["sz_top"]),
            (-0.83, 0.708, k["sz_top"])]


def s2(t, D):
    im = canvas(CREAM)
    d = ImageDraw.Draw(im, "RGBA")
    # sky band
    rect(d, (0, 0, W, H), fill=CREAM)
    x = ease(prog(t, 0.0, 3.0))
    drift = 0.6 * math.sin(t * 0.35)
    cam = lerp_cam((CAM_A[0], CAM_A[1]), ((CAM_B[0][0] + drift, CAM_B[0][1], CAM_B[0][2]), CAM_B[1]), x, 1300, 1800)
    cam.cx = 760
    draw_field(d, cam)

    k = DATA["vierling"]
    # ghost slider paths: his other first-pitch sliders
    ga = ease(prog(t, 1.4, 1.2))
    if ga > 0:
        for g in GHOSTS:
            sp = cam.project(g)
            line(d, [tuple(p) for p in sp], (46, 125, 91, int(70 * ga)), 2)
    # strike zone
    zb = cam.poly(zone_box(k))
    if zb:
        poly(d, zb, fill=(22, 24, 28, 18), outline=None)
        line(d, zb + [zb[0]], (22, 24, 28, 200), 2)

    ts, pts, hit = TRAJ
    t0, fl = 3.0, 2.8                               # flight starts at 3s, lasts 2.8s on screen
    p = clamp((t - t0) / fl)
    n = len(pts)
    if t >= t0:
        i = int(p * (n - 1))
        sp = cam.project(pts[: i + 1])
        if i > 0:
            line(d, [tuple(q) for q in sp], (200, 50, 43, 230), 5)
        # shadow on ground
        sh = cam.project([(pts[i][0], pts[i][1], 0.01)])[0]
        sr = max(2, cam.scale(pts[i]) * BALL_R * 1.6)
        d.ellipse([(sh[0] - sr) * S, (sh[1] - sr * 0.35) * S, (sh[0] + sr) * S, (sh[1] + sr * 0.35) * S],
                  fill=(120, 96, 70, 90))
        bp = sp[-1] if i > 0 else cam.project([pts[0]])[0]
        r = max(3, cam.scale(pts[i]) * BALL_R * 1.6)
        ball(d, tuple(bp), r, rot=t * 9, shadow=False)
        # impact puff
        if hit is not None and i >= hit:
            g = cam.project([pts[hit]])[0]
            age = (i - hit) / max(1, n - hit)
            for j in range(3):
                rr = (18 + 60 * (age + j * 0.12)) * (cam.scale(pts[hit]) / 160)
                a = int(120 * (1 - min(1, age + j * 0.2)))
                if a > 0:
                    d.ellipse([(g[0] - rr) * S, (g[1] - rr * 0.3) * S, (g[0] + rr) * S, (g[1] + rr * 0.3) * S],
                              outline=(150, 110, 70, a), width=3 * S)
    # HUD
    hx = 1330
    a = ease_out(prog(t, t0 + fl - 0.3, 0.5))
    if a > 0:
        rows = [("PITCH", "Slider"), ("SPEED", f"{k['release_speed']:.1f} mph"),
                ("CROSSES AT", f"{k['plate_z']:+.2f} ft".replace("-", "−")),
                ("ZONE BOTTOM", f"{k['sz_bot']:.2f} ft"), ("RESULT", "Ball, in the dirt")]
        rect(d, (hx - 30, 150, hx + 500, 150 + 70 + len(rows) * 74), fill=(255, 255, 255, int(235 * a)), radius=18)
        text(d, (hx, 178), "STATCAST · OCT 5 2024 · 9TH", font("mono", 20, 500), MUTED, alpha=a, bg=(255, 255, 255))
        for j, (lab, val) in enumerate(rows):
            aj = ease_out(prog(t, t0 + fl - 0.2 + j * 0.12, 0.4))
            y = 228 + j * 74
            text(d, (hx, y), lab, font("mono", 18, 500), MUTED, alpha=aj, bg=(255, 255, 255))
            text(d, (hx, y + 24), val, font("sans", 34, 600), RED if j in (2, 4) else INK, alpha=aj,
                 bg=(255, 255, 255))
    # legend
    if ga > 0:
        line(d, [(96, 1000 - 70), (136, 1000 - 70)], (46, 125, 91, int(180 * ga)), 3)
        text(d, (148, 930), "his other first-pitch sliders (Statcast)", font("sans", 22, 500), GREEN, "lm", ga)
    # narration cards
    c18 = cue("s2", "eighteen", default=3.5)
    cards = [(c18, "1 of 18", "pitches prosecutors say were sold"),
             (cue("s2", "four", default=7), "$400,000+", "allegedly won by bettors"),
             (cue("s2", "pleaded", default=10), "Not guilty", "both pitchers' pleas")]
    for j, (ct, big, small) in enumerate(cards):
        a = ease_out(prog(t, ct - 0.1, 0.5))
        if a <= 0:
            continue
        y = 640 + j * 96
        x = 1270 + (1 - a) * 24
        rect(d, (x, y, x + 590, y + 84), fill=(22, 24, 28, int(235 * a)), radius=14)
        text(d, (x + 26, y + 42), big, font("serif", 46), (240, 200, 120), "lm", a, INK)
        text(d, (x + 215, y + 42), small, font("sans", 21, 500), CREAM, "lm", a, INK)
    return im


# ---------------------------------------------------------------- S3  the problem

BETS = [("Pitch 1 · Ball", "+105"), ("Pitch 1 · 95+ mph", "-120"), ("Pitch 1 · Strike", "-140"),
        ("Pitch 2 · Ball", "+110"), ("Pitch 1 · Slider", "+150"), ("Pitch 3 · In play", "+300")]


def s3(t, D):
    im = canvas(CREAM)
    d = ImageDraw.Draw(im, "RGBA")
    # left card: betting side
    a = ease_out(prog(t, 0.2, 0.6))
    x0, y0 = 110, 150
    rect(d, (x0, y0 + (1 - a) * 20, x0 + 760, y0 + 520), fill=(255, 255, 255, int(255 * a)), radius=22)
    text(d, (x0 + 40, y0 + 40), "THE BETTING SIDE", font("mono", 22, 600), AMBER, alpha=a, bg=(255, 255, 255))
    text(d, (x0 + 40, y0 + 80), "Pitch-level prop markets", font("serif", 52), INK, alpha=a, bg=(255, 255, 255))
    for j, (lab, odds) in enumerate(BETS):
        aj = ease_out(prog(t, 0.6 + j * 0.15, 0.4))
        y = y0 + 170 + j * 50
        hot = j == 0
        if hot:
            pulse = 0.5 + 0.5 * math.sin(t * 6)
            ha = ease_out(prog(t, cue("s3", "strange", default=3), 0.4))
            if ha > 0:
                rect(d, (x0 + 26, y - 8, x0 + 734, y + 38), fill=(200, 50, 43, int((40 + 40 * pulse) * ha)),
                     radius=10)
        text(d, (x0 + 40, y), lab, font("sans", 26, 500), INK, alpha=aj, bg=(255, 255, 255))
        text(d, (x0 + 520, y), odds, font("mono", 26, 500), INK2, alpha=aj, bg=(255, 255, 255))
        vol = [0.92, 0.18, 0.22, 0.12, 0.16, 0.08][j]
        grow = ease_out(prog(t, 1.2 + j * 0.1, 1.2))
        if hot:
            grow *= 0.3 + 0.7 * ease_out(prog(t, cue("s3", "strange", default=3) - 0.3, 0.8))
        rect(d, (x0 + 630, y + 6, x0 + 630 + 90 * vol * grow, y + 24), fill=RED if hot else (205, 200, 190))
    ha = ease_out(prog(t, cue("s3", "strange", default=3) + 0.2, 0.4))
    if ha > 0:
        rect(d, (x0 + 40, y0 + 470 - 6, x0 + 360, y0 + 470 + 36), fill=(200, 50, 43, int(255 * ha)), radius=18)
        text(d, (x0 + 60, y0 + 470 + 15), "ALERT · unusual money", font("mono", 20, 600), CREAM, "lm", ha, RED)

    # right card: performance side (photo)
    cq = cue("s3", "different", default=5)
    b = ease_out(prog(t, cq - 0.3, 0.7))
    if b > 0:
        x1, y1, w1, h1 = 960, 150, 850, 520
        ph = cover(photo("pitcher.jpg"), int(w1 * S), int(h1 * S), lerp(1.12, 1.0, ease(prog(t, cq, D - cq))),
                   0.5, 0.55)
        ph = ImageEnhance.Color(ph).enhance(0.8)
        mask = Image.new("L", ph.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, ph.size[0], ph.size[1]], 22 * S, fill=int(255 * b))
        im.paste(ph, (int(x1 * S), int((y1 + (1 - b) * 24) * S)), mask)
        d = ImageDraw.Draw(im, "RGBA")
        rect(d, (x1 + 30, y1 + 30, x1 + 400, y1 + 76), fill=(22, 24, 28, int(220 * b)), radius=12)
        text(d, (x1 + 50, y1 + 53), "THE PERFORMANCE SIDE", font("mono", 22, 600), (240, 200, 120), "lm", b, INK)
        # tracking dots overlay
        rng = random.Random(4)
        for j in range(26):
            px = x1 + 80 + rng.random() * (w1 - 160)
            py = y1 + 120 + rng.random() * (h1 - 200)
            aj = ease_out(prog(t, cq + 0.3 + j * 0.05, 0.3))
            if aj > 0:
                circle(d, (px, py), 5, fill=(255, 255, 255, int(200 * aj)))
                circle(d, (px, py), 11, outline=(255, 255, 255, int(110 * aj)), width=1.5)
    # questions
    q1 = cue("s3", "can", default=7)
    rise(d, (110, 730), "Can the pitch data itself reveal a fix?", font("serif", 74), t, q1 - 0.1, dy=22)
    q2 = cue("s3", "innocent", default=10) - 0.6
    rise(d, (110, 830), "And how many innocent pitchers would it flag?", font("serif-i", 58), t, q2, fill=RED,
         dy=22)
    return im


# ---------------------------------------------------------------- S4  the data

def s4(t, D):
    im = canvas(CREAM)
    d = ImageDraw.Draw(im, "RGBA")
    lm = DATA["league_monitor"]
    N = lm["n_pitches"]
    # dot cloud: real 2025 pitch locations, catcher's view
    zx, zy, sc = 470, 560, 125                 # plate centre on screen, px per foot
    pc = ease(prog(t, 0.3, 4.5))
    cloud = DATA["cloud"]
    k = int(len(cloud) * pc)
    for j in range(k):
        x, z = cloud[j]
        sx, sy = zx + x * sc, zy - (z - 2.5) * sc
        if 60 < sx < 880 and 120 < sy < 870:
            col = (200, 50, 43, 110) if z < 0.6 else (46, 125, 91, 60)
            d.rectangle([(sx - 1.6) * S, (sy - 1.6) * S, (sx + 1.6) * S, (sy + 1.6) * S], fill=col)
    a = ease_out(prog(t, 0.2, 0.6))
    rect(d, (zx - 0.83 * sc, zy - 0.9 * sc, zx + 0.83 * sc, zy + 0.95 * sc), outline=(22, 24, 28, int(200 * a)),
         width=2.5)
    text(d, (zx, 890), "Where pitches crossed the plate (2025 sample, catcher's view)", font("sans", 20, 500), INK2, "ma", a)
    circle(d, (zx - 150, 935), 5, fill=RED)
    text(d, (zx - 136, 935), "in the dirt", font("sans", 20, 500), RED, "lm", a)

    # counter
    cnt = int(N * ease_out(prog(t, 0.4, 3.6)))
    rise(d, (980, 200), "EVERY MLB PITCH · 2023–2025", font("mono", 24, 600), t, 0.2, fill=AMBER)
    text(d, (976, 250), fmt(cnt), font("serif", 150), INK, alpha=ease_out(prog(t, 0.3, 0.4)))
    rise(d, (984, 430), f"pitches  ·  {fmt(lm['n_pitchers'])} pitchers  ·  {fmt(lm['n_pitcher_months'])} pitcher-months",
         font("sans", 28, 500), t, 2.0, fill=INK2)
    # matched labels
    cm = cue("s4", "matched", default=6.5)
    rise(d, (984, 520), "18 of 18 court-named pitches matched 1:1", font("sans", 34, 600), t, cm - 0.2, fill=INK)
    named = DATA["named"]
    for j, r in enumerate(named):
        aj = ease_out(prog(t, cm + 0.1 + j * 0.09, 0.35))
        if aj <= 0:
            continue
        col, row = j // 9, j % 9
        x, y = 984 + col * 440, 590 + row * 38
        circle(d, (x + 10, y + 12), 10, fill=(46, 125, 91, int(255 * aj)))
        line(d, [(x + 5, y + 12), (x + 9, y + 16), (x + 16, y + 7)], (255, 255, 255, int(255 * aj)), 2.5)
        text(d, (x + 32, y), f"{r['game_date']}  {r['batter_name']}", font("mono", 20, 500), INK, alpha=aj)
    return im


# ---------------------------------------------------------------- S5  single pitches: the honest loss

def s5(t, D):
    im = canvas(CREAM)
    d = ImageDraw.Draw(im, "RGBA")
    flags, nb = DATA["waffle_flags"], DATA["waffle_notball"]
    cols, cell, gap = 76, 11, 3
    x0, y0 = 100, 300
    rise(d, (100, 150), "RESULT 1 · SINGLE PITCHES", font("mono", 24, 600), t, 0.1, fill=AMBER)
    rise(d, (100, 190), "All 2,972 Clase pitches. 18 named.", font("serif", 64), t, 0.3)
    nbt = cue("s5", "six", default=14)
    for j, f in enumerate(flags):
        r, c = divmod(j, cols)
        appear = 0.4 + (c + r) * 0.012
        a = prog(t, appear, 0.25)
        if a <= 0:
            continue
        x, y = x0 + c * (cell + gap), y0 + r * (cell + gap)
        if f:
            pulse = 1 + 0.25 * max(0, math.sin((t - 2.0) * 3)) if t > 2 else 1
            g = (pulse - 1) * 6
            hollow = nb[j] and t > nbt
            if hollow:
                rect(d, (x - g, y - g, x + cell + g, y + cell + g), outline=RED, width=2)
            else:
                rect(d, (x - g, y - g, x + cell + g, y + cell + g), fill=RED)
        else:
            rect(d, (x, y, x + cell, y + cell), fill=mix(CREAM, (214, 208, 196), a))
    # git lock chip
    lk = cue("s5", "locked", default=2)
    a = spring(prog(t, lk - 0.1, 0.5))
    if a > 0:
        x, y = 100, 880
        rect(d, (x, y, x + 470, y + 56), fill=INK, radius=28)
        rect(d, (x + 24, y + 22, x + 46, y + 40), fill=(240, 200, 120), radius=3)
        d.arc([(x + 27) * S, (y + 12) * S, (x + 43) * S, (y + 30) * S], 180, 360, fill=(240, 200, 120), width=3 * S)
        text(d, (x + 64, y + 28), "model frozen in git · 5fa3b3e", font("mono", 22, 500), CREAM, "lm", min(1, a), INK)
    # AP bars
    wc = DATA["within_clase"]["methods"]
    bars = [("Our model", wc["PIM (ours)"]["avg_precision"], INK2),
            ("One-line rule: spiked ball", wc["B1 spiked-ball rule"]["avg_precision"], AMBER),
            ("Random", wc["B3 random"]["avg_precision"], (190, 185, 175))]
    lost = cue("s5", "lost", default=5)
    bx, by, bw = 1240, 330, 560
    rise(d, (bx, by - 50), "AVERAGE PRECISION (higher is better)", font("mono", 20, 600), t, lost - 0.4, fill=MUTED)
    for j, (lab, v, col) in enumerate(bars):
        p = ease_out(prog(t, lost - 0.2 + j * 0.25, 1.0))
        if p <= 0:
            continue
        y = by + j * 120
        text(d, (bx, y), lab, font("sans", 28, 600 if j < 2 else 500), INK, alpha=p)
        rect(d, (bx, y + 44, bx + bw * (v / 0.25) * p, y + 84), fill=col, radius=6)
        text(d, (bx + bw * (v / 0.25) * p + 14, y + 64), f"{v * p:.2f}", font("mono", 30, 600), INK, "lm", p)
    rise(d, (bx, 720), "A rigged ball in the dirt", font("serif", 46), t, cue("s5", "rigged", default=10) - 0.1)
    rise(d, (bx, 772), "looks like an ordinary miss.", font("serif-i", 46), t, cue("s5", "ordinary", default=11) - 0.2,
         fill=INK2)
    a = ease_out(prog(t, nbt - 0.1, 0.4))
    if a > 0:
        rect(d, (bx, 850, bx + 26, 876), outline=RED, width=2.5)
        text(d, (bx + 40, 863), "6 of 18 were not even balls", font("sans", 28, 600), RED, "lm", a)
    return im


# ---------------------------------------------------------------- S6  the monthly pattern

def s6(t, D):
    im = canvas(CREAM)
    d = ImageDraw.Draw(im, "RGBA")
    rise(d, (110, 140), "RESULT 2 · THE PATTERN", font("mono", 24, 600), t, 0.1, fill=AMBER)
    rise(d, (110, 180), "First pitch of an at-bat, in the dirt, taken for a ball.", font("serif", 58), t, 0.4)
    rise(d, (112, 260), "Clase's monthly rate vs his own baseline", font("sans", 28, 500), t, 1.2, fill=INK2)
    months = DATA["clase_months"]
    x0, y0, w, h = 150, 840, 1480, 470          # baseline y0 is the x-axis
    ymax = 0.25
    a = ease_out(prog(t, 0.6, 0.6))
    line(d, [(x0, y0), (x0 + w, y0)], mix(CREAM, INK, a), 2)
    for v in (0.05, 0.10, 0.15, 0.20):
        y = y0 - h * v / ymax
        line(d, [(x0, y), (x0 + w, y)], mix(CREAM, LINE, a), 1)
        text(d, (x0 - 16, y), f"{int(v * 100)}%", font("mono", 18, 500), MUTED, "rm", a)
    n = len(months)
    bw = w / n
    may = cue("s6", "may", default=7)
    for j, m in enumerate(months):
        p = ease_out(prog(t, 1.4 + j * 0.12, 0.7))
        is_may = m["month"] == "2025-05"
        if is_may:
            p = ease_out(prog(t, may - 0.2, 1.0))
        if p <= 0:
            continue
        bh = h * m["rate"] / ymax * (spring(prog(t, may - 0.2, 0.9)) if is_may else p)
        x = x0 + j * bw + bw * 0.18
        col = RED if is_may else ((222, 160, 120) if m["label"] else (196, 190, 178))
        rect(d, (x, y0 - bh, x + bw * 0.64, y0), fill=col, radius=4)
        text(d, (x + bw * 0.32, y0 + 14), m["month"][2:].replace("-", "·"), font("mono", 16, 500), MUTED, "ma", p)
        if m["label"]:
            circle(d, (x + bw * 0.32, y0 + 48), 5, fill=RED if is_may else (222, 160, 120))
    # baseline (his own, rolling) as a step line
    pb = ease(prog(t, cue("s6", "own", default=3), 1.2))
    if pb > 0:
        pts = []
        for j, m in enumerate(months[: max(1, int(n * pb))]):
            y = y0 - h * m["base_audit"] / ymax
            pts += [(x0 + j * bw, y), (x0 + (j + 1) * bw, y)]
        for q in range(0, len(pts) - 1, 2):
            line(d, [pts[q], pts[q + 1]], INK, 3)
        text(d, (x0 + w + 12, y0 - h * months[-1]["base_audit"] / ymax), "his baseline", font("sans", 20, 600),
             INK, "lm", pb)
    # callout
    a = ease_out(prog(t, cue("s6", "nine", default=8) - 0.1, 0.5))
    if a > 0:
        j = [m["month"] for m in months].index("2025-05")
        m = months[j]
        x = x0 + j * bw + bw * 0.5
        y = y0 - h * m["rate"] / ymax
        cx, cy = x - 520, y - 40
        rect(d, (cx, cy - 10, cx + 420, cy + 120), fill=(22, 24, 28, int(240 * a)), radius=16)
        text(d, (cx + 24, cy + 6), "MAY 2025", font("mono", 20, 600), (240, 200, 120), alpha=a, bg=INK)
        text(d, (cx + 24, cy + 36), f"{m['k']} of {m['n']} first pitches", font("sans", 30, 600), CREAM, alpha=a, bg=INK)
        text(d, (cx + 24, cy + 76), f"{m['rate'] * 100:.0f}% vs his {m['base_audit'] * 100:.1f}%", font("mono", 24, 500),
             (240, 160, 150), alpha=a, bg=INK)
        line(d, [(cx + 420, cy + 55), (x - 20, y + 10)], (22, 24, 28, int(200 * a)), 2)
    rise(d, (x0 + 30, 940), "●  named months in the court filing", font("sans", 20, 500), t, 2.0, fill=(200, 120, 90))
    return im


# ---------------------------------------------------------------- S7  the whole league

def _league_layout():
    L = DATA["league"]
    n = len(L["scores"])
    cols = 139
    rng = np.random.default_rng(11)
    order = rng.permutation(n)                  # random start positions
    start = np.zeros((n, 2))
    end = np.zeros((n, 2))
    for rank in range(n):
        r, c = divmod(rank, cols)
        end[rank] = (c, r)
        r2, c2 = divmod(int(order[rank]), cols)
        start[rank] = (c2, r2)
    return start, end


START, END_POS = _league_layout()


def s7(t, D):
    im = canvas(CREAM)
    d = ImageDraw.Draw(im, "RGBA")
    L, lm = DATA["league"], DATA["league_monitor"]
    rise(d, (100, 120), "EVERY PITCHER-MONTH IN BASEBALL, 2023–25", font("mono", 24, 600), t, 0.1, fill=AMBER)
    rise(d, (100, 160), f"{fmt(lm['n_pitcher_months'])} pitcher-months, sorted by the monitor", font("serif", 58), t, 0.3)
    x0, y0, sp = 100, 270, 9.0
    sort_p = ease(prog(t, 1.2, 2.6))
    n = len(L["scores"])
    flag_t = cue("s7", "alert", default=11)
    fa = ease_out(prog(t, flag_t - 0.3, 0.6))
    hit = 21                                   # rank 22 -> index 21
    for i in range(n):
        if i == hit:
            continue
        cx, cy = START[i] * (1 - sort_p) + END_POS[i] * sort_p
        x, y = x0 + cx * sp, y0 + cy * sp
        alert = L["scores"][i] >= 3.0
        col = (196, 190, 178)
        if alert and fa > 0:
            col = mix(col, AMBER, fa)
        d.rectangle([(x - 2.8) * S, (y - 2.8) * S, (x + 2.8) * S, (y + 2.8) * S], fill=col)
    cx, cy = START[hit] * (1 - sort_p) + END_POS[hit] * sort_p
    hx, hy = x0 + cx * sp, y0 + cy * sp
    pulse = 1 + 0.35 * abs(math.sin(t * 3))
    circle(d, (hx, hy), 6 * pulse, fill=RED)
    a = ease_out(prog(t, cue("s7", "twenty-second", default=cue("s7", "ranks", default=4)) - 0.2, 0.5))
    if a > 0:
        circle(d, (hx, hy), 18, outline=(200, 50, 43, int(255 * a)), width=2.5)
        line(d, [(hx + 14, hy + 14), (hx + 120, hy + 120)], (200, 50, 43, int(255 * a)), 2)
        rect(d, (hx + 120, hy + 100, hx + 520, hy + 176), fill=(22, 24, 28, int(240 * a)), radius=14)
        text(d, (hx + 144, hy + 116), "CLASE · MAY 2025", font("mono", 20, 600), (240, 200, 120), alpha=a, bg=INK)
        text(d, (hx + 144, hy + 142), f"#22 of {fmt(n)}", font("sans", 28, 700), CREAM, alpha=a, bg=INK)
    # rank comparison panel
    px = 1420
    ranks = [("Our monitor", lm["methods"]["score_audit"]["positive_ranks"]["Emmanuel Clase 2025-05"], RED),
             ("Raw monthly rate", lm["methods"]["baseline_rate"]["positive_ranks"]["Emmanuel Clase 2025-05"], INK2),
             ("Raw monthly count", lm["methods"]["baseline_count"]["positive_ranks"]["Emmanuel Clase 2025-05"], INK2)]
    ra = cue("s7", "ahead", default=7)
    rise(d, (px, 300), "RANK OF MAY 2025", font("mono", 20, 600), t, ra - 0.4, fill=MUTED)
    for j, (lab, rk, col) in enumerate(ranks):
        aj = ease_out(prog(t, ra - 0.2 + j * 0.3, 0.5))
        y = 350 + j * 100
        text(d, (px, y), lab, font("sans", 24, 500), INK, alpha=aj)
        text(d, (px, y + 30), f"#{rk}", font("serif", 58), col, alpha=aj)
    # alerts / month
    a = ease_out(prog(t, flag_t - 0.2, 0.5))
    if a > 0:
        al = lm["alerts"]["score_audit>=3.0"]
        rect(d, (px - 20, 670, px + 440, 790), fill=(255, 255, 255, int(255 * a)), radius=16)
        text(d, (px, 690), f"{al['per_month_league_wide']:.2f} alerts / month", font("serif", 46), AMBER, alpha=a,
             bg=(255, 255, 255))
        text(d, (px, 748), f"{al['flagged_cells']} in 3 seasons, whole league", font("sans", 22, 500), INK2, alpha=a,
             bg=(255, 255, 255))
    # live timeline
    lv = cue("s7", "live", default=14)
    a = ease_out(prog(t, lv - 0.2, 0.6))
    if a > 0:
        y = 860
        x1, x2 = 100, 1300
        line(d, [(x1, y), (x1 + (x2 - x1) * a, y)], INK, 2)
        pts = [(0.15, "May 2025", "9 of 41 in the dirt", INK2), (0.45, "June 1", "live monitor flags", RED),
               (0.85, "July 2025", "placed on leave", INK2)]
        for j, (fx, lab, sub, col) in enumerate(pts):
            aj = ease_out(prog(t, lv + j * 0.5, 0.4))
            if aj <= 0:
                continue
            x = x1 + (x2 - x1) * fx
            circle(d, (x, y), 9 if col == RED else 7, fill=col)
            text(d, (x, y - 46), lab, font("mono", 22, 600), col, "ma", aj)
            text(d, (x, y + 18), sub, font("sans", 22, 500), INK2, "ma", aj)
    return im


# ---------------------------------------------------------------- S8  limits

def s8(t, D):
    im = canvas(CREAM)
    d = ImageDraw.Draw(im, "RGBA")
    rise(d, (110, 170), "It is not magic.", font("serif", 120), t, 0.2)
    lm = DATA["league_monitor"]["methods"]["score_audit"]["positive_ranks"]
    items = list(lm.items())
    c = cue("s8", "caught", default=2)
    rise(d, (114, 330), "It caught 1 of 7 named months.", font("sans", 40, 600), t, c - 0.1, fill=INK2)
    for j, (name, rk) in enumerate(items):
        a = spring(prog(t, c + 0.2 + j * 0.15, 0.5))
        if a <= 0:
            continue
        x, y = 200 + j * 240, 560
        caught = rk <= 83                      # inside the top 1% (83 cells)
        r = 70 * min(1, a)
        if caught:
            circle(d, (x, y), r, fill=GREEN)
            line(d, [(x - 26, y), (x - 6, y + 20), (x + 28, y - 18)], CREAM, 8)
        else:
            circle(d, (x, y), r, outline=(196, 190, 178), width=4)
        who, mon = name.rsplit(" ", 1)
        text(d, (x, y + 96), mon, font("mono", 22, 600), INK if caught else MUTED, "ma", min(1, a))
        text(d, (x, y + 128), who.split()[-1], font("sans", 20, 500), INK2, "ma", min(1, a))
        text(d, (x, y + 160), f"rank #{rk:,}", font("mono", 20, 500), GREEN if caught else MUTED, "ma", min(1, a))
    sp = cue("s8", "sparse", default=6)
    rise(d, (114, 850), "Too few rigged pitches in a month to move the rate.", font("serif-i", 50), t, sp - 0.5,
         fill=RED)
    return im


# ---------------------------------------------------------------- S9  outro

def s9(t, D):
    im = photo_frame(stadium(), t, D, 1.12, 1.2, 0.55, 0.7, 0.78)
    im = im.filter(ImageFilter.GaussianBlur(6 * S * ease(prog(t, 0, 2.0))))
    d = ImageDraw.Draw(im)
    bg = INK
    rise(d, (W / 2, 250), "It never says “rigged”.", font("serif", 96), t, 0.3, fill=CREAM, anchor="ma", bg=bg)
    rise(d, (W / 2, 370), "It tells a human where to look.", font("serif-i", 80), t, cue("s9", "tells", default=2) - 0.1,
         fill=(240, 200, 120), anchor="ma", bg=bg)
    a = ease_out(prog(t, cue("s9", "pitch", default=4) - 0.2, 0.7))
    if a > 0:
        ball(d, (W / 2 - 330, 560), 34 * spring(prog(t, cue("s9", "pitch", default=4) - 0.2, 0.6)), rot=t, shadow=False)
        text(d, (W / 2 - 280, 560), "Pitch Integrity Monitor", font("serif", 84), CREAM, "lm", a, bg)
        text(d, (W / 2, 640), "Real data, honest limits.", font("sans", 34, 500), (220, 214, 200), "ma",
             ease_out(prog(t, cue("s9", "real", default=5.5) - 0.1, 0.5)), bg)
    a = ease_out(prog(t, cue("s9", "real", default=5.5) + 0.3, 0.6))
    if a > 0:
        text(d, (W / 2, 740), "pitch-integrity-monitor-uzwappgttfxqom7nyrx2nyk.streamlit.app", font("mono", 26, 500),
             CREAM, "ma", a, bg)
        text(d, (W / 2, 784), "github.com/debi910/pitch-integrity-monitor", font("mono", 26, 500), (200, 196, 186),
             "ma", a, bg)
    return im


# ---------------------------------------------------------------- end card

CREDITS = [
    ("DATA", "Baseball Savant / MLBAM Statcast via pybaseball, 2023–2025 (non-commercial research use)"),
    ("LABELS", "Allegations in the Sept 18 2026 EDNY filing (25-CR-346), as reported by Sports Betting Dime and TSN"),
    ("PHOTOS", "Jfvoll, CC BY-SA 4.0 · taka, CC BY-SA 3.0 · Frettie, CC BY 3.0 · Tage Olsin, CC BY-SA 2.0 (Wikimedia Commons)"),
    ("VOICE", "Microsoft neural text-to-speech (Andrew)"),
    ("MUSIC", "Original, synthesized for this video"),
    ("TYPE", "Instrument Serif, Inter, JetBrains Mono (SIL Open Font License)"),
]


def end(t, D):
    im = canvas(CREAM)
    d = ImageDraw.Draw(im)
    rise(d, (W / 2, 190), "Pitch Integrity Monitor", font("serif", 80), t, 0.1, anchor="ma")
    rise(d, (W / 2, 300), "AQX SPORTS ANALYTICS DATA BOWL 4.0", font("mono", 24, 600), t, 0.3, fill=AMBER, anchor="ma")
    for j, (k, v) in enumerate(CREDITS):
        y = 420 + j * 62
        rise(d, (360, y), k, font("mono", 20, 600), t, 0.5 + j * 0.08, fill=MUTED)
        rise(d, (500, y), v, font("sans", 24, 500), t, 0.5 + j * 0.08, fill=INK)
    rise(d, (W / 2, 850), "Allegations, not findings. Both pitchers have pleaded not guilty.", font("serif-i", 40), t,
         1.0, fill=RED, anchor="ma")
    return im


SCENES = {"s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7, "s8": s8, "s9": s9, "end": end}
DARK = {"s1", "s9"}
