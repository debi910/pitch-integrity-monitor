"""Concatenate rendered segments, mux the mix, write video/out/pitch-integrity-monitor.mp4 (+ <=95 MB copy if needed)."""
import subprocess
import imageio_ffmpeg
from common import BUILD, VID
from timeline import build

FF = imageio_ffmpeg.get_ffmpeg_exe()
tl, T = build()
keys = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "end"]
lst = BUILD / "concat.txt"
lst.write_text("".join(f"file '{(BUILD / f'seg_{k}.mp4').as_posix()}'\n" for k in keys))
out = VID / "out"
out.mkdir(exist_ok=True)
final = out / "pitch-integrity-monitor.mp4"
intro = tl["s1"]["start"]
# INTRO seconds of music-only: hold the first frame (black fade-in start) via tpad
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(BUILD / "mix.wav"),
                "-filter_complex", f"[0:v]tpad=start_duration={intro}:start_mode=add:color=0x16181C[v]",
                "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-profile:v", "high", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                "-movflags", "+faststart", str(final)], check=True)
size = final.stat().st_size / 1e6
print(final, f"{size:.1f} MB")
if size > 95:
    small = out / "pitch-integrity-monitor-95mb.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(final), "-c:v", "libx264", "-preset", "slow",
                    "-b:v", "5M", "-maxrate", "6M", "-bufsize", "12M", "-c:a", "copy", "-movflags", "+faststart",
                    str(small)], check=True)
    print(small, f"{small.stat().st_size / 1e6:.1f} MB")
