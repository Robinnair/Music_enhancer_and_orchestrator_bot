import json
import sys
from pathlib import Path
from agents.upload import upload_to_youtube
from agents.description_generator import generate_description

project_root = Path(__file__).parent

if len(sys.argv) < 4:
    print("Usage: python upload_video.py <video_path> <song_name> <artist_name>")
    print("Example: python upload_video.py outputs/final/PIN-EYE_video.mp4 PIN-EYE Jhariah")
    sys.exit(1)

video_path = sys.argv[1]
song_name = sys.argv[2]
artist_name = sys.argv[3]

# Load analysis if available
analysis_path = project_root / "analysis.json"
if analysis_path.exists():
    with open(analysis_path) as f:
        analysis = json.load(f)
    print("Loaded analysis.json")
else:
    analysis = {"tempo_bpm": 120, "average_energy": 0.3}
    print("No analysis.json found — using defaults")

# Generate description
print("Generating description...")
description, tags = generate_description(song_name, artist_name, analysis)
tags_clean = [t.replace("#", "") for t in tags]

title = f"{song_name} by {artist_name} — Restored & Orchestrated"

print(f"\nTitle: {title}")
print(f"\nDescription preview:\n{description[:200]}...")
print(f"\nTags: {tags_clean}")

confirm = input("\nLook good? Upload now? (y/n): ")
if confirm.lower() != "y":
    print("Upload cancelled.")
    sys.exit(0)

secrets_file = str(project_root / "client_secrets.json")

url = upload_to_youtube(
    video_path=video_path,
    title=title,
    description=description,
    tags=tags_clean,
    privacy="public",
    secrets_file=secrets_file
)

print(f"\nDone. YouTube URL: {url}")