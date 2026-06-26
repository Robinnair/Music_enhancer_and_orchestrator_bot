import numpy as np
import librosa
import json
import subprocess
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def generate_video(audio_path: str, lyrics: dict, song_name: str) -> str:
    print("=" * 50)
    print("VIDEO AGENT")
    print("=" * 50)

    project_root = Path(__file__).parent.parent
    output_path = str(project_root / "outputs" / "final" / f"{song_name}_video.mp4")
    frames_dir = project_root / "outputs" / "frames"
    frames_dir.mkdir(exist_ok=True)

    for f in frames_dir.glob("*.png"):
        f.unlink()

    print("Loading audio...")
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    title = lyrics.get("title", song_name)
    artist = lyrics.get("artist", "")

    timed_path = project_root / "outputs" / "timed_lyrics.json"
    if timed_path.exists():
        with open(timed_path, encoding="utf-8") as f:
            raw = json.load(f)
        timed_lines = [(t["start"], t["text"]) for t in raw] if raw else []
        if timed_lines:
            print(f"Using {len(timed_lines)} aligned lyric lines.")
        else:
            print("Instrumental track — rendering waveform only.")
    else:
        print("No alignment found. Using even spacing.")
        lines = lyrics.get("lines", [])
        time_per_line = duration / len(lines) if lines else 1
        timed_lines = [(i * time_per_line, line) for i, line in enumerate(lines)]

    fps = 24
    total_frames = int(duration * fps)

    # Canvas is 1080x1920 (9:16 vertical)
    # We work in figure inches — 9x16 at 120dpi = 1080x1920
    fig = plt.figure(figsize=(9, 16), facecolor="black")

    # Manual axes placement — gives full control over layout
    # [left, bottom, width, height] in figure fraction
    ax_wave = fig.add_axes([0.05, 0.35, 0.90, 0.28])   # waveform — tall and centered
    ax_info = fig.add_axes([0.0,  0.0,  1.0,  1.0])    # overlay for text
    ax_info.set_xlim(0, 1)
    ax_info.set_ylim(0, 1)
    ax_info.axis("off")
    ax_info.set_facecolor("none")

    print(f"Rendering {total_frames} frames...")

    for frame_idx in range(total_frames):
        # Clear both axes
        ax_wave.clear()
        ax_wave.set_facecolor("black")
        ax_wave.set_xlim(0, 1)
        ax_wave.set_ylim(-1, 1)
        ax_wave.axis("off")

        ax_info.clear()
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)
        ax_info.axis("off")
        ax_info.set_facecolor("none")

        current_time = frame_idx / fps

        # ── WAVEFORM ─────────────────────────────────────────────
        window_samples = int(0.6 * sr)
        start_sample = max(0, int(current_time * sr) - window_samples // 2)
        end_sample = min(len(y), start_sample + window_samples)
        wave_chunk = y[start_sample:end_sample]

        if len(wave_chunk) > 0:
            x_wave = np.linspace(0, 1, len(wave_chunk))

            # Mirror waveform for a more visual look
            ax_wave.plot(x_wave, wave_chunk * 0.85,
                         color="#00FF88", linewidth=1.2, alpha=1.0)
            ax_wave.plot(x_wave, -wave_chunk * 0.85,
                         color="#00CC66", linewidth=0.8, alpha=0.5)

            # Fill between top and bottom for body
            ax_wave.fill_between(x_wave,
                                  wave_chunk * 0.85,
                                  -wave_chunk * 0.85,
                                  color="#00FF88", alpha=0.08)

            # Glow effect — wider softer line behind
            ax_wave.plot(x_wave, wave_chunk * 0.85,
                         color="#00FF88", linewidth=6, alpha=0.05)

        # ── TITLE ────────────────────────────────────────────────
        ax_info.text(0.5, 0.88, title,
                     color="white", fontsize=26, fontweight="bold",
                     ha="center", va="center",
                     fontfamily="monospace")

        # ── ARTIST ───────────────────────────────────────────────
        if artist and artist != "Unknown":
            ax_info.text(0.5, 0.82, artist,
                         color="#888888", fontsize=16,
                         ha="center", va="center",
                         fontfamily="monospace")

        # Thin separator line under title
        ax_info.axhline(y=0.79, xmin=0.2, xmax=0.8,
                        color="#333333", linewidth=0.8)

        # ── LYRICS ───────────────────────────────────────────────
        if timed_lines:
            prev_line = ""
            current_line = ""
            next_line = ""

            for i, (t, line) in enumerate(timed_lines):
                if t <= current_time:
                    prev_line = current_line
                    current_line = line
                    next_line = timed_lines[i + 1][1] if i + 1 < len(timed_lines) else ""

            if prev_line:
                ax_info.text(0.5, 0.24, prev_line,
                             color="#444444", fontsize=14,
                             ha="center", va="center",
                             fontfamily="monospace",
                             style="italic")

            if current_line:
                ax_info.text(0.5, 0.18, current_line,
                             color="white", fontsize=19,
                             fontweight="bold",
                             ha="center", va="center",
                             fontfamily="monospace")

            if next_line:
                ax_info.text(0.5, 0.12, next_line,
                             color="#444444", fontsize=14,
                             ha="center", va="center",
                             fontfamily="monospace")

        # ── PROGRESS BAR ─────────────────────────────────────────
        progress = current_time / duration if duration > 0 else 0
        ax_info.add_patch(Rectangle(
            (0.05, 0.055), 0.90, 0.012,
            color="#222222", transform=ax_info.transAxes, zorder=3
        ))
        ax_info.add_patch(Rectangle(
            (0.05, 0.055), 0.90 * progress, 0.012,
            color="#00FF88", transform=ax_info.transAxes, zorder=4
        ))

        # ── TIMESTAMP ────────────────────────────────────────────
        mins = int(current_time // 60)
        secs = int(current_time % 60)
        total_mins = int(duration // 60)
        total_secs = int(duration % 60)
        ax_info.text(0.95, 0.04,
                     f"{mins:02d}:{secs:02d} / {total_mins:02d}:{total_secs:02d}",
                     color="#555555", fontsize=9,
                     ha="right", va="center",
                     fontfamily="monospace")

        plt.savefig(str(frames_dir / f"frame_{frame_idx:06d}.png"),
                    dpi=120, bbox_inches="tight",
                    facecolor="black", edgecolor="none")

        if frame_idx % 200 == 0:
            print(f"  Frame {frame_idx}/{total_frames}")

    plt.close(fig)
    print("Encoding video with FFmpeg...")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%06d.png"),
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise RuntimeError("Video encoding failed")

    import time
    time.sleep(2)

    for f in frames_dir.glob("*.png"):
        try:
            f.unlink()
        except PermissionError:
            pass

    try:
        frames_dir.rmdir()
    except Exception:
        pass

    print(f"Video saved: {output_path}")
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python video.py <audio_path> <song_name>")
        exit()

    project_root = Path(__file__).parent.parent
    lyrics_path = project_root / "outputs" / "lyrics.json"

    with open(lyrics_path, encoding="utf-8") as f:
        lyrics = json.load(f)

    generate_video(sys.argv[1], lyrics, sys.argv[2])