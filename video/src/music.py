"""Original soundtrack, synthesized from scratch (no samples): A-minor pad, bass, plucked arpeggio, soft drums.

Sections follow the scene timeline so the music builds under the story and resolves at the end.
"""
import numpy as np
import wave
from common import BUILD
from timeline import build

SR = 48000
BPM = 84
BEAT = 60 / BPM
BAR = 4 * BEAT
NOTES = {"A": 57, "B": 59, "C": 60, "D": 62, "E": 64, "F": 65, "G": 67}
PROG = [("A", [0, 3, 7, 10]), ("F", [0, 4, 7, 11]), ("C", [0, 4, 7, 14]), ("G", [0, 4, 7, 9])]


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def pad_note(f, dur, rng):
    t = np.arange(int(dur * SR)) / SR
    L = np.zeros_like(t)
    R = np.zeros_like(t)
    for det, side in ((-0.09, 0), (0.0, 0.5), (0.11, 1)):
        ff = f * 2 ** (det / 12)
        ph = rng.random() * 6.28
        s = sum(np.sin(2 * np.pi * ff * h * t + ph * h) / h ** 1.4 for h in range(1, 7))
        L += s * (1 - side)
        R += s * side
    e = env_adsr(len(t), 1.2, 1.4)
    return L * e, R * e


def pluck(f, dur=0.9):
    t = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t))
    return s * np.exp(-t * 5.5) * np.minimum(1, t * 400)


def kick():
    t = np.arange(int(0.35 * SR)) / SR
    f = 46 + 80 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hat(rng):
    n = int(0.05 * SR)
    x = rng.standard_normal(n)
    x = np.diff(x, prepend=0)
    return x * np.exp(-np.arange(n) / SR * 90) * 0.25


def add(buf, x, t0, gain=1.0, pan=0.5):
    i = int(t0 * SR)
    if i >= buf.shape[1]:
        return
    x = x[: buf.shape[1] - i]
    buf[0, i:i + len(x)] += x * gain * (1 - pan) * 2 ** 0.5
    buf[1, i:i + len(x)] += x * gain * pan * 2 ** 0.5


def main():
    tl, T = build()
    rng = np.random.default_rng(5)
    buf = np.zeros((2, int((T + 1) * SR)))
    sec = {k: v["start"] for k, v in tl.items()}
    nbars = int(T / BAR) + 1
    for b in range(nbars):
        t0 = b * BAR
        root, ivs = PROG[b % 4]
        base = NOTES[root] - 12
        # pad throughout
        for iv in ivs:
            l, r = pad_note(hz(base + iv), BAR + 1.2, rng)
            buf[0, int(t0 * SR):int(t0 * SR) + len(l)] += l[: max(0, buf.shape[1] - int(t0 * SR))] * 0.05
            buf[1, int(t0 * SR):int(t0 * SR) + len(r)] += r[: max(0, buf.shape[1] - int(t0 * SR))] * 0.05
        # bass from the problem statement on
        if t0 >= sec["s3"] - 0.1 and t0 < sec["end"] + 1:
            for q in range(4):
                add(buf, pluck(hz(base - 12), 0.6) * (1.0 if q == 0 else 0.6), t0 + q * BEAT, 0.20)
        # arpeggio from the data scene on, thinning out for the limits scene
        if sec["s4"] - 0.1 <= t0 < sec["s9"] + 2:
            dens = 0.5 if sec["s8"] <= t0 < sec["s9"] else 1.0
            for e8 in range(8):
                if rng.random() > dens:
                    continue
                m = base + 24 + ivs[(e8 * 3 + b) % 4] + (12 if e8 in (3, 6) else 0)
                p = pluck(hz(m), 1.0)
                tt = t0 + e8 * BEAT / 2
                pan = 0.3 + 0.4 * ((e8 % 2))
                add(buf, p, tt, 0.06, pan)
                add(buf, p, tt + BEAT * 0.75, 0.025, 1 - pan)     # echo
        # soft drums under the results
        if sec["s6"] - 0.1 <= t0 < sec["s8"]:
            add(buf, kick(), t0, 0.32)
            add(buf, kick(), t0 + 2 * BEAT, 0.24)
            for q in range(4):
                add(buf, hat(rng), t0 + q * BEAT + BEAT / 2, 0.5, 0.65)
    # final A minor (add9) swell over the outro + credits
    for m in (45, 57, 60, 64, 71):
        l, r = pad_note(hz(m), sec["end"] + 3.4 - sec["s9"] + 1.0, rng)
        i = int((sec["s9"] + 0.5) * SR)
        n = min(len(l), buf.shape[1] - i)
        buf[0, i:i + n] += l[:n] * 0.045
        buf[1, i:i + n] += r[:n] * 0.045
    # fade in / out
    n = buf.shape[1]
    fade = np.ones(n)
    fade[: int(1.5 * SR)] = np.linspace(0, 1, int(1.5 * SR))
    end = int(T * SR)
    fl = int(2.5 * SR)
    fade[end - fl:end] *= np.linspace(1, 0, fl)
    fade[end:] = 0
    buf *= fade
    buf /= np.abs(buf).max() + 1e-9
    np.save(BUILD / "music.npy", buf.astype(np.float32))
    print("music", buf.shape[1] / SR, "s")


if __name__ == "__main__":
    main()
