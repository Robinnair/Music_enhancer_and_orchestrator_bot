import librosa
import soundfile as sf
import numpy as np
from pathlib import Path


def mono_to_stereo(input_file, output_file):

    print(f"\nProcessing: {input_file.name}")

    y, sr = librosa.load(input_file, sr=None, mono=True)

    if "vocal" in input_file.stem.lower():
        left = y * 1.0
        right = y * 1.0
        print("  Vocals centered in stereo field")

    else:
        delay_ms = 20
        delay_samples = int(sr * delay_ms / 1000)
        left = y.copy()
        right = np.concatenate([np.zeros(delay_samples), y])[:len(y)]
        print(f"  Haas effect applied -> {delay_ms}ms delay on right channel")

    stereo_audio = np.vstack([left, right]).T

    sf.write(output_file, stereo_audio, sr)

    print(f"Saved: {output_file.name}")


def process_all_files():

    project_root = Path(__file__).parent.parent
    restored_folder = project_root / "outputs" / "restored"
    stereo_folder = project_root / "outputs" / "stereo"
    stereo_folder.mkdir(exist_ok=True)

    stems = list(restored_folder.glob("*.wav"))

    if not stems:
        print("No restored stems found.")
        return

    print("=" * 50)
    print("STEREO AGENT")
    print("=" * 50)

    for stem in stems:
        output_file = stereo_folder / f"{stem.stem}_stereo.wav"
        mono_to_stereo(stem, output_file)

    print("\nStereo Processing Complete")


if __name__ == "__main__":
    process_all_files()
