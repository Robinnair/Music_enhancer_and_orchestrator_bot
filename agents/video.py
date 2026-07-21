import numpy as np
import librosa
import json
import re
import subprocess
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.gridspec import GridSpec


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "untitled"


STEM_COLORS = {
    "vocals":  {"line": "#FF6B9D", "fill": "#FF6B9D", "label": "VOCALS"},
    "drums":   {"line": "#FFD93D", "fill": "#FFD93D", "label": "DRUMS"},
    "bass":    {"line": "#6BCB77", "fill": "#6BCB77", "label": "BASS"},
    "other":   {"line": "#4D96FF", "fill": "#4D96FF", "label": "MELODY"},
}

DEFAULT_COLOR = {"line": "#00FF88", "fill": "#00FF88", "label": "AUDIO"}


def load_stems(song_name: str, project_root: Path, target_sr: int = 22050) -> dict:
    htdemucs = project_root / "outputs" / "htdemucs_ft" / song_name
    stems = {}

    NOISE_FLOOR = 0.01

    for stem_name, color in STEM_COLORS.items():
        for ext in ["wav", "mp3"]:
            matches = list(htdemucs.glob(f"*{stem_name}*.{ext}"))
            if matches:
                try:
                    y, sr = librosa.load(str(matches[0]), sr=target_sr, mono=True)
                    # True max, not a percentile. A percentile (e.g. 95th)
                    # guarantees that ~5% of samples exceed the scale and get
                    # hard-clipped to the axis edge -- that's exactly what
                    # was flattening the tops of dense stems like melody.
                    # Using the true max means chunk/scale is mathematically
                    # never > 1, so peaks keep their natural rounded shape
                    # and nothing is ever clipped. Stems that are
                    # effectively silent (e.g. no vocals in an instrumental)
                    # keep scale=1 so they stay flat instead of being
                    # amplified into fake-looking noise.
                    peak = float(np.max(np.abs(y))) if len(y) else 0.0
                    scale = peak if peak > NOISE_FLOOR else 1.0
                    stems[stem_name] = {"audio": y, "color": color, "scale": scale}
                    print(f"Loaded stem: {stem_name} (display scale={scale:.4f})")
                    break
                except Exception as e:
                    print(f"Could not load {stem_name}: {e}")

    return stems


def _display_wave(chunk: np.ndarray, scale: float, height: float = 0.85) -> np.ndarray:
    """Normalize a chunk to its track's own dynamic range and hard-clip to
    +/-1 so peaks can never exceed the subplot's axis limits -- that overflow
    was what caused the waveform to visually flatten/clip at the top and
    bottom edges. Unlike the earlier version, this does NOT apply a
    compression curve, so loud passages still look as full/tall as they used
    to -- only the normalization (to stop silent stems getting amplified,
    and loud stems from exceeding the axis) is kept."""
    norm = np.clip(chunk / scale, -1.0, 1.0)
    return norm * height


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
    y_full, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=y_full, sr=sr)

    stems = load_stems(song_name, project_root, sr)
    has_stems = len(stems) > 0
    print(f"Stems loaded: {len(stems)}")

    title = lyrics.get("title", song_name)
    artist = lyrics.get("artist", "")

    # Only use timed lyrics that were actually generated for THIS song.
    # The shared outputs/timed_lyrics.json is stale leftover from whatever
    # song last went through the aligner -- falling back to it would show
    # another song's captions (or stems, in the analogous htdemucs case).
    per_song_timed = project_root / "outputs" / f"timed_lyrics_{_slug(song_name)}.json"
    timed_lines = []
    if per_song_timed.exists():
        with open(per_song_timed, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            timed_lines = [(t["start"], t["text"]) for t in raw] if raw else []
        elif isinstance(raw, dict):
            lines = raw.get("lines", [])
            timed_lines = [(t["start"], t["text"]) for t in lines] if lines else []

    fps = 24
    total_frames = int(duration * fps)
    window_samples = int(0.4 * sr)

    print(f"Rendering {total_frames} frames...")

    fig = plt.figure(figsize=(9, 16), facecolor="#0A0A0A")

    if has_stems:
        gs = GridSpec(
            6, 1,
            figure=fig,
            top=0.92,
            bottom=0.08,
            hspace=0.15,
            height_ratios=[0.8, 1, 1, 1, 1, 0.6]
        )
        ax_title = fig.add_subplot(gs[0])
        ax_stems = [fig.add_subplot(gs[i+1]) for i in range(4)]
        ax_lyrics = fig.add_subplot(gs[5])
    else:
        gs = GridSpec(3, 1, figure=fig, top=0.92, bottom=0.08, hspace=0.2,
                      height_ratios=[0.5, 2, 0.8])
        ax_title = fig.add_subplot(gs[0])
        ax_stems = [fig.add_subplot(gs[1])]
        ax_lyrics = fig.add_subplot(gs[2])

    stem_list = list(stems.items()) if has_stems else []

    # Fallback (no-stems) scale, computed once so it stays consistent
    # across the whole video instead of jumping per frame. True max (not a
    # percentile) so nothing ever gets hard-clipped -- see load_stems.
    fallback_peak = float(np.max(np.abs(y_full))) if len(y_full) else 0.0
    fallback_scale = fallback_peak if fallback_peak > 0.01 else 1.0

    for frame_idx in range(total_frames):
        current_time = frame_idx / fps
        start_s = max(0, int(current_time * sr) - window_samples // 2)
        end_s = min(len(y_full), start_s + window_samples)

        ax_title.clear()
        ax_title.set_facecolor("#0A0A0A")
        ax_title.axis("off")
        ax_lyrics.clear()
        ax_lyrics.set_facecolor("#0A0A0A")
        ax_lyrics.axis("off")
        for ax in ax_stems:
            ax.clear()
            ax.set_facecolor("#0A0A0A")
            ax.axis("off")

        # ── TITLE ────────────────────────────────────────────────
        ax_title.text(0.5, 0.75, title,
                      color="white", fontsize=24, fontweight="bold",
                      ha="center", va="center",
                      fontfamily="monospace",
                      transform=ax_title.transAxes)
        if artist and artist != "Unknown":
            ax_title.text(0.5, 0.25, artist,
                          color="#888888", fontsize=14,
                          ha="center", va="center",
                          fontfamily="monospace",
                          transform=ax_title.transAxes)

        ax_title.axhline(y=0.0, xmin=0.1, xmax=0.9,
                         color="#222222", linewidth=0.8)

        # ── STEM WAVEFORMS ───────────────────────────────────────
        if has_stems:
            for i, (stem_name, stem_data) in enumerate(stem_list):
                ax = ax_stems[i]
                color = stem_data["color"]
                stem_audio = stem_data["audio"]
                scale = stem_data.get("scale", 1.0)
                label = color["label"]

                start_s2 = max(0, int(current_time * sr) - window_samples // 2)
                end_s2 = min(len(stem_audio), start_s2 + window_samples)
                chunk = stem_audio[start_s2:end_s2]

                if len(chunk) > 0:
                    x = np.linspace(0, 1, len(chunk))
                    line_color = color["line"]
                    fill_color = color["fill"]
                    display = _display_wave(chunk, scale)

                    ax.plot(x, display,
                            color=line_color, linewidth=0.9, alpha=1.0)
                    ax.plot(x, -display,
                            color=line_color, linewidth=0.5, alpha=0.4)
                    ax.fill_between(x, display, -display,
                                    color=fill_color, alpha=0.06)
                    ax.plot(x, display,
                            color=line_color, linewidth=5, alpha=0.04)

                ax.set_xlim(0, 1)
                ax.set_ylim(-1, 1)
                ax.set_facecolor("#0A0A0A")
                ax.axis("off")

                ax.text(-0.02, 0.5, label,
                        color=color["line"],
                        fontsize=7,
                        fontweight="bold",
                        ha="right", va="center",
                        fontfamily="monospace",
                        transform=ax.transAxes,
                        alpha=0.8)

                if i < len(stem_list) - 1:
                    ax.axhline(y=-0.95, xmin=0, xmax=1,
                               color="#1A1A1A", linewidth=0.5)

        else:
            ax = ax_stems[0]
            chunk = y_full[start_s:end_s]
            if len(chunk) > 0:
                x = np.linspace(0, 1, len(chunk))
                display = _display_wave(chunk, fallback_scale)
                ax.plot(x, display, color="#00FF88", linewidth=1.0)
                ax.plot(x, -display, color="#00CC66", linewidth=0.5, alpha=0.4)
                ax.fill_between(x, display, -display,
                                color="#00FF88", alpha=0.06)
            ax.set_xlim(0, 1)
            ax.set_ylim(-1, 1)
            ax.axis("off")

        # ── LYRICS ───────────────────────────────────────────────
        ax_lyrics.set_xlim(0, 1)
        ax_lyrics.set_ylim(0, 1)

        if timed_lines:
            prev_line = ""
            current_line = ""
            next_line = ""

            for i, (t, line) in enumerate(timed_lines):
                if t <= current_time:
                    prev_line = current_line
                    current_line = line
                    next_line = timed_lines[i+1][1] if i+1 < len(timed_lines) else ""

            if prev_line:
                ax_lyrics.text(0.5, 0.82, prev_line,
                               color="#333333", fontsize=12,
                               ha="center", va="center",
                               fontfamily="monospace",
                               style="italic",
                               transform=ax_lyrics.transAxes)
            if current_line:
                ax_lyrics.text(0.5, 0.55, current_line,
                               color="white", fontsize=17,
                               fontweight="bold",
                               ha="center", va="center",
                               fontfamily="monospace",
                               transform=ax_lyrics.transAxes)
            if next_line:
                ax_lyrics.text(0.5, 0.28, next_line,
                               color="#333333", fontsize=12,
                               ha="center", va="center",
                               fontfamily="monospace",
                               transform=ax_lyrics.transAxes)

        # ── PROGRESS BAR ─────────────────────────────────────────
        progress = current_time / duration if duration > 0 else 0

        ax_lyrics.add_patch(Rectangle(
            (0.05, 0.05), 0.90, 0.08,
            color="#1A1A1A",
            transform=ax_lyrics.transAxes,
            zorder=3,
            clip_on=False
        ))

        if progress > 0:
            ax_lyrics.add_patch(Rectangle(
                (0.05, 0.05), 0.90 * progress, 0.08,
                color="#FF6B9D" if has_stems else "#00FF88",
                transform=ax_lyrics.transAxes,
                zorder=4,
                clip_on=False
            ))

        mins = int(current_time // 60)
        secs = int(current_time % 60)
        total_mins = int(duration // 60)
        total_secs = int(duration % 60)
        ax_lyrics.text(0.95, 0.02,
                       f"{mins:02d}:{secs:02d} / {total_mins:02d}:{total_secs:02d}",
                       color="#444444", fontsize=8,
                       ha="right", va="bottom",
                       fontfamily="monospace",
                       transform=ax_lyrics.transAxes)

        plt.savefig(
            str(frames_dir / f"frame_{frame_idx:06d}.png"),
            dpi=100,
            facecolor="#0A0A0A",
            edgecolor="none"
        )

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
    song_name = sys.argv[2]

    # Prefer the per-song lyrics file matching this song_name over the
    # shared outputs/lyrics.json, which may be stale from whatever song
    # was processed last (e.g. if fetch_lyrics found no match for an
    # instrumental track and this file never got refreshed for THIS song).
    per_song_path = project_root / "outputs" / f"lyrics_{_slug(song_name)}.json"
    legacy_path = project_root / "outputs" / "lyrics.json"

    if per_song_path.exists():
        lyrics_path = per_song_path
    else:
        lyrics_path = legacy_path
        print(f"Warning: no per-song lyrics file for '{song_name}' — "
              f"falling back to {legacy_path}, which may belong to a "
              f"different song. Run agents/lyrics.py \"{song_name}\" "
              f"\"<artist>\" first if you want correct title/artist here.")

    with open(lyrics_path, encoding="utf-8") as f:
        lyrics = json.load(f)

    print(f"Using lyrics file: {lyrics_path}")
    print(f"Loaded lyrics for: {lyrics.get('title')} by {lyrics.get('artist')}")
    generate_video(sys.argv[1], lyrics, song_name)