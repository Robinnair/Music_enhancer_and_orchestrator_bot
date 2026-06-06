import json
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path
from scipy.signal import butter, filtfilt


MAPPING = {
    "vocals": "lead vocals + choir",
    "drums": "timpani + orchestral percussion",
    "bass": "cello + double bass",
    "other": "strings + brass + woodwinds"
}


def apply_orchestral_eq(y, sr, instrument):

    nyquist = sr / 2

    if instrument == "bass":
        cutoff = min(400 / nyquist, 0.99)
        b, a = butter(2, cutoff, btype='low')
        y = filtfilt(b, a, y) * 1.2
        print("  Applied cello EQ -> low pass 400Hz, boosted warmth")

    elif instrument == "drums":
        cutoff = min(300 / nyquist, 0.99)
        b, a = butter(2, cutoff, btype='low')
        y = filtfilt(b, a, y) * 1.1
        print("  Applied timpani EQ -> low pass 300Hz, boosted thump")

    elif instrument == "other":
        cutoff = min(200 / nyquist, 0.99)
        b, a = butter(2, cutoff, btype='high')
        y = filtfilt(b, a, y)
        print("  Applied strings EQ -> high pass 200Hz, removed mud")

    elif instrument == "vocals":
        print("  Vocals unchanged -> preserving emotional nuance")

    max_amp = np.max(np.abs(y))
    if max_amp > 0:
        y = y / max_amp

    return y


def apply_orchestral_eq_to_stems(stems_path):

    stems_folder = Path(stems_path)

    stems = (
        list(stems_folder.glob("*.wav")) +
        list(stems_folder.glob("*.mp3"))
    )

    for stem in stems:
        instrument = stem.stem.lower()
        print(f"\nOrchestrating: {stem.name}")
        y, sr = librosa.load(stem, sr=None)
        y = apply_orchestral_eq(y, sr, instrument)
        sf.write(stem, y, sr)


def orchestrate(instruments, stems_path=None):

    print("=" * 50)
    print("ORCHESTRATION AGENT")
    print("=" * 50)

    result = {i: MAPPING.get(i, "strings") for i in instruments}

    for original, orchestral in result.items():
        print(f"{original:10} ->  {orchestral}")

    if stems_path:
        print("\nApplying orchestral EQ to stems...")
        apply_orchestral_eq_to_stems(stems_path)

    output_file = Path(__file__).parent.parent / "orchestration.json"

    with open(output_file, "w") as f:
        json.dump(result, f, indent=4)

    print(f"\nSaved to: {output_file}")

    return result


if __name__ == "__main__":
    orchestrate(["vocals", "drums", "bass", "other"])
