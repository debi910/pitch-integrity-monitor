"""Judge-facing pitch deck (PDF) in the video's visual language. Numbers come from results/*.json.

    python deck.py            -> docs/pitch-deck.pdf (+ build/deck/*.png)
"""
import json

from PIL import ImageDraw

from common import *  # noqa: F401,F403
import scenes
from timeline import build

R = ROOT / "results"
LM = json.loads((R / "league_monitor.json").read_text())
WC = json.loads((R / "within_clase.json").read_text())["methods"]
PW = json.loads((R / "power.json").read_text())
TOTAL = 9


def chrome(im, n, dark=False):
    d = ImageDraw.Draw(im, "RGBA")
    col = (236, 230, 218) if dark else MUTED
    text(d, (60, 1030), "PITCH INTEGRITY MONITOR  ·  AQX SPORTS ANALYTICS DATA BOWL 4.0", font("mono", 16, 500), col,
         "lm", bg=INK if dark else CREAM)
    text(d, (W - 60, 1030), f"{n} / {TOTAL}", font("mono", 16, 500), col, "rm", bg=INK if dark else CREAM)
    f = font("mono", 15, 600)
    s = "ALLEGATIONS, NOT FINDINGS"
    w = text_w(s, f)
    rect(d, (W - 60 - w - 50, 30, W - 60, 66), fill=(255, 255, 255, 34) if dark else (22, 24, 28, 14), radius=18)
    circle(d, (W - 60 - w - 30, 48), 5, fill=AMBER)
    d.text(((W - 60 - w - 16) * S, 48 * S), s, font=f, fill=(236, 230, 218) if dark else INK2, anchor="lm")
    return im


def heading(d, kicker, title, y=110):
    text(d, (110, y), kicker, font("mono", 22, 600), AMBER)
    text(d, (106, y + 40), title, font("serif", 72), INK)


def bullets(d, items, x, y, size=30, gap=62, width=None):
    for i, s in enumerate(items):
        circle(d, (x + 8, y + i * gap + size * 0.62), 5, fill=RED)
        text(d, (x + 32, y + i * gap), s, font("sans", size, 500), INK)


def slide_title():
    im = scenes.photo_frame(scenes.stadium(), 1, 1, 1.06, 1.06, 0.6, 0.72, 0.7)
    d = ImageDraw.Draw(im)
    text(d, (120, 300), "Can pitch data catch", font("serif", 120), CREAM, bg=INK)
    text(d, (120, 430), "a rigged pitch?", font("serif-i", 120), (240, 200, 120), bg=INK)
    text(d, (124, 600), "A pitcher-relative integrity monitor, tested on the 18 pitches federal prosecutors say were "
         "sold to bettors", font("sans", 30, 500), (230, 224, 210), bg=INK)
    text(d, (124, 644), "and on every MLB pitcher-month from 2023 to 2025.", font("sans", 30, 500), (230, 224, 210), bg=INK)
    text(d, (124, 760), "pitch-integrity-monitor-uzwappgttfxqom7nyrx2nyk.streamlit.app", font("mono", 24, 500), CREAM,
         bg=INK)
    text(d, (124, 800), "github.com/debi910/pitch-integrity-monitor", font("mono", 24, 500), (200, 196, 186), bg=INK)
    return chrome(im, 1, True)


def slide_problem():
    im = canvas()
    d = ImageDraw.Draw(im, "RGBA")
    heading(d, "THE PROBLEM", "A single pitch can now be bought.")
    bullets(d, [
        "Pitch-level prop bets (ball or strike, speed, type) let a pitcher sell one pitch, not a game.",
        "Nov 2025: two Cleveland pitchers charged. Sept 2026 filing names 18 pitches; $400,000+ allegedly won.",
        "Every detection so far came from the betting side: someone noticed strange money.",
        "Nobody had measured whether the performance data itself gives a fixer away,",
        "or how many innocent pitchers a performance alarm would also flag.",
    ], 110, 300, 30, 70)
    rect(d, (110, 690, 1810, 900), fill=(255, 255, 255), radius=22)
    text(d, (150, 720), "OUR TWO QUESTIONS", font("mono", 20, 600), AMBER, bg=(255, 255, 255))
    text(d, (150, 760), "1. Can public Statcast data reveal a fix?", font("serif", 52), INK, bg=(255, 255, 255))
    text(d, (150, 826), "2. What does the alarm cost in false alerts, league-wide?", font("serif-i", 52), RED,
         bg=(255, 255, 255))
    return chrome(im, 2)


def slide_data():
    im = canvas()
    d = ImageDraw.Draw(im, "RGBA")
    heading(d, "THE DATA", "Every MLB pitch, 2023–2025. All real.")
    stats_ = [(fmt(LM["n_pitches"]), "pitches scored (2.18M pulled)"), (fmt(LM["n_pitchers"]), "pitchers"),
              (fmt(LM["n_pitcher_months"]), "pitcher-months"), ("18 / 18", "court-named pitches matched 1:1")]
    for i, (v, lab) in enumerate(stats_):
        x = 110 + i * 440
        text(d, (x, 300), v, font("serif", 96), RED if i == 3 else INK)
        text(d, (x + 4, 420), lab, font("sans", 26, 500), INK2)
    rows = [("Baseball Savant Statcast", "via pybaseball, polite monthly pulls", "MLBAM terms, research use"),
            ("Sept 18 2026 EDNY filing (25-CR-346)", "18 pitches: date, inning, batter, pitch #", "Public record, allegations"),
            ("DOJ press release, Nov 2025", "charges, scheme description, Ortiz games", "Public record")]
    y = 560
    for c, h in zip((110, 760, 1360), ("SOURCE", "WHAT", "TERMS")):
        text(d, (c, y), h, font("mono", 18, 600), MUTED)
    for j, r in enumerate(rows):
        yy = y + 50 + j * 70
        line(d, [(110, yy - 14), (1810, yy - 14)], LINE, 1)
        for c, v in zip((110, 760, 1360), r):
            text(d, (c, yy), v, font("sans", 26, 500 if c > 110 else 600), INK)
    text(d, (110, 880), "Nothing simulated or mocked. Raw pulls stay local; slim parquet files are in the repo.",
         font("serif-i", 40), INK2)
    return chrome(im, 3)


def slide_method():
    im = canvas()
    d = ImageDraw.Draw(im, "RGBA")
    heading(d, "THE METHOD", "Judge each pitcher only against himself.")
    cards = [
        ("v1 · PER PITCH", "Is this pitch strange for him?",
         ["Location, pitch choice, velocity", "vs his own EARLIER games only", "Fisher-combined p-value",
          "Frozen in git 5fa3b3e before labels"]),
        ("v2 · PATTERN MONITOR", "Has his rate jumped?",
         ["Template from the indictment's text:", "first pitch, taken ball, in the dirt",
          "Binomial tail vs his own baseline,", "shrunk to the league; frozen 674637e"]),
        ("EVALUATION", "Honest, league-wide",
         ["Simple baselines beside ours", "False alarms on all 8,339 months", "Stress test: 27 settings",
          "Detection limit by injection"]),
    ]
    for i, (k, t, items) in enumerate(cards):
        x = 110 + i * 580
        rect(d, (x, 280, x + 540, 860), fill=(255, 255, 255), radius=22)
        text(d, (x + 36, 316), k, font("mono", 20, 600), AMBER, bg=(255, 255, 255))
        text(d, (x + 36, 360), t, font("serif", 46), INK, bg=(255, 255, 255))
        for j, s in enumerate(items):
            text(d, (x + 36, 470 + j * 74), s, font("sans", 25, 500), INK2, bg=(255, 255, 255))
    text(d, (110, 900), "Code computes, nothing guesses: no LLM in the pipeline, every number reproducible with `make evals`.",
         font("sans", 26, 500), INK2)
    return chrome(im, 4)


def from_scene(key, frac, n):
    tl, _ = build()
    D = tl[key]["dur"]
    im = scenes.SCENES[key](D * frac, D)
    return chrome(im, n)


def slide_power():
    im = canvas()
    d = ImageDraw.Draw(im, "RGBA")
    heading(d, "DETECTION LIMIT", "How many rigged pitches can the data see?")
    g = PW["groups"]
    series = [("Relievers (20–59 first pitches / month)", g["light (20-59 batters/month, mostly relievers)"]["binomial"], RED),
              ("Starters (60+)", g["heavy (60+ batters/month, mostly starters)"]["binomial"], INK2)]
    x0, y0, w, h = 200, 860, 1000, 520
    line(d, [(x0, y0), (x0 + w, y0)], INK, 2)
    line(d, [(x0, y0), (x0, y0 - h)], INK, 2)
    for v in (0.25, 0.5, 0.75, 1.0):
        y = y0 - h * v
        line(d, [(x0, y), (x0 + w, y)], LINE, 1)
        text(d, (x0 - 14, y), f"{int(v * 100)}%", font("mono", 18, 500), MUTED, "rm")
    rs = PW["r"]
    for r in rs[::3]:
        text(d, (x0 + w * r / rs[-1], y0 + 14), str(r), font("mono", 18, 500), MUTED, "ma")
    text(d, (x0 + w / 2, y0 + 50), "rigged first pitches planted in one month", font("sans", 22, 500), INK2, "ma")
    text(d, (x0 - 10, y0 - h - 40), "chance the frozen monitor alerts", font("sans", 22, 500), INK2)
    for lab, ys, col in series:
        pts = [(x0 + w * r / rs[-1], y0 - h * v) for r, v in zip(rs, ys)]
        line(d, pts, col, 5)
        for p in pts:
            circle(d, p, 5, fill=col)
    for i, (lab, ys, col) in enumerate(series):
        circle(d, (1290, 370 + i * 50), 8, fill=col)
        text(d, (1310, 370 + i * 50), lab, font("sans", 24, 600), INK, "lm")
    rl = g["light (20-59 batters/month, mostly relievers)"]
    rh = g["heavy (60+ batters/month, mostly starters)"]
    text(d, (1290, 500), f"~{rl['r50_binomial']} a month", font("serif", 80), RED)
    text(d, (1294, 600), "for a 50% chance to catch a reliever", font("sans", 24, 500), INK2)
    text(d, (1290, 660), f"~{rh['r50_binomial']} a month", font("serif", 80), INK)
    text(d, (1294, 760), "for a starter", font("sans", 24, 500), INK2)
    text(d, (1290, 830), "Label-free: planted into real months,", font("sans", 22, 500), MUTED)
    text(d, (1290, 862), "alert at the same ~1/month threshold.", font("sans", 22, 500), MUTED)
    return chrome(im, 7)


def slide_use():
    im = canvas()
    d = ImageDraw.Draw(im, "RGBA")
    heading(d, "WHO USES IT", "A review list for an integrity analyst.")
    steps = [("1", "Monthly run", "python -m pim season.csv"),
             ("2", "Ranked list", "~1 alert a month, MLB-wide"),
             ("3", "Analyst review", "pitches, video, betting data"),
             ("4", "Decision", "humans, with betting evidence")]
    for i, (n, t, s) in enumerate(steps):
        x = 110 + i * 440
        circle(d, (x + 36, 330), 36, fill=INK)
        text(d, (x + 36, 330), n, font("serif", 44), CREAM, "mm", bg=INK)
        text(d, (x, 390), t, font("serif", 46), INK)
        text(d, (x, 452), s, font("sans", 22, 500), INK2)
        if i < 3:
            line(d, [(x + 90, 330), (x + 400, 330)], LINE, 3)
    text(d, (110, 560), "USERS", font("mono", 20, 600), AMBER)
    bullets(d, ["League integrity offices", "Sportsbook integrity desks", "Gaming regulators"], 110, 600, 28, 54)
    text(d, (960, 560), "NEXT", font("mono", 20, 600), AMBER)
    bullets(d, ["Velocity and pitch-type monitors (other prop markets)", "Join with betting-volume data for a two-sided alert",
                "Minor leagues and other pitch-tracking sports", "Pilot with one integrity desk, measure analyst time"],
            960, 600, 28, 54)
    text(d, (110, 880), "Ships as: live web app · CLI · Docker image · tested Python module · CI on every push",
         font("sans", 26, 600), INK)
    return chrome(im, 8)


def slide_limits():
    im = canvas()
    d = ImageDraw.Draw(im, "RGBA")
    heading(d, "WHERE IT STOPS", "Honest limits.")
    bullets(d, [
        "It never outputs “rigged”. It ranks what is unusual for this pitcher.",
        f"Single pitches: our frozen model lost to a one-line rule (AP {WC['PIM (ours)']['avg_precision']:.2f} vs "
        f"{WC['B1 spiked-ball rule']['avg_precision']:.2f}). Reported, not hidden.",
        "Caught 1 of 7 named months: sparse fixes do not move a monthly rate.",
        "Bets on speed or pitch type leave no trace in location.",
        "Labels are allegations; 18 positives make every interval wide.",
        "Other pitchers who trigger alerts are never named.",
    ], 110, 290, 30, 78)
    text(d, (110, 820), "Both pitchers have pleaded not guilty; trial set for November 2026.", font("serif-i", 44), RED)
    return chrome(im, 9)


def main():
    out = BUILD / "deck"
    out.mkdir(parents=True, exist_ok=True)
    slides = [slide_title(), slide_problem(), slide_data(), slide_method(),
              from_scene("s5", 0.98, 5), from_scene("s7", 0.98, 6), slide_power(), slide_use(), slide_limits()]
    imgs = []
    for i, s in enumerate(slides, 1):
        im = finish(s)
        im.save(out / f"slide_{i}.png")
        imgs.append(im.convert("RGB"))
    pdf = ROOT / "docs" / "pitch-deck.pdf"
    imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=144, quality=88)
    print(pdf, f"{pdf.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
