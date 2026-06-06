import subprocess
import sys
from pathlib import Path


def separate_audio(audio_file):

    project_root = Path(__file__).parent.parent
    output_folder = project_root / "outputs"

    print("\n===== SEPARATOR AGENT =====")
    print(f"Input: {audio_file}")

    command = [
        "demucs",
        "--mp3",
        "-o",
        str(output_folder),
        str(audio_file)
    ]

    subprocess.run(command, check=True)

    print("\nSeparation Complete")

    stems_folder = output_folder / "htdemucs" / Path(audio_file).stem

    print(f"\nStems saved in: {stems_folder}")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("python separator.py <audio_file>")
        exit()

    separate_audio(sys.argv[1])
