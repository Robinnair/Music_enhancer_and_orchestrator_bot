import sys
import shutil
from pathlib import Path
from datetime import datetime
from pipeline_graph import pipeline


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
                        "status": parts[2].strip(),
                        "window_mode": parts[3].strip() if len(parts) > 3 else "peak"
                    })
    return lines


def write_queue(queue_path: Path, entries: list):
    with open(queue_path, "w", encoding="utf-8") as f:
        for e in entries:
            window = e.get("window_mode", "peak")
            status = e["status"]
            f.write(f"{e['song']}|{e['artist']}|{status}|{window}\n")


def get_next_pending(entries: list) -> dict:
    for e in entries:
        if e["status"] == "pending":
            return e
    return None


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open("app.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def clean_output_folders(project_root: Path):
    for folder in [
        project_root / "outputs" / "restored",
        project_root / "outputs" / "stereo",
        project_root / "outputs" / "final",
        project_root / "outputs" / "htdemucs",
    ]:
        if folder.exists():
            try:
                shutil.rmtree(folder)
            except PermissionError:
                for f in folder.glob("**/*"):
                    try:
                        if f.is_file():
                            f.unlink()
                    except Exception:
                        pass
        folder.mkdir(parents=True, exist_ok=True)


def run():
    project_root = Path(__file__).parent
    queue_path = project_root / "songs_queue.txt"

    if not queue_path.exists():
        log("songs_queue.txt not found. Exiting.")
        sys.exit(1)

    entries = read_queue(queue_path)
    entry = get_next_pending(entries)

    if not entry:
        log("No pending songs in queue. Nothing to do.")
        sys.exit(0)

    song = entry["song"]
    artist = entry["artist"]
    window_mode = entry.get("window_mode", "peak")

    log(f"Starting LangGraph pipeline: {song} by {artist} (window: {window_mode})")

    clean_output_folders(project_root)

    # Initial state
    initial_state = {
        "song": song,
        "artist": artist,
        "window_mode": window_mode,
        "genre": "",
        "audio_path": "",
        "stems_path": "",
        "final_audio": "",
        "video_path": "",
        "analysis": {},
        "lyrics": {},
        "timed_lyrics": [],
        "alignment_score": 0.0,
        "alignment_retry_count": 0,
        "alignment_strategy": "vocal_stem",
        "youtube_url": "",
        "status": "running",
        "error_message": "",
        "app_log": []
    }

    # Run the graph
    try:
        final_state = pipeline.invoke(initial_state)
    except Exception as e:
        log(f"Pipeline crashed: {e}")
        import traceback
        log(traceback.format_exc())
        final_state = {"status": "error", "error_message": str(e)}

    # Update queue based on final status
    status = final_state.get("status", "error")
    url = final_state.get("youtube_url", "")
    date = datetime.now().strftime("%Y-%m-%d")

    for e in entries:
        if e["song"] == song and e["artist"] == artist:
            if status == "done":
                e["status"] = f"done|{date}|{url}"
            elif status == "needs_review":
                e["status"] = "needs_review"
            else:
                e["status"] = "error"

    write_queue(queue_path, entries)
    log(f"Pipeline finished with status: {status}")

    if status == "done":
        log(f"YouTube URL: {url}")
    elif status == "needs_review":
        log(f"Song flagged for manual review — check app.log for details")


if __name__ == "__main__":
    run()