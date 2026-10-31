"""Screenshots of the story page (docs/index.html) for the Devpost gallery, 3:2 at 1500x1000.

Uses the system Microsoft Edge through Playwright (no browser download): python scripts/gallery.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "gallery"
SHOTS = [("01-hero", None), ("02-the-pitch", "#pitch"), ("03-one-pitch-is-not-enough", "#single"),
         ("04-the-pattern", "#pattern"), ("05-all-of-mlb", "#league"), ("06-try-it", "#tryit"),
         ("07-where-it-stops", "#stops"), ("08-method", "#method")]

OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1500, "height": 1000})
    pg.goto((ROOT / "docs" / "index.html").as_uri(), wait_until="networkidle")
    pg.wait_for_timeout(2500)
    for name, sel in SHOTS:
        if sel:
            pg.eval_on_selector(sel, "e => window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 20)")
            pg.wait_for_timeout(3000)
        if sel == "#tryit":                       # show a real result, not an empty panel
            pg.locator("#tryit").get_by_text("Emmanuel Clase", exact=True).first.click()
            pg.wait_for_timeout(3000)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        print(name)
    b.close()
