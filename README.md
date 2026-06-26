# E_skillveda_project — Multi-Agent Audio Restoration & YouTube Automation Pipeline

A fully autonomous AI music content pipeline that takes any song, restores and orchestrates it through six intelligent agents, generates a synchronized lyric video, and publishes it to YouTube Shorts automatically every day with zero human involvement after initial setup.

---

## What It Does

Every morning the pipeline wakes up, picks the next song from a queue, downloads it from YouTube, finds the most energetically interesting 59-second window, processes it through a multi-agent audio restoration system, fetches and translates lyrics, aligns them frame by frame using Whisper, generates a vertical waveform video, writes a unique RAG-powered description using Wikipedia and live web search, and uploads the finished video to YouTube Shorts automatically.

---

## Pipeline Architecture

```
songs_queue.txt
        |
DOWNLOADER AGENT
  — Searches YouTube via yt-dlp
  — Downloads best quality audio
  — Converts stereo to mono
  — Finds best 59-second energy window (skips intro/outro)
        |
ANALYSER AGENT
  — Extracts tempo, energy, brightness, noise level
  — Spectral rolloff and bandwidth analysis
  — Outputs analysis.json used downstream by mixer
        |
ORCHESTRATION AGENT
  — Maps stems to orchestral equivalents
  — Bass to cello (Butterworth low pass 400Hz)
  — Drums to timpani (Butterworth low pass 300Hz)
  — Other to strings (Butterworth high pass 200Hz)
  — Vocals unchanged
        |
SEPARATOR AGENT
  — Demucs htdemucs model
  — Separates into vocals / drums / bass / other
        |
RESTORATION AGENT
  — Vocals skip noise reduction entirely
  — Other stems: 40% noisereduce
  — All stems: Butterworth high shelf frequency super-resolution
        |
STEREO AGENT
  — Haas effect 20ms delay on right channel
  — Vocals centered
  — Instruments: natural stereo width
        |
MIXER AGENT
  — Analysis-driven vocal boost (1.3x or 1.5x based on energy)
  — Drums 2.5x, other 1.4x, bass 1.0x
  — Normalized to 0.95x peak amplitude
  — Timestamped output
        |
LYRICS AGENT
  — Fetches from Genius API
  — Auto-detects Japanese and Korean
  — Batch translates to English via Ollama if needed
  — Saves original and translated versions
        |
ALIGNMENT AGENT
  — Whisper small model transcribes actual sung content
  — Word-level timestamps mapped to lyric lines
  — Fuzzy matching cleans up transcription
  — Auto-detects instrumental tracks and skips
        |
VIDEO AGENT
  — 1080x1920 vertical format (9:16 for Shorts)
  — Animated mirrored green waveform
  — Three-line scrolling lyrics (prev / current / next)
  — Progress bar and timestamp
  — FFmpeg encodes final MP4
        |
DESCRIPTION GENERATOR AGENT
  — Wikipedia fetch for song and artist info
  — DuckDuckGo search for TV and movie appearances
  — FAISS RAG retrieves most relevant chunks
  — Ollama generates unique human-sounding description
  — Extracts pop culture hashtags automatically
        |
UPLOAD AGENT
  — YouTube Data API v3
  — OAuth 2.0 (one-time browser login, token saved)
  — Uploads as public YouTube Short
  — Marks song done in queue with URL and date
  — Logs everything to scheduler.log
```

---

## Technologies

| Tool | Purpose | Why Chosen |
|---|---|---|
| Demucs | Source separation | Best open source model, maintained by Meta, hybrid architecture |
| Librosa | Audio analysis | Industry standard for music feature extraction |
| Noisereduce | Noise reduction | Effective spectral noise gating with controllable strength |
| SciPy | Butterworth filters | Maximally flat passband, frequencies kept are not distorted |
| Whisper stable-ts | Lyric alignment | Word-level timestamps, runs locally, no API cost |
| Matplotlib and FFmpeg | Video generation | Full control over rendering, no external dependencies |
| LyricsGenius | Lyrics fetching | Free API, large database |
| Wikipedia API | Song and artist info | Free, reliable, structured |
| DuckDuckGo Search ddgs | Pop culture references | No API key required |
| FAISS | Vector store for RAG | Fast similarity search, runs locally |
| Ollama Llama 3.2 | Description generation and translation | Free, local, no API cost |
| LangChain | RAG framework | Clean abstraction for retrieval and generation |
| yt-dlp | Audio download | No API key, downloads best quality |
| YouTube Data API v3 | Upload | Official API, OAuth authentication |
| Windows Task Scheduler | Automation | Native Windows scheduling |

---

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/E_skillveda_project.git
cd E_skillveda_project

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

ollama pull llama3.2
ollama pull nomic-embed-text
```

Place `client_secrets.json` from Google Cloud Console in the project root.

---

## Usage

### Manual run on a specific file
```bash
python main.py "input/song_MONO.wav" "Artist Name"
```

### Process and upload a specific song manually
```bash
python upload_video.py "outputs/final/song_video.mp4" "Song Name" "Artist Name"
```

### Automated daily run
```bash
python scheduler.py
```

### Songs queue format
```
Megalovania|Toby Fox|done|2026-06-21|https://youtube.com/watch?v=...
Dire Dire Docks|Koji Kondo|pending
Creep|Radiohead|pending
```

---

## Project Structure

```
E_skillveda_project/
|-- agents/
|   |-- analyser.py
|   |-- downloader.py
|   |-- separator.py
|   |-- orchestrator.py
|   |-- restoration.py
|   |-- stereo.py
|   |-- mixer.py
|   |-- lyrics.py
|   |-- aligner.py
|   |-- video.py
|   |-- description_generator.py
|   |-- upload.py
|-- input/
|-- outputs/
|   |-- final/
|-- main.py
|-- scheduler.py
|-- upload_video.py
|-- songs_queue.txt
|-- requirements.txt
|-- README.md
|-- .gitignore
```

---

## Automation

Set Windows Task Scheduler to run scheduler.py daily at 6AM:

- Program: path to .venv/Scripts/python.exe
- Arguments: scheduler.py
- Start in: path to E_skillveda_project
- Conditions: uncheck Stop if switching to battery power
- Settings: check Run as soon as possible after scheduled start is missed

---

## Important

Never commit these files to GitHub:
- client_secrets.json contains your Google OAuth credentials
- token.json contains your YouTube access token
- input/ folder contains downloaded audio files
- outputs/ folder contains generated files

All are listed in .gitignore.

---

## Future Improvements

- Neural audio super-resolution using AudioSR instead of Butterworth filters
- MIDI-based orchestral synthesis using Basic Pitch by Spotify
- Thumbnail generation for non-Shorts uploads
- Web dashboard to monitor queue and view analytics
- Support for multiple YouTube channels
- Automatic language detection for aligner