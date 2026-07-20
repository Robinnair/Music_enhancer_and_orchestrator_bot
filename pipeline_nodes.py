import json
import traceback
from datetime import datetime
from pathlib import Path
from pipeline_state import PipelineState


def log_event(state: PipelineState, node: str, event: str, data: dict = None, score: float = None) -> list:
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "song": state.get("song", ""),
        "artist": state.get("artist", ""),
        "node": node,
        "event": event,
        "data": data or {},
        "score": score,
        "retry_count": state.get("alignment_retry_count", 0)
    }
    log = state.get("app_log", [])
    log.append(entry)

    with open("app.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[{entry['timestamp']}] [{node}] {event}")
    return log


# ── NODE 1: DOWNLOADER ────────────────────────────────────────────────────────
def node_downloader(state: PipelineState) -> dict:
    from agents.downloader import download_and_convert

    song = state["song"]
    artist = state["artist"]
    window_mode = state.get("window_mode", "peak")

    log = log_event(state, "DOWNLOADER", f"Starting download: {song} by {artist}")

    try:
        audio_path = download_and_convert(song, artist, window_mode)
        if not audio_path:
            raise ValueError("Downloader returned None")

        log = log_event(state, "DOWNLOADER", "Download complete", {"audio_path": audio_path})
        return {"audio_path": audio_path, "app_log": log, "status": "running"}

    except Exception as e:
        log = log_event(state, "DOWNLOADER", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 2: ANALYSER ──────────────────────────────────────────────────────────
def node_analyser(state: PipelineState) -> dict:
    from agents.analyser import analyze_audio

    log = log_event(state, "ANALYSER", "Analysing audio")

    try:
        analysis = analyze_audio(state["audio_path"])
        log = log_event(state, "ANALYSER", "Analysis complete", {
            "tempo": analysis.get("tempo_bpm"),
            "energy": analysis.get("average_energy"),
            "brightness": analysis.get("brightness")
        })
        return {"analysis": analysis, "app_log": log}

    except Exception as e:
        log = log_event(state, "ANALYSER", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 3: GENRE CLASSIFIER ──────────────────────────────────────────────────
def node_genre_classifier(state: PipelineState) -> dict:
    from langchain_ollama import OllamaLLM

    llm = OllamaLLM(model="llama3.2")
    analysis = state.get("analysis", {})

    log = log_event(state, "GENRE_CLASSIFIER", "Classifying genre")

    prompt = f"""Song: {state['song']} by {state['artist']}
Tempo: {analysis.get('tempo_bpm')} BPM
Energy: {analysis.get('average_energy')}
Brightness: {analysis.get('brightness')}

Classify into exactly one category:
- video_game_instrumental
- video_game_vocal
- anime_japanese
- vocaloid
- indie_alternative
- electronic
- classic_rock_pop

Return only the category name, nothing else."""

    try:
        genre = llm.invoke(prompt).strip().lower()
        valid = ["video_game_instrumental", "video_game_vocal", "anime_japanese",
                 "vocaloid", "indie_alternative", "electronic", "classic_rock_pop"]
        if genre not in valid:
            genre = "indie_alternative"

        log = log_event(state, "GENRE_CLASSIFIER", f"Genre: {genre}", {"genre": genre})
        return {"genre": genre, "app_log": log}

    except Exception as e:
        log = log_event(state, "GENRE_CLASSIFIER", f"ERROR: {e} — defaulting to indie_alternative")
        return {"genre": "indie_alternative", "app_log": log}


# ── NODE 4: ORCHESTRATOR ──────────────────────────────────────────────────────
def node_orchestrator(state: PipelineState) -> dict:
    from agents.orchestrator import orchestrate

    log = log_event(state, "ORCHESTRATOR", "Orchestrating stems")

    try:
        analysis = state.get("analysis", {})
        orchestrate(analysis.get("instruments_detected", []))
        log = log_event(state, "ORCHESTRATOR", "Orchestration complete")
        return {"app_log": log}

    except Exception as e:
        log = log_event(state, "ORCHESTRATOR", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 5: SEPARATOR ─────────────────────────────────────────────────────────
def node_separator(state: PipelineState) -> dict:
    from agents.separator import separate_audio

    log = log_event(state, "SEPARATOR", "Separating stems with Demucs")

    try:
        separate_audio(state["audio_path"])
        song_stem = Path(state["audio_path"]).stem
        stems_path = str(Path("outputs/htdemucs") / song_stem)
        log = log_event(state, "SEPARATOR", "Separation complete", {"stems_path": stems_path})
        return {"stems_path": stems_path, "app_log": log}

    except Exception as e:
        log = log_event(state, "SEPARATOR", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 6: RESTORATION ───────────────────────────────────────────────────────
def node_restoration(state: PipelineState) -> dict:
    from agents.restoration import process_all_stems

    genre = state.get("genre", "indie_alternative")
    log = log_event(state, "RESTORATION", f"Restoring stems (genre: {genre})")

    try:
        stems_path = Path(state["stems_path"])

        # Electronic genre skips noise reduction
        if genre == "electronic":
            log = log_event(state, "RESTORATION", "Electronic genre — skipping noise reduction")
        
        process_all_stems(stems_path)
        log = log_event(state, "RESTORATION", "Restoration complete")
        return {"app_log": log}

    except Exception as e:
        log = log_event(state, "RESTORATION", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 7: STEREO ────────────────────────────────────────────────────────────
def node_stereo(state: PipelineState) -> dict:
    from agents.stereo import process_all_files

    log = log_event(state, "STEREO", "Converting to stereo")

    try:
        process_all_files()
        log = log_event(state, "STEREO", "Stereo conversion complete")
        return {"app_log": log}

    except Exception as e:
        log = log_event(state, "STEREO", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 8: MIXER ─────────────────────────────────────────────────────────────
def node_mixer(state: PipelineState) -> dict:
    from agents.mixer import mix_tracks

    log = log_event(state, "MIXER", "Mixing stems")

    try:
        song_stem = Path(state["audio_path"]).stem
        analysis = state.get("analysis", {})
        mix_tracks(song_stem, analysis)

        final_folder = Path("outputs/final")
        final_files = sorted(final_folder.glob(f"{song_stem}*.wav"))
        if not final_files:
            raise FileNotFoundError("Final mix not found")

        final_audio = str(final_files[-1])
        log = log_event(state, "MIXER", "Mix complete", {"final_audio": final_audio})
        return {"final_audio": final_audio, "app_log": log}

    except Exception as e:
        log = log_event(state, "MIXER", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 9: LYRICS ────────────────────────────────────────────────────────────
def node_lyrics(state: PipelineState) -> dict:
    from agents.lyrics import fetch_lyrics

    log = log_event(state, "LYRICS", "Fetching lyrics from Genius")

    try:
        lyrics = fetch_lyrics(state["song"], state["artist"])
        line_count = len(lyrics.get("lines", []))
        language = lyrics.get("language", "en")
        log = log_event(state, "LYRICS", f"Lyrics fetched", {
            "lines": line_count,
            "language": language
        })
        return {"lyrics": lyrics, "app_log": log}

    except Exception as e:
        log = log_event(state, "LYRICS", f"ERROR: {e}")
        return {"lyrics": {"title": state["song"], "artist": state["artist"], "lines": [], "language": "en"}, "app_log": log}


# ── NODE 10: ALIGNER ──────────────────────────────────────────────────────────
def node_aligner(state: PipelineState) -> dict:
    from agents.aligner import align_lyrics

    strategy = state.get("alignment_strategy", "vocal_stem")
    retry = state.get("alignment_retry_count", 0)

    log = log_event(state, "ALIGNER", f"Aligning lyrics (strategy: {strategy}, attempt: {retry + 1})")

    try:
        timed_lyrics = align_lyrics(state["final_audio"], state["lyrics"])
        log = log_event(state, "ALIGNER", "Alignment complete", {"lines": len(timed_lyrics) if timed_lyrics else 0})
        return {"timed_lyrics": timed_lyrics or [], "app_log": log}

    except Exception as e:
        log = log_event(state, "ALIGNER", f"ERROR: {e}")
        return {"timed_lyrics": [], "app_log": log}


# ── NODE 11: ALIGNMENT JUDGE ──────────────────────────────────────────────────
def node_alignment_judge(state: PipelineState) -> dict:
    import librosa

    timed_lyrics = state.get("timed_lyrics", [])
    lyrics = state.get("lyrics", {})
    retry = state.get("alignment_retry_count", 0)

    log = log_event(state, "ALIGNMENT_JUDGE", f"Scoring alignment (attempt {retry + 1})")

    # Score 1 — timestamp order
    order_pass = all(
        timed_lyrics[i]["start"] < timed_lyrics[i+1]["start"]
        for i in range(len(timed_lyrics) - 1)
    ) if len(timed_lyrics) > 1 else True

    # Score 2 — duration check
    try:
        y, sr = librosa.load(state["final_audio"], sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        duration_pass = all(t["end"] <= duration + 1 for t in timed_lyrics) if timed_lyrics else True
    except Exception:
        duration_pass = True

    # Score 3 — whisper confidence
    confidences = [t.get("confidence", -0.5) for t in timed_lyrics if isinstance(t.get("confidence"), float)]
    avg_confidence = sum(confidences) / len(confidences) if confidences else -0.5
    confidence_score = max(0, min(1, (avg_confidence + 1) / 1))

    # Score 4 — line count reasonable
    genius_lines = [l for l in lyrics.get("lines", []) if not (l.startswith("[") and l.endswith("]"))]
    line_ratio = len(timed_lyrics) / len(genius_lines) if genius_lines else 1
    line_score = 1.0 if 0.2 <= line_ratio <= 1.5 else 0.0

    # Final score
    score = (
        (1.0 if order_pass else 0.0) * 0.25 +
        (1.0 if duration_pass else 0.0) * 0.25 +
        confidence_score * 0.25 +
        line_score * 0.25
    )

    score = round(score, 3)

    log = log_event(state, "ALIGNMENT_JUDGE", f"Score: {score}", {
        "order_pass": order_pass,
        "duration_pass": duration_pass,
        "avg_confidence": round(avg_confidence, 3),
        "line_ratio": round(line_ratio, 3),
        "final_score": score
    }, score=score)

    # Determine next strategy if retry needed
    next_strategy = "vocal_stem"
    if retry == 0:
        next_strategy = "medium_model"
    elif retry == 1:
        next_strategy = "full_mix"
    elif retry == 2:
        next_strategy = "even_spacing"

    return {
        "alignment_score": score,
        "alignment_strategy": next_strategy,
        "alignment_retry_count": retry + 1,
        "app_log": log
    }


# ── NODE 12: VIDEO ────────────────────────────────────────────────────────────
def node_video(state: PipelineState) -> dict:
    from agents.video import generate_video

    log = log_event(state, "VIDEO", "Generating video")

    try:
        song_stem = Path(state["audio_path"]).stem
        video_path = generate_video(
            audio_path=state["final_audio"],
            lyrics=state["lyrics"],
            song_name=song_stem
        )
        log = log_event(state, "VIDEO", "Video complete", {"video_path": video_path})
        return {"video_path": video_path, "app_log": log}

    except Exception as e:
        log = log_event(state, "VIDEO", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 13: DESCRIPTION ──────────────────────────────────────────────────────
def node_description(state: PipelineState) -> dict:
    from agents.description_generator import generate_description

    log = log_event(state, "DESCRIPTION", "Generating RAG description")

    try:
        description, tags = generate_description(
            state["song"],
            state["artist"],
            state.get("analysis", {})
        )
        log = log_event(state, "DESCRIPTION", "Description complete")
        return {"app_log": log, "lyrics": {**state.get("lyrics", {}), "description": description, "tags": tags}}

    except Exception as e:
        log = log_event(state, "DESCRIPTION", f"ERROR: {e}")
        return {"app_log": log}


# ── NODE 14: UPLOAD ───────────────────────────────────────────────────────────
def node_upload(state: PipelineState) -> dict:
    from agents.upload import upload_to_youtube

    log = log_event(state, "UPLOAD", "Uploading to YouTube")

    try:
        lyrics = state.get("lyrics", {})
        title = f"{lyrics.get('title', state['song'])} — Restored & Orchestrated"
        description = lyrics.get("description", "AI audio restoration.")
        tags = [t.replace("#", "") for t in lyrics.get("tags", [])]

        project_root = Path(__file__).parent
        secrets_file = str(project_root / "client_secrets.json")

        url = upload_to_youtube(
            video_path=state["video_path"],
            title=title,
            description=description,
            tags=tags,
            privacy="public",
            secrets_file=secrets_file
        )

        log = log_event(state, "UPLOAD", "Upload complete", {"url": url})
        return {"youtube_url": url, "status": "done", "app_log": log}

    except Exception as e:
        log = log_event(state, "UPLOAD", f"ERROR: {e}")
        return {"status": "error", "error_message": str(e), "app_log": log}


# ── NODE 15: NEEDS REVIEW ─────────────────────────────────────────────────────
def node_needs_review(state: PipelineState) -> dict:
    log = log_event(state, "NEEDS_REVIEW",
                    f"Song flagged after {state.get('alignment_retry_count', 0)} retries",
                    {"final_score": state.get("alignment_score")})
    return {"status": "needs_review", "app_log": log}