# Documentation: Multi-Agent Polyphonic Song Reconstruction

## Approach Overview

The goal was to take a low-quality mono recording and produce a high-fidelity
stereo output with separated instruments, restored frequencies, and an
orchestral arrangement — while preserving the original vocal's emotional nuance.

Rather than building a single monolithic script, the system is designed as a
pipeline of six independent agents. Each agent has one responsibility, takes
a clear input, and produces a clear output. This makes the system easy to
debug, extend, and explain.

---

## Agent-by-Agent Decisions

### Analyser Agent

The first step is understanding what we are working with before touching the
audio. Librosa is used to extract tempo, energy, brightness, noise level,
dynamic range, spectral rolloff, and spectral bandwidth. These are not just
for reporting — the energy value is passed all the way to the Mixer Agent to
drive intelligent vocal weighting. This means every mix is tailored to the
specific song rather than using hardcoded values.

Why Librosa: it is the industry standard Python library for music feature
extraction. It is well documented, actively maintained, and handles edge cases
like variable tempo arrays cleanly.

### Separator Agent

Source separation is the most technically demanding step. Rather than attempting
to build a model from scratch, Demucs by Meta is used. Demucs (htdemucs model)
is a state-of-the-art deep learning separator that produces four stems: vocals,
drums, bass, and other.

Why Demucs over Spleeter: Spleeter is older and produces more artefacts,
particularly on vocals. Demucs is actively maintained, produces cleaner
separation, and handles a wider range of musical styles. The htdemucs model
specifically was chosen because it is the highest quality model available in
the Demucs package without requiring custom training.

### Orchestration Agent

This agent runs immediately after separation, before restoration. The reason
for this ordering is important — orchestral EQ is applied directly to the raw
separated stems while they still have their full dynamic range. Applying EQ
after noise reduction would process an already-modified signal.

Each instrument gets a different EQ curve to simulate its orchestral equivalent.
Bass receives a low pass filter at 400Hz with a 1.2x boost to simulate the
warmth of a cello. Drums receive a low pass at 300Hz with a 1.1x boost to
simulate the low thump of timpani. The other stem receives a high pass at 200Hz
to remove low-end mud and simulate the clarity of strings. Vocals are left
completely untouched — the brief specifically asked to preserve the original
vocal's emotional nuance, so no processing is applied.

Why SciPy Butterworth filters: Butterworth filters have a maximally flat
frequency response in the passband, meaning they shape the frequency content
without introducing ringing or phase distortion. This is important for musical
audio where phase coherence affects how natural the result sounds.

### Restoration Agent

After orchestration, each stem is cleaned. Noise level is estimated using zero
crossing rate. Stems above the threshold get gentle noise reduction via
noisereduce with prop_decrease=0.4, meaning only 40% of detected noise is
removed. A more aggressive reduction would destroy musical transients and
introduce musical artefacts.

Vocals are detected by filename and skipped entirely for noise reduction.
Any processing on the vocal stem risks damaging the emotional quality of the
performance, which is a core requirement of the brief.

After noise reduction, all stems go through frequency super-resolution. A
Butterworth high shelf filter isolates content above 8000Hz and blends it
back into the signal at 30% strength. Low quality mono recordings lose high
frequency content due to compression and bitrate limitations. This step
partially restores that content and adds air and presence back to the mix.

### Stereo Agent

Mono to stereo conversion uses the Haas effect for instruments. A 20ms delay
is applied to the right channel. The human auditory system interprets sounds
arriving at slightly different times as coming from a wider space, creating a
natural stereo image without simply duplicating the channel.

Vocals are kept perfectly centered — equal left and right with no delay. This
matches how vocals are mixed in professional recordings and preserves the
forward, intimate quality of the vocal performance.

### Mixer Agent

The final mix uses weighted summing rather than equal mixing. Equal mixing of
four stems at full volume would cause clipping and an unbalanced result.

The vocal weight is driven by the energy value from the Analyser Agent. Quiet
songs (average energy below 0.2) get a 1.5x vocal boost. Louder songs get 1.3x.
This means the system adapts to the specific song rather than applying a fixed
mix. Bass is weighted at 1.1x to maintain low-end presence. Drums are reduced
to 0.9x to sit underneath the vocals rather than competing with them.

The final output is normalized to 0.9x peak amplitude, leaving 10% headroom
to prevent clipping on playback. Each output file is timestamped so multiple
runs never overwrite each other.

---

## Why Multi-Agent Architecture

A single script could technically do all of this. The multi-agent approach was
chosen for three reasons.

First, each agent can be tested and run independently. If the stereo conversion
produces unexpected results, it can be tested in isolation without running the
full pipeline.

Second, the architecture mirrors how real audio production works. In a
professional studio, mastering, mixing, separation, and arrangement are handled
by different specialists. The agents model this separation of concerns.

Third, it makes the system extensible. The Orchestration Agent currently uses
EQ-based transformation. In a future version it could be replaced with a
neural synthesis agent that generates actual cello or strings audio from MIDI,
without changing any other part of the pipeline.

---

## Key Engineering Decisions

The orchestrator runs before the restoration agent, not after. This preserves
the full dynamic range of each stem when applying EQ. If restoration ran first,
the EQ would be shaping an already-normalized signal, reducing its effectiveness.

Noise reduction uses prop_decrease=0.4 rather than the default full reduction.
Full noise reduction on music stems removes musical content along with noise.
A partial reduction cleans the signal without destroying transients.

Vocals are treated as a special case throughout the entire pipeline. They skip
noise reduction, skip orchestral EQ, stay centered in the stereo field, and
receive a dynamic mix boost. Every decision in the pipeline respects the brief's
requirement to preserve the vocal's emotional nuance.

The Demucs separator uses the --mp3 flag to output compressed stems, which are
then rewritten as WAV during restoration. This keeps the separation step fast
while ensuring all downstream processing works with uncompressed audio.

---

## Limitations and Future Work

The frequency super-resolution step uses a traditional signal processing filter
rather than a neural model. A tool like AudioSR would produce more accurate
high frequency reconstruction by learning from large datasets of high and low
quality audio pairs. This was not feasible within the 24 hour assessment window
but is the most impactful improvement available.

The orchestration uses EQ to approximate orchestral timbres. True orchestral
rearrangement would require MIDI transcription of each stem, mapping to
orchestral instrument patches, and re-synthesis using a sample library or
neural audio synthesizer. This is a significantly more complex problem that
would constitute a full project in its own right.

The instrument detection in the analyser returns a fixed list of vocals, drums,
bass, and other — reflecting what Demucs separates rather than a genuine
detection of what instruments are present. A more sophisticated classifier
using a pretrained audio model could identify specific instruments within the
other stem.
