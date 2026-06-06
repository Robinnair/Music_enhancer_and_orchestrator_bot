import librosa
import noisereduce as nr
import soundfile as sf
import numpy as np
from pathlib import Path
from scipy.signal import butter, filtfilt


def calculate_noise_level(y):
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    return np.mean(zcr)


def apply_frequency_restoration(y, sr):

    print("Applying frequency super-resolution...")

    nyquist = sr / 2
    high_freq = min(8000 / nyquist, 0.99)

    b, a = butter(2, high_freq, btype='high', analog=False)
    high_shelf = filtfilt(b, a, y)

    restored = y + (high_shelf * 0.3)

    max_amp = np.max(np.abs(restored))
    if max_amp > 0:
        restored = restored / max_amp

    return restored


def restore_audio(input_file, output_file):

    print(f"\nProcessing: {input_file.name}")

    y, sr = librosa.load(input_file, sr=None)

    noise_level = calculate_noise_level(y)

    print(f"Noise Level: {noise_level:.5f}")

    if "vocal" in input_file.stem.lower():
        print("Vocals detected -> Skipping noise reduction to preserve quality")
        cleaned = y

    elif noise_level > 0.08:
        print("High noise detected -> Applying gentle restoration")
        cleaned = nr.reduce_noise(y=y, sr=sr, prop_decrease=0.4)

    else:
        print("Audio clean -> Skipping noise reduction")
        cleaned = y

    cleaned = apply_frequency_restoration(cleaned, sr)

    max_amp = np.max(np.abs(cleaned))
    if max_amp > 0:
        cleaned = cleaned / max_amp

    sf.write(output_file, cleaned, sr)

    print(f"Saved: {output_file.name}")


def process_all_stems(stems_path):

    project_root = Path(__file__).parent.parent
    stems_folder = Path(stems_path)
    restored_folder = project_root / "outputs" / "restored"
    restored_folder.mkdir(exist_ok=True)

    print("=" * 50)
    print("RESTORATION AGENT")
    print("=" * 50)
    print(f"Reading stems from: {stems_folder}")

    stems = (
        list(stems_folder.glob("*.wav")) +
        list(stems_folder.glob("*.mp3"))
    )

    if not stems:
        print("No stems found.")
        return

    for stem in stems:
        output_file = restored_folder / f"{stem.stem}_clean.wav"
        restore_audio(stem, output_file)

    print("\nRestoration Complete")


if __name__ == "__main__":
    print("Run this via main.py")
    print("python main.py <audio_file>")
