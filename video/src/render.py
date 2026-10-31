"""Render scenes to video segments (or single preview stills).

usage:  python render.py still s2 5.0 [out.png]
        python render.py seg s2 [s3 ...]
        python render.py all            # every segment, in parallel
"""
import subprocess
import sys
from multiprocessing import Pool

import imageio_ffmpeg
from PIL import ImageDraw

from common import *  # noqa: F401,F403
from script import SCENES as NARRATION
from timeline import build, words, LEAD

FADE = 0.3


def caption_chunks(key):
    """Split narration into caption lines aligned to word timings (keeps the script's punctuation)."""
    txt = dict(NARRATION).get(key)
    if not txt:
        return []
    ws = words(key)
    low, cur, spans = txt.lower(), 0, []
    for w in ws:
        p = low.find(w["w"].lower(), cur)
        spans.append(p if p >= 0 else None)
        if p >= 0:
            cur = p + len(w["w"])
    toks = []
    for i, w in enumerate(ws):
        a = spans[i]
        nxt = next((s for s in spans[i + 1:] if s is not None), len(txt))
        toks.append({"s": txt[a:nxt].strip() if a is not None else w["w"], "t": w["t"], "e": w["t"] + w["d"]})
    chunks, cur = [], []
    for tk in toks:
        cur.append(tk)
        line_ = " ".join(x["s"] for x in cur)
        if len(line_) > 38 or tk["s"][-1:] in ".?:!" or (tk["s"][-1:] == "," and len(line_) > 22):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        end = chunks[i + 1][0]["t"] if i + 1 < len(chunks) else c[-1]["e"] + 0.4
        out.append({"t0": LEAD + c[0]["t"], "t1": LEAD + min(end, c[-1]["e"] + 0.6), "toks": c})
    return out


def draw_caption(im, chunks, t, dark):
    for c in chunks:
        if c["t0"] - 0.05 <= t <= c["t1"]:
            d = ImageDraw.Draw(im, "RGBA")
            f = font("sans", 36, 600)
            parts = [tk["s"] for tk in c["toks"]]
            s = " ".join(parts)
            wpx = text_w(s, f)
            x0, y = (W - wpx) / 2, 990
            rect(d, (x0 - 26, y - 34, x0 + wpx + 26, y + 30), fill=(22, 24, 28, 200), radius=14)
            x = x0
            for tk in c["toks"]:
                col = (255, 214, 140) if tk["t"] + LEAD <= t < tk["e"] + LEAD + 0.08 else (248, 246, 240)
                d.text((x * S, y * S), tk["s"], font=f, fill=col, anchor="lm")
                x += text_w(tk["s"] + " ", f)
            return


def draw_tag(im, dark):
    d = ImageDraw.Draw(im, "RGBA")
    f = font("mono", 17, 600)
    s = "ALLEGATIONS, NOT FINDINGS"
    w = text_w(s, f)
    fill = (255, 255, 255, 34) if dark else (22, 24, 28, 14)
    rect(d, (36, 30, 36 + w + 56, 70), fill=fill, radius=20)
    circle(d, (58, 50), 6, fill=AMBER)
    d.text((76 * S, 50 * S), s, font=f, fill=(236, 230, 218) if dark else INK2, anchor="lm")


def frame(key, t, dur):
    from scenes import SCENES, DARK
    im = SCENES[key](t, dur)
    dark = key in DARK
    draw_caption(im, CAPS.get(key) or [], t, dark)
    if key != "end":
        draw_tag(im, dark)
    im = finish(im)
    # dip to/from cream (or ink for the very first/last frames)
    a = min(clamp(t / FADE), clamp((dur - t) / FADE))
    if key == "s1":
        a = min(clamp(t / 0.8), clamp((dur - t) / FADE))
    if a < 1:
        from PIL import Image
        base = Image.new("RGB", im.size, INK if key in ("s1",) and t < 1 else CREAM)
        im = Image.blend(base, im, ease(a))
    return im


CAPS = {}


def render_seg(key):
    tl, _ = build()
    dur = tl[key]["dur"]
    CAPS[key] = caption_chunks(key)
    n = int(round(dur * FPS))
    out = BUILD / f"seg_{key}.mp4"
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
           "-pix_fmt", "yuv420p", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(key, i / FPS, dur).tobytes())
    p.stdin.close()
    p.wait()
    return f"{key}: {n} frames, {dur:.2f}s"


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "still":
        key, t = sys.argv[2], float(sys.argv[3])
        tl, _ = build()
        CAPS[key] = caption_chunks(key)
        dest = sys.argv[4] if len(sys.argv) > 4 else str(BUILD / f"still_{key}_{t:.1f}.png")
        frame(key, t, tl[key]["dur"]).save(dest)
        print(dest)
    else:
        keys = sys.argv[2:] if mode == "seg" else ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "end"]
        with Pool(min(6, len(keys))) as pool:
            for msg in pool.imap_unordered(render_seg, keys):
                print(msg, flush=True)
