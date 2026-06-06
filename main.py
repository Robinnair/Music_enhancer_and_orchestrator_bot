import sys
import shutil
from pathlib import Path
from agents.analyser import analyze_audio
from agents.separator import separate_audio
from agents.restoration import process_all_stems
from agents.stereo import process_all_files
from agents.orchestrator import orchestrate
from agents.mixer import mix_tracks

if len(sys.argv) < 2:
    print("Usage:")
    print("python main.py <audio_file>")
    exit()

audio_file = sys.argv[1]
song_name = Path(audio_file).stem

project_root = Path(__file__).parent

for folder in [
    project_root / "outputs" / "restored",
    project_root / "outputs" / "stereo",
    project_root / "outputs" / "final",
    project_root / "outputs" / "htdemucs",
]:
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

stems_path = project_root / "outputs" / "htdemucs" / song_name

analysis = analyze_audio(audio_file)
separate_audio(audio_file)
orchestrate(analysis["instruments_detected"], stems_path)
process_all_stems(stems_path)
process_all_files()
mix_tracks(song_name, analysis)

print("\nPipeline Complete")
