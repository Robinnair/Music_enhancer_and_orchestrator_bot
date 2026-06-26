import stable_whisper
import json
from pathlib import Path


def align_lyrics(audio_path: str, lyrics: dict) -> list:
    print("=" * 50)
    print("ALIGNMENT AGENT")
    print("=" * 50)

    lines = lyrics.get("lines", [])

    placeholder_indicators = [
        "lyrics not found",
        "add manually",
        "instrumental"
    ]

    is_instrumental = (
        not lines or
        (len(lines) <= 3 and any(
            indicator in " ".join(lines).lower()
            for indicator in placeholder_indicators
        ))
    )

    if is_instrumental:
        print("Instrumental track detected — skipping lyric alignment.")
        project_root = Path(__file__).parent.parent
        out = project_root / "outputs" / "timed_lyrics.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

    print("Loading Whisper model...")
    model = stable_whisper.load_model("small")

    print("Transcribing audio to find what is actually sung...")
    transcription = model.transcribe(audio_path, language="en")

    transcribed_lines = []
    for segment in transcription.segments:
        text = segment.text.strip()
        if text:
            transcribed_lines.append({
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": text
            })

    if not transcribed_lines:
        print("No speech detected. Treating as instrumental.")
        project_root = Path(__file__).parent.parent
        out = project_root / "outputs" / "timed_lyrics.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

    print(f"Transcribed {len(transcribed_lines)} segments from audio.")

    if not lines:
        result = transcribed_lines
    else:
        result = match_to_lyrics(transcribed_lines, lines)

    project_root = Path(__file__).parent.parent
    out = project_root / "outputs" / "timed_lyrics.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Aligned {len(result)} lines.")
    print(f"Saved to: {out}")
    for t in result[:8]:
        print(f"  {t['start']}s — {t['text']}")

    return result


def match_to_lyrics(transcribed: list, full_lyrics: list) -> list:
    from difflib import SequenceMatcher

    result = []

    for segment in transcribed:
        transcribed_text = segment["text"].lower().strip()
        best_match = None
        best_ratio = 0

        for lyric_line in full_lyrics:
            lyric_lower = lyric_line.lower().strip()
            if not lyric_lower:
                continue
            ratio = SequenceMatcher(None, transcribed_text, lyric_lower).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = lyric_line

        if best_match and best_ratio > 0.4:
            result.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": best_match
            })
        else:
            result.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip()
            })

    return result


def _even_spacing(lines: list, audio_path: str) -> list:
    import librosa
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    if not lines:
        return []
    time_per_line = duration / len(lines)
    return [
        {
            "start": i * time_per_line,
            "end": (i + 1) * time_per_line,
            "text": line
        }
        for i, line in enumerate(lines)
    ]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python aligner.py <audio_path>")
        exit()

    project_root = Path(__file__).parent.parent
    lyrics_path = project_root / "outputs" / "lyrics.json"

    with open(lyrics_path, encoding="utf-8") as f:
        lyrics = json.load(f)

    align_lyrics(sys.argv[1], lyrics)