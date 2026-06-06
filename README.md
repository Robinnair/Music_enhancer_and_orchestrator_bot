# Multi-Agent Polyphonic Song Reconstruction

A multi-agent audio processing pipeline that takes a low-quality mono recording
and reconstructs a high-fidelity stereo version by separating instruments,
applying frequency super-resolution, orchestrating stems, and producing a
clean final mix.

---

## Problem

Low-quality mono recordings lose stereo width, contain noise, have missing high
frequencies, and have instruments muddled together. This pipeline separates,
restores, orchestrates, and reconstructs them into a clean stereo output.

---

## Architecture

```
Input (Mono WAV/MP3)
        |
   Analyser Agent          -> analysis.json
        |
   Separator Agent         -> outputs/htdemucs/vocals, drums, bass, other
        |
   Orchestration Agent     -> orchestration.json + EQ applied to stems
        |
   Restoration Agent       -> outputs/restored/ (noise reduced + frequency restored)
        |
   Stereo Agent            -> outputs/stereo/ (stereo stems via Haas effect)
        |
   Mixer Agent             -> outputs/final/<songname>_<timestamp>_final_mix.wav
```

---

## Agents

### Analyser Agent (agents/analyser.py)
Loads the audio and extracts musical features using Librosa. Outputs a JSON
report containing tempo, sample rate, duration, energy, brightness, noise level,
dynamic range, spectral rolloff, and spectral bandwidth. The analysis data is
passed downstream to drive intelligent mixing decisions in the Mixer Agent.

### Separator Agent (agents/separator.py)
Uses Meta's Demucs (htdemucs model) to separate the audio into four stems:
vocals, drums, bass, and other. Demucs is a state-of-the-art deep learning
source separation model that outperforms older tools like Spleeter in both
vocal preservation and instrument isolation.

### Orchestration Agent (agents/orchestrator.py)
Maps detected instruments to their orchestral equivalents and applies
instrument-specific EQ to each stem to simulate orchestral timbre.
Bass receives a cello EQ (low pass 400Hz with warmth boost).
Drums receive a timpani EQ (low pass 300Hz with thump boost).
Other instruments receive a strings EQ (high pass 200Hz to remove mud).
Vocals are left completely untouched to preserve the original emotional nuance
as specified in the brief. Saves an orchestration.json report.

### Restoration Agent (agents/restoration.py)
Cleans each separated stem. Vocals skip noise reduction entirely to preserve
quality. Other stems are cleaned gently using noisereduce with 40% reduction
strength to avoid over-processing. All stems then go through frequency
super-resolution which uses a scipy Butterworth high shelf filter to restore
missing high frequencies lost in the original low-quality mono recording.
All stems are normalized to consistent volume.

### Stereo Agent (agents/stereo.py)
Converts mono stems to stereo. Vocals are kept centered with equal left and
right channels to preserve natural placement. Instrument stems use the Haas
effect (a 20ms delay on the right channel) to create natural stereo width
without phase cancellation.

### Mixer Agent (agents/mixer.py)
Combines all stereo stems into a final mix using analysis-driven weighted
summing. Vocal boost is dynamically adjusted based on the song's average energy
from the analyser output (1.5x for quiet songs, 1.3x for louder songs). Bass
is set to 1.1x and drums to 0.9x. Output is normalized with 0.9x headroom to
prevent clipping. Each output file is timestamped so runs never overwrite
each other.

---

## Technologies

| Tool | Purpose | Why Chosen |
|---|---|---|
| Demucs | Source separation | Best open source model for music, actively maintained by Meta |
| Librosa | Audio analysis | Industry standard for music feature extraction in Python |
| Noisereduce | Noise reduction | Effective spectral noise gating with controllable strength |
| SciPy | Frequency restoration and EQ | Butterworth filters for high shelf and instrument-specific EQ |
| Soundfile | Audio I/O | Reliable WAV read/write with full sample rate support |
| NumPy | Signal processing | Fast array operations for audio manipulation |

---

## Setup

```bash
python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt
```

---

## Usage

Place your mono WAV or MP3 file inside the input/ folder, then run:

```bash
python main.py "input/your_song_mono.wav"
```

Output will be saved to:

```
outputs/final/<your_song>_<timestamp>_final_mix.wav
```

---

## Project Structure

```
E_skillveda_project/
|
|-- agents/
|   |-- __init__.py
|   |-- analyser.py
|   |-- separator.py
|   |-- restoration.py
|   |-- stereo.py
|   |-- orchestrator.py
|   |-- mixer.py
|
|-- input/
|-- outputs/
|   |-- final/
|
|-- main.py
|-- requirements.txt
|-- README.md
|-- analysis.json
|-- orchestration.json
```

---

## Future Improvements

- Neural audio super-resolution using AudioSR or similar transformer models
- MIDI-based orchestral generation to synthesize real instrument sounds
- Mid-side processing for more professional stereo imaging
- LLM-powered orchestration agent for richer arrangement descriptions
- Web interface for non-technical users
