import yt_dlp
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path


def download_and_convert(song_name: str, artist_name: str) -> str:
    print("=" * 50)
    print("DOWNLOADER AGENT")
    print("=" * 50)

    project_root = Path(__file__).parent.parent
    input_folder = project_root / "input"
    input_folder.mkdir(exist_ok=True)

    safe_name = f"{song_name}_{artist_name}".replace(" ", "_").replace("/", "_")
    mono_path = input_folder / f"{safe_name}_MONO.wav"

    if mono_path.exists():
        print(f"Already exists: {mono_path}")
        return str(mono_path)

    search_query = f"{song_name} {artist_name} official audio"
    temp_path = str(input_folder / f"{safe_name}_STEREO.%(ext)s")

    print(f"Searching YouTube: {search_query}")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": temp_path,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "0",
        }],
        "default_search": "ytsearch1",
    }

    stereo_path = input_folder / f"{safe_name}_STEREO.mp3"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch1:{search_query}"])
    except Exception as e:
        print(f"Download error: {e}")
        raise

    if not stereo_path.exists():
        matches = list(input_folder.glob(f"{safe_name}_STEREO*"))
        if matches:
            stereo_path = matches[0]
        else:
            raise FileNotFoundError("Download failed — file not found")

    print(f"Downloaded: {stereo_path.name}")
    print("Converting to mono...")

    y, sr = librosa.load(str(stereo_path), sr=None, mono=True)

    target_duration = 59
    target_samples = target_duration * sr

    if len(y) > target_samples:
        print(f"Finding best {target_duration}s window...")

        # Calculate RMS energy in 1 second chunks
        chunk_size = sr
        energies = []
        for i in range(0, len(y) - chunk_size, chunk_size):
            chunk = y[i:i + chunk_size]
            energy = np.sqrt(np.mean(chunk ** 2))
            energies.append((i, energy))

        # Smooth energies to avoid picking a single loud spike
        window = 5
        smoothed = []
        for i in range(len(energies)):
            start = max(0, i - window)
            end = min(len(energies), i + window)
            avg = np.mean([e[1] for e in energies[start:end]])
            smoothed.append((energies[i][0], avg))

        # Skip first 15 seconds (usually intro) and last 15 seconds (outro)
        skip_start = int(15 * sr / chunk_size)
        skip_end = int(15 * sr / chunk_size)
        trimmed_energies = smoothed[skip_start:len(smoothed) - skip_end]

        # Find the peak energy position
        peak_idx = max(range(len(trimmed_energies)), key=lambda i: trimmed_energies[i][1])
        peak_sample = trimmed_energies[peak_idx][0]

        # Centre the 59 second window around the peak
        half = target_samples // 2
        start_sample = max(0, peak_sample - half)
        end_sample = start_sample + target_samples

        # Make sure we do not go past the end
        if end_sample > len(y):
            end_sample = len(y)
            start_sample = max(0, end_sample - target_samples)

        y = y[start_sample:end_sample]
        start_time = round(start_sample / sr, 1)
        print(f"Best window found at {start_time}s — extracting {target_duration}s")

        sf.write(str(mono_path), y, sr)

        stereo_path.unlink()

        print(f"Mono file saved: {mono_path}")
        return str(mono_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python downloader.py <song_name> <artist_name>")
        exit()
    result = download_and_convert(sys.argv[1], sys.argv[2])
    print(f"Ready: {result}")