import librosa
import soundfile as sf
import numpy as np
from pathlib import Path
from datetime import datetime


def mix_tracks(song_name, analysis=None):

    project_root = Path(__file__).parent.parent
    stereo_folder = project_root / "outputs" / "stereo"
    final_folder = project_root / "outputs" / "final"
    final_folder.mkdir(exist_ok=True)

    stems = list(stereo_folder.glob("*.wav"))

    if not stems:
        print("No stereo stems found.")
        return

    print("=" * 50)
    print("MIXER AGENT")
    print("=" * 50)

    loaded_stems = []
    sample_rate = None

    for stem in stems:
        print(f"Loading: {stem.name}")
        audio, sr = librosa.load(stem, sr=None, mono=False)
        if sample_rate is None:
            sample_rate = sr
        loaded_stems.append(audio)

    min_length = min(s.shape[-1] for s in loaded_stems)

    loaded_stems = [
        s[:, :min_length] if s.ndim > 1 else s[:min_length]
        for s in loaded_stems
    ]

    print("\nMixing stems...")

    energy = analysis.get("average_energy", 0.3) if analysis else 0.3

    weights = []
    for stem in stems:
        name = stem.name.lower()
        if "vocal" in name:
            boost = 1.5 if energy < 0.2 else 1.3
            weights.append(boost)
            print(f"  vocals weight: {boost} (energy={round(energy, 3)})")
        elif "bass" in name:
            weights.append(1.0)
            print(f"  bass weight: 1.0")
        elif "drum" in name:
            weights.append(2.5)
            print(f"  drums weight: 2.5")
        else:
            weights.append(1.4)
            print(f"  other weight: 1.4")

    weighted_stems = [s * w for s, w in zip(loaded_stems, weights)]

    mixed = np.sum(weighted_stems, axis=0)

    max_amp = np.max(np.abs(mixed))
    if max_amp > 0:
        mixed = (mixed / max_amp) * 0.95

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = final_folder / f"{song_name}_{timestamp}_final_mix.wav"

    sf.write(output_file, mixed.T, sample_rate)

    print(f"\nMix Complete")
    print(f"Saved: {output_file}")
    return str(output_file)


if __name__ == "__main__":
    print("Run this via main.py")
    print("python main.py <audio_file>")