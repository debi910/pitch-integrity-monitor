"""Synthesize narration per scene with edge-tts; keep word timings for captions."""
import asyncio, json, subprocess, sys
from pathlib import Path
import edge_tts, imageio_ffmpeg
from script import SCENES

OUT = Path(__file__).resolve().parents[1] / "build" / "voice"
OUT.mkdir(parents=True, exist_ok=True)
VOICE, RATE = "en-US-AndrewNeural", "+0%"


async def one(key, text):
    words, audio = [], bytearray()
    async for c in edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary").stream():
        if c["type"] == "audio":
            audio += c["data"]
        elif c["type"] == "WordBoundary":
            words.append({"t": c["offset"] / 1e7, "d": c["duration"] / 1e7, "w": c["text"]})
    (OUT / f"{key}.mp3").write_bytes(audio)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(OUT / f"{key}.mp3"),
                    "-ar", "48000", "-ac", "1", str(OUT / f"{key}.wav")], check=True)
    (OUT / f"{key}.json").write_text(json.dumps(words))
    print(key, f"{words[-1]['t'] + words[-1]['d']:.2f}s", len(words), "words")


async def main():
    for k, t in SCENES:
        if (OUT / f"{k}.json").exists() and "--force" not in sys.argv:
            continue
        for attempt in range(5):
            try:
                await one(k, t); break
            except edge_tts.exceptions.NoAudioReceived as e:
                print(k, "retry", attempt + 1, e); await asyncio.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f"TTS failed for {k}")

asyncio.run(main())
