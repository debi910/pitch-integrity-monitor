# Demo video

`video/out/pitch-integrity-monitor.mp4` (not in git): 2:00, 1920x1080, 30 fps, H.264 + AAC, burned-in captions.

Everything is generated from code and the repo's own data:

| Step | Script | Output |
|---|---|---|
| Narration (Microsoft neural TTS via edge-tts, en-US-AndrewNeural) + word timings | `src/voice.py` (text in `src/script.py`) | `build/voice/` |
| Real numbers for the scenes (Statcast trajectories, labels, results/*.json) | `src/prep.py` | `build/data.json` |
| Original soundtrack, synthesized from sine partials (no samples) | `src/music.py` | `build/music.npy` |
| Mix: voice at -17 dBFS RMS, music ducked ~20 dB under speech, crowd/whoosh/thud SFX | `src/mix.py` | `build/mix.wav` |
| Frames (Pillow, 2x supersampled), captions, corner tag | `src/render.py all` (scenes in `src/scenes.py`, 3D in `src/field3d.py`) | `build/seg_*.mp4` |
| Concatenate + mux | `src/assemble.py` | `out/pitch-integrity-monitor.mp4` |

The scene 2 pitch is drawn from its actual Statcast 9-parameter fit (release point, velocity, acceleration);
the green paths are 40 of Clase's real first-pitch sliders. Photos are CC-licensed (`web/img/CREDITS.md`),
and the stadium photo is blurred outside the diamond so no team logos are legible. Fonts are OFL (`fonts/OFL.txt`).

Rebuild: `cd video/src && python voice.py && python prep.py && python music.py && python mix.py && python render.py all && python assemble.py`
(needs `pip install edge-tts imageio-ffmpeg` on top of `requirements-pipeline.txt`).
