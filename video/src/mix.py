"""Mix narration, ducked music and a few synthesized SFX into build/mix.wav."""
import wave
import numpy as np
from common import BUILD
from timeline import build, words, LEAD

SR = 48000


def read_wav(p):
    with wave.open(str(p)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return x


def db(x):
    return 10 ** (x / 20)


def main():
    tl, T = build()
    n = int((T + 0.5) * SR)
    voice = np.zeros(n)
    active = np.zeros(n)
    for k in [k for k in tl if k != "end"]:
        x = read_wav(BUILD / "voice" / f"{k}.wav")
        x = x / (np.sqrt(np.mean(x[np.abs(x) > 0.01] ** 2)) + 1e-9) * db(-17)     # speech RMS -> -17 dBFS
        i = int((tl[k]["start"] + LEAD) * SR)
        m = min(len(x), n - i)
        voice[i:i + m] += x[:m]
        for w in words(k):
            a = int((tl[k]["start"] + LEAD + w["t"]) * SR)
            b = int((tl[k]["start"] + LEAD + w["t"] + w["d"] + 0.25) * SR)
            active[a:b] = 1
    # smooth the duck envelope (attack/release ~250 ms)
    k = int(0.25 * SR)
    kern = np.hanning(2 * k)
    kern /= kern.sum()
    from scipy.signal import fftconvolve
    duck = np.clip(fftconvolve(active, kern, "same"), 0, 1)

    music = np.load(BUILD / "music.npy")[:, :n]
    if music.shape[1] < n:
        music = np.pad(music, ((0, 0), (0, n - music.shape[1])))
    mrms = np.sqrt(np.mean(music[:, : int(T * SR)] ** 2))
    music = music / mrms * db(-29)                      # music bed alone ~ -29 dBFS RMS
    gain = 1 - (1 - db(-8)) * duck                      # ducked a further 8 dB under speech -> ~20 dB below voice
    music *= gain

    sfx = np.zeros(n)
    rng = np.random.default_rng(2)
    # crowd murmur under the opener
    s1 = tl["s1"]
    a, b = int(s1["start"] * SR), int((s1["start"] + s1["dur"] + 0.4) * SR)
    noise = rng.standard_normal(b - a)
    for _ in range(3):                                   # cheap low-pass (brown-ish)
        noise = np.convolve(noise, np.ones(40) / 40, "same")
    env = np.ones(b - a)
    env[: SR] = np.linspace(0, 1, SR)
    env[-SR:] = np.linspace(1, 0, SR)
    sfx[a:b] += noise / (np.abs(noise).max() + 1e-9) * db(-30) * env
    # the pitch in scene 2: whoosh during the flight, thud at the bounce
    from scenes import TRAJ
    ts, pts, hit = TRAJ
    s2 = tl["s2"]["start"]
    t0, fl = 3.0, 2.8
    a, b = int((s2 + t0) * SR), int((s2 + t0 + fl) * SR)
    wn = rng.standard_normal(b - a)
    wn = np.diff(wn, prepend=0)
    wenv = np.sin(np.linspace(0, np.pi, b - a)) ** 2
    sfx[a:b] += wn * wenv * db(-34)
    if hit is not None:
        th = s2 + t0 + fl * hit / (len(pts) - 1)
        tt = np.arange(int(0.4 * SR)) / SR
        thud = np.sin(2 * np.pi * (70 + 60 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14)
        dust = rng.standard_normal(len(tt)) * np.exp(-tt * 25) * 0.3
        i = int(th * SR)
        sfx[i:i + len(tt)] += (thud + dust) * db(-14)

    mix = music + (voice + sfx)[None, :]
    peak = np.abs(mix).max()
    if peak > db(-1):
        mix *= db(-1) / peak
    out = (np.clip(mix, -1, 1) * 32767).astype(np.int16).T.copy()
    with wave.open(str(BUILD / "mix.wav"), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())
    print("mix", n / SR, "s, peak", round(20 * np.log10(peak + 1e-9), 1), "dBFS")


if __name__ == "__main__":
    main()
