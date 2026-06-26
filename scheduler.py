import sys
import shutil
import json
from pathlib import Path
from datetime import datetime
import random
import time


def read_queue(queue_path: Path) -> list:
    lines = []
    with open(queue_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("|")
                if len(parts) >= 3:
                    lines.append({
                        "song": parts[0].strip(),
                        "artist": parts[1].strip(),
                        "status": parts[2].strip()
                    })
    return lines


def write_queue(queue_path: Path, entries: list):
    with open(queue_path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(f"{e['song']}|{e['artist']}|{e['status']}\n")


def get_next_pending(entries: list) -> dict:
    for e in entries:
        if e["status"] == "pending":
            return e
    return None


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    log_path = Path(__file__).parent / "scheduler.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def run():
    project_root = Path(__file__).parent
    queue_path = project_root / "songs_queue.txt"

    if not queue_path.exists():
        log("songs_queue.txt not found. Exiting.")
        sys.exit(1)

    # # Random skip — roughly 1 in 7 days
    # if random.randint(1, 7) == 1:
    #     log("Randomly skipping today to avoid bot detection patterns.")
    #     sys.exit(0)

    # # Random delay — 0 to 3 hours
    # delay_minutes = random.randint(0, 180)
    # log(f"Starting in {delay_minutes} minutes to randomise upload time...")
    # time.sleep(delay_minutes * 60)

    entries = read_queue(queue_path)
    entry = get_next_pending(entries)

    if not entry:
        log("No pending songs in queue. Nothing to do.")
        sys.exit(0)

    song = entry["song"]
    artist = entry["artist"]
    log(f"Processing: {song} by {artist}")

    for folder in [
        project_root / "outputs" / "restored",
        project_root / "outputs" / "stereo",
        project_root / "outputs" / "final",
        project_root / "outputs" / "htdemucs",
    ]:
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)

    try:
        log("Step 1: Downloading audio...")
        from agents.downloader import download_and_convert
        audio_path = download_and_convert(song, artist)
        log(f"Audio ready: {audio_path}")

        song_name = Path(audio_path).stem

        log("Step 2: Analysing audio...")
        from agents.analyser import analyze_audio
        analysis = analyze_audio(audio_path)

        log("Step 3: Orchestrating...")
        from agents.orchestrator import orchestrate
        orchestrate(analysis["instruments_detected"])

        log("Step 4: Separating stems...")
        from agents.separator import separate_audio
        separate_audio(audio_path)

        log("Step 5: Restoring stems...")
        stems_path = project_root / "outputs" / "htdemucs" / song_name
        from agents.restoration import process_all_stems
        process_all_stems(stems_path)

        log("Step 6: Converting to stereo...")
        from agents.stereo import process_all_files
        process_all_files()

        log("Step 7: Mixing...")
        from agents.mixer import mix_tracks
        mix_tracks(song_name, analysis)

        final_folder = project_root / "outputs" / "final"
        final_files = list(final_folder.glob(f"{song_name}*.wav"))
        if not final_files:
            raise FileNotFoundError("Final mix not found")
        final_audio = str(sorted(final_files)[-1])
        log(f"Final mix: {final_audio}")

        log("Step 8: Fetching lyrics...")
        from agents.lyrics import fetch_lyrics
        lyrics = fetch_lyrics(song, artist)

        log("Step 9: Aligning lyrics...")
        from agents.aligner import align_lyrics
        align_lyrics(final_audio, lyrics)

        log("Step 10: Generating video...")
        from agents.video import generate_video
        video_path = generate_video(
            audio_path=final_audio,
            lyrics=lyrics,
            song_name=song_name
        )
        log(f"Video: {video_path}")

        log("Step 11: Generating description...")
        from agents.description_generator import generate_description
        description, tags = generate_description(song, artist, analysis)
        tags_clean = [t.replace("#", "") for t in tags]

        log("Step 12: Uploading to YouTube...")
        from agents.upload import upload_to_youtube
        title = f"{lyrics.get('title', song)} — Restored & Orchestrated"
        secrets_file = str(project_root / "client_secrets.json")

        url = upload_to_youtube(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags_clean,
            privacy="public",
            secrets_file=secrets_file
        )

        for e in entries:
            if e["song"] == song and e["artist"] == artist:
                e["status"] = f"done|{datetime.now().strftime('%Y-%m-%d')}|{url}"
        write_queue(queue_path, entries)

        log(f"Done: {song} by {artist}")
        log(f"YouTube URL: {url}")

    except Exception as e:
        log(f"ERROR processing {song} by {artist}: {e}")
        import traceback
        log(traceback.format_exc())

        for e_entry in entries:
            if e_entry["song"] == song and e_entry["artist"] == artist:
                e_entry["status"] = "error"
        write_queue(queue_path, entries)
        sys.exit(1)


if __name__ == "__main__":
    run()