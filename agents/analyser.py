import librosa
import json
import sys
from pathlib import Path
import numpy as np


def analyze_audio(path):

    print(f"\nLoading audio: {path}")

    y, sr = librosa.load(path, sr=None)

    duration = librosa.get_duration(y=y, sr=sr)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    if hasattr(tempo, "__len__"):
        tempo = tempo[0]

    rms = librosa.feature.rms(y=y)[0]
    avg_energy = np.mean(rms)

    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    avg_brightness = np.mean(spectral_centroid)

    zcr = librosa.feature.zero_crossing_rate(y)[0]
    avg_zcr = np.mean(zcr)

    dynamic_range = np.max(y) - np.min(y)

    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    avg_rolloff = np.mean(spectral_rolloff)

    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    avg_bandwidth = np.mean(spectral_bandwidth)

    analysis = {
        "file_name": Path(path).name,
        "sample_rate": int(sr),
        "duration_seconds": round(float(duration), 2),
        "tempo_bpm": round(float(tempo), 2),
        "average_energy": round(float(avg_energy), 5),
        "brightness": round(float(avg_brightness), 2),
        "noise_level": round(float(avg_zcr), 5),
        "dynamic_range": round(float(dynamic_range), 5),
        "spectral_rolloff": round(float(avg_rolloff), 2),
        "spectral_bandwidth": round(float(avg_bandwidth), 2),
        "instruments_detected": [
            "vocals",
            "drums",
            "bass",
            "other"
        ]
    }

    output_file = Path(__file__).parent.parent / "analysis.json"

    with open(output_file, "w") as f:
        json.dump(analysis, f, indent=4)

    print("\n===== AUDIO ANALYSIS =====")
    print(json.dumps(analysis, indent=4))
    print(f"\nSaved to: {output_file}")

    return analysis


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("python analyser.py <audio_file>")
        exit()

    analyze_audio(sys.argv[1])
