"""Scene timing from the narration: each scene = LEAD + voice + TAIL. Word cues for syncing visuals."""
import json
import wave
from common import BUILD

LEAD, TAIL = 0.35, 0.45
INTRO = 0.4           # music-only before scene 1
END = 3.4             # credits card
KEYS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9"]
EXTRA = {"s2": 0.5, "s7": 0.2, "s9": 0.8}    # extra hold where the picture needs it


def voice_len(k):
    """Spoken length: last word end (the TTS file carries trailing silence)."""
    w = words(k)[-1]
    return w["t"] + w["d"] + 0.15


def words(k):
    return json.loads((BUILD / "voice" / f"{k}.json").read_text())


def build():
    tl, t = {}, INTRO
    for k in KEYS:
        d = LEAD + voice_len(k) + TAIL + EXTRA.get(k, 0)
        tl[k] = {"start": t, "dur": d}
        t += d
    tl["end"] = {"start": t, "dur": END}
    return tl, t + END


def cue(k, word, nth=0, default=0.0):
    """Scene-local time (s) at which `word` is spoken (nth occurrence)."""
    hits = [w["t"] for w in words(k) if w["w"].lower().strip(".,:?") == word.lower()]
    return LEAD + hits[nth] if len(hits) > nth else default
