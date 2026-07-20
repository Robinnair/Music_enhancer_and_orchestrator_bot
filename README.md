# E_skillveda_project — Multi-Agent Audio Restoration & YouTube Automation Pipeline

A fully autonomous AI music content pipeline that downloads songs, restores and orchestrates them through six intelligent agents, generates synchronized lyric videos with four colored stem waveforms, and publishes to YouTube Shorts automatically every day with zero human involvement after initial setup.

---

## What It Does

Every morning the pipeline wakes up, picks the next song from a queue, downloads it from YouTube, finds the most interesting 59-second window based on the song's emotional character, processes it through a multi-agent audio restoration system, fetches lyrics and aligns them to the audio using Whisper on isolated vocals, auto-detects and translates non-English lyrics, generates a vertical waveform video showing all four separated stems in different colors, writes a unique RAG-powered description using Wikipedia and live web search, and uploads the finished video to YouTube Shorts automatically.

---

## Pipeline Architecture

```
songs_queue.txt
        |
DOWNLOADER AGENT
  — Searches YouTube via yt-dlp
  — Downloads best quality audio
  — Converts stereo to mono
  — Three window modes:
      peak  → highest RMS energy 59s window
      intro → first 59 seconds
      quiet → lowest non-silent 59s window
        |
ANALYSER AGENT
  — Extracts tempo, energy, brightness, noise level
  — Spectral rolloff and bandwidth
  — Saves analysis.json
        |
ORCHESTRATION AGENT
  — Runs BEFORE restoration (full dynamic range)
  — Bass → cello: Butterworth low pass 400Hz
  — Drums → timpani: Butterworth low pass 300Hz
  — Other → strings: Butterworth high pass 200Hz
  — Vocals → unchanged
        |
SEPARATOR AGENT
  — Demucs htdemucs_ft fine-tuned model
  — Separates into: vocals / drums / bass / other
  — Cleaner separation with less inter-stem bleed
        |
RESTORATION AGENT
  — Vocals: skip noise reduction entirely
  — Other stems: 40% noisereduce
  — All stems: Butterworth high shelf frequency super-resolution
        |
STEREO AGENT
  — Haas effect: 20ms delay on right channel
  — Vocals centered
  — Instruments: natural stereo width
        |
MIXER AGENT
  — Vocal boost: 1.5x (quiet songs) or 1.3x (loud songs)
  — Drums: 2.5x, Melody: 1.4x, Bass: 1.0x
  — Normalized to 0.95x peak amplitude
        |
LYRICS AGENT
  — DuckDuckGo finds exact Genius URL
  — Fetches via Genius API
  — Auto-detects language with langdetect
        |
ALIGNMENT AGENT
  — Loads vocal stem (not full mix)
  — Whisper small model transcribes vocal stem
  — Auto-detects language, forces English if invalid code
  — Ollama judge: MATCH / MISMATCH / UNCERTAIN
  — If MISMATCH: uses Whisper transcription directly
  — If non-English: Ollama translates with context
  — If English: fuzzy match to clean Genius lines
  — Timestamp sanity validation
  — Saves enriched timed_lyrics.json
        |
VIDEO AGENT
  — 1080x1920 vertical format (9:16 for Shorts)
  — 24fps, four colored stem waveforms:
      VOCALS  — pink  (#FF6B9D)
      DRUMS   — yellow (#FFD93D)
      BASS    — green (#6BCB77)
      MELODY  — blue  (#4D96FF)
  — Mirrored waveforms with glow effect
  — Three-line scrolling lyrics
  — Progress bar, timestamp, title overlay
        |
DESCRIPTION GENERATOR AGENT
  — Wikipedia fetch for song and artist
  — DuckDuckGo searches for TV/movie appearances
  — FAISS RAG retrieves most relevant chunks
  — Ollama generates unique human-sounding description
  — Extracts pop culture hashtags automatically
        |
UPLOAD AGENT
  — YouTube Data API v3 via OAuth 2.0
  — One-time browser login, token saved permanently
  — Uploads as public YouTube Short
  — Marks song done in queue with date and URL
  — Logs everything to app.log
```

---

## LangGraph Pipeline (New Architecture)

The pipeline is also implemented as a LangGraph state machine for more intelligent routing:

```
pipeline_state.py     — Shared state TypedDict
pipeline_nodes.py     — Each agent wrapped as a LangGraph node
pipeline_graph.py     — Graph with conditional edges and retry loops
langgraph_scheduler.py — Reads queue and invokes the graph
```

Key features of the LangGraph implementation:
- Genre classification routes songs through different processing paths
- Alignment judge scores output and retries with escalating strategies
- Max 3 retries before flagging as needs_review in queue
- Every decision logged to app.log with scores and confidence levels

---

## Genre Paths

| Genre | Lyrics | Whisper | Translation | Window |
|---|---|---|---|---|
| Video Game Instrumental | Skip | Skip | No | peak |
| Video Game Vocal | Genius | Vocal stem | No | peak |
| Anime Japanese | Genius | Vocal stem | Ollama | intro |
| Vocaloid | Manual | Skip | Manual | peak |
| Indie/Alternative | Genius | Vocal stem | No | quiet |
| Electronic | Skip | Skip | No | peak |
| Classic Rock/Pop | Genius | Vocal stem | No | peak |

---

## Songs Queue Format

```
SongName|ArtistName|status|window_mode
SongName|ArtistName|done|peak|2026-06-21|https://youtube.com/watch?v=...
SongName|ArtistName|needs_review|quiet
```

**Status values:** pending, done, error, needs_review, skipped
**Window modes:** peak, intro, quiet

---

## Setup

```bash
# Clone
git clone https://github.com/Robinnair/Music_enhancer_and_orchestrator_bot.git
cd E_skillveda_project

# Virtual environment (Windows)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull Ollama models
ollama pull llama3.2
ollama pull nomic-embed-text
```

Place `client_secrets.json` from Google Cloud Console in the project root.

---

## Usage

### Automated daily pipeline (original)
```bash
python scheduler.py
```

### Automated daily pipeline (LangGraph)
```bash
python langgraph_scheduler.py
```

### Manual run on a specific file
```bash
python main.py "input/song_MONO.wav" "Artist Name"
```

### Manual upload with description
```bash
python upload_video.py "outputs/final/song_video.mp4" "Song Name" "Artist Name"
```

### Manual per-agent commands

```bash
# Instrumental songs (no lyrics)
python agents/downloader.py "Song Name" "Artist" "peak"
python main.py "input/Song_Artist_MONO.wav" "Artist"
python agents/video.py "outputs/final/EXACT_FILENAME.wav" "Song_Artist"
python upload_video.py "outputs/final/Song_Artist_video.mp4" "Song Name" "Artist"

# Lyric songs (English)
python agents/downloader.py "Song Name" "Artist" "peak"
python main.py "input/Song_Artist_MONO.wav" "Artist"
python test_lyrics.py
python agents/aligner.py "outputs/final/EXACT_FILENAME.wav"
python agents/video.py "outputs/final/EXACT_FILENAME.wav" "Song_Artist"
python upload_video.py "outputs/final/Song_Artist_video.mp4" "Song Name" "Artist"

# Rerun just the mix (stems already exist)
python -c "
import json
from agents.mixer import mix_tracks
with open('analysis.json') as f:
    analysis = json.load(f)
mix_tracks('Song_Artist_MONO', analysis)
"
```

---

## Windows Task Scheduler Setup

```
Program:   C:\path\to\.venv\Scripts\python.exe
Arguments: scheduler.py
Start in:  C:\path\to\E_skillveda_project
```

Conditions: uncheck Stop if switching to battery power
Settings: check Run as soon as possible after scheduled start is missed

---

## Known Issues and Fixes

**cffi _cffi_backend not found**
```bash
pip install cffi==1.17.1 --force-reinstall
pip install cryptography --force-reinstall
```

**Windows PermissionError on output folders**
Already handled in main.py and scheduler.py with try/except fallback.

**Librosa cannot load MP3**
All downloads save as WAV. Convert old MP3s with:
```bash
ffmpeg -i song.mp3 song.wav
```

**Whisper detects wrong language (Latin)**
Already handled — invalid codes force English fallback.

**token.json expired**
```bash
del token.json
python upload_video.py ...
```

**numpy circular import**
```bash
pip install numpy --force-reinstall
```

**Ollama not running**
```bash
ollama serve
```

**yt-dlp 403 Forbidden**
```bash
pip install yt-dlp --upgrade
```
Then add to downloader ydl_opts:
```python
"cookiesfrombrowser": ("chrome",),
```

**Task Scheduler not firing at 6AM**
Enable Wake the computer to run this task in Conditions tab.

---

## Vocaloid Songs

Whisper cannot transcribe synthesized voices. Manually create timed_lyrics.json:

```json
{
  "song": "Song Name",
  "artist": "Artist",
  "language_detected": "ja",
  "ollama_verdict": "MANUAL",
  "timestamp_issues": [],
  "lines": [
    {"start": 0.98, "end": 5.0, "text": "English translation", "confidence": "manual"}
  ]
}
```

---

## needs_review Songs

When a song is flagged as needs_review after 3 failed alignment retries:

1. Check app.log for the failure reason and scores
2. Manually edit outputs/timed_lyrics.json with correct timestamps
3. Regenerate video: `python agents/video.py "outputs/final/FILENAME.wav" "Song_Artist"`
4. Upload: `python upload_video.py "outputs/final/video.mp4" "Song" "Artist"`
5. Update songs_queue.txt to done or skipped

---

## Technologies

| Tool | Purpose |
|---|---|
| Demucs htdemucs_ft | Source separation (fine-tuned, less bleed) |
| Librosa | Audio feature extraction |
| Noisereduce | Spectral noise gating |
| SciPy Butterworth | EQ and frequency super-resolution |
| Whisper stable-ts | Lyric transcription with word-level timestamps |
| Matplotlib + FFmpeg | Video frame rendering and encoding |
| LyricsGenius | Lyrics fetching |
| langdetect | Language detection |
| Wikipedia API | Song and artist information |
| ddgs (DuckDuckGo) | Pop culture reference search |
| FAISS | Local vector store for RAG |
| Ollama llama3.2 | Description generation, judge, translation |
| LangChain | RAG framework |
| LangGraph | Pipeline state machine with retry loops |
| yt-dlp | YouTube audio download |
| YouTube Data API v3 | Upload with OAuth 2.0 |
| Windows Task Scheduler | Daily automation |

---

## Project Structure

```
E_skillveda_project/
├── agents/
│   ├── analyser.py
│   ├── downloader.py
│   ├── separator.py
│   ├── orchestrator.py
│   ├── restoration.py
│   ├── stereo.py
│   ├── mixer.py
│   ├── lyrics.py
│   ├── aligner.py
│   ├── video.py
│   ├── description_generator.py
│   └── upload.py
├── pipeline_state.py
├── pipeline_nodes.py
├── pipeline_graph.py
├── langgraph_scheduler.py
├── main.py
├── scheduler.py
├── upload_video.py
├── test_lyrics.py
├── songs_queue.txt
├── requirements.txt
├── README.md
└── .gitignore
```

**Never commit:** client_secrets.json, token.json, input/, outputs/

---

## Requirements

```
librosa
numpy
soundfile
noisereduce
demucs
scipy
lyricsgenius
stable-ts
openai-whisper
matplotlib
ffmpeg-python
yt-dlp
deep-translator
langdetect
ddgs
wikipedia-api
langchain
langchain-ollama
langchain-community
langchain-core
faiss-cpu
google-auth
google-auth-oauthlib
google-api-python-client
langgraph
python-docx
requests
```

---

## YouTube Channel

**@robinnair1703** — AI audio restoration. Game music and classic songs rebuilt from scratch. New video daily.

Pin this comment on every upload:
```
Which stem surprised you the most? Drop a song request below!
```

---

## Future Improvements

- AudioSR neural audio super-resolution replacing Butterworth high shelf
- LUFS loudness normalization to YouTube recommended -14 LUFS
- Before/after comparison video showing original mono vs restored stereo
- Automatic comment pinning via YouTube API
- Song request reader from YouTube comments
- Thumbnail generation
- Web dashboard for queue monitoring