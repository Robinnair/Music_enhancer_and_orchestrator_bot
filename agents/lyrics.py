import lyricsgenius
import json
import unicodedata
from pathlib import Path
from langchain_ollama import OllamaLLM

GENIUS_TOKEN = "y-ReuJT3vZL5FAoVA1nverhB6-L1OqYB-P8nzUJhpHHtCjHnIxol2bnz7dW35RTc"

llm = OllamaLLM(model="llama3.2")


def is_japanese(text: str) -> bool:
    for char in text:
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            return True
    return False


def is_korean(text: str) -> bool:
    for char in text:
        if '\uAC00' <= char <= '\uD7A3':
            return True
    return False


def needs_translation(lines: list) -> bool:
    sample = " ".join(lines[:8])
    return is_japanese(sample) or is_korean(sample)


def translate_lyrics_batch(lines: list) -> list:
    print("Translating lyrics to English...")

    translatable = []
    indices = []
    result_lines = list(lines)

    for i, line in enumerate(lines):
        if line.strip() and not line.startswith("["):
            translatable.append(line)
            indices.append(i)

    if not translatable:
        return lines

    numbered = "\n".join([f"{i+1}. {line}" for i, line in enumerate(translatable)])

    prompt = f"""Translate these song lyrics to English.
Return ONLY a numbered list in the exact same format.
Keep translations poetic and natural sounding.
One translation per number. Do not add explanations.

{numbered}

English translations:"""

    try:
        response = llm.invoke(prompt).strip()
        translated = []

        for line in response.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line[0].isdigit() and ". " in line:
                translated.append(line.split(". ", 1)[1].strip())
            elif line[0].isdigit() and "." in line:
                translated.append(line.split(".", 1)[1].strip())
            else:
                translated.append(line)

        if len(translated) == len(indices):
            for i, idx in enumerate(indices):
                result_lines[idx] = translated[i]
            print(f"Translated {len(translated)} lines successfully.")
        else:
            print(f"Translation count mismatch ({len(translated)} vs {len(indices)}). Using partial translation.")
            for i, idx in enumerate(indices[:len(translated)]):
                result_lines[idx] = translated[i]

    except Exception as e:
        print(f"Translation failed: {e}. Keeping original lyrics.")

    return result_lines


def fetch_lyrics(song_name: str, artist_name: str = None, translate: bool = True) -> dict:
    print("=" * 50)
    print("LYRICS AGENT")
    print("=" * 50)

    genius = lyricsgenius.Genius(
        GENIUS_TOKEN,
        skip_non_songs=True,
        excluded_terms=["(Remix)", "(Live)"],
        remove_section_headers=False,
        timeout=15,
        retries=3
    )

    try:
        if artist_name:
            print(f"Searching: {song_name} by {artist_name}")
            song = genius.search_song(song_name, artist_name)
            if not song:
                print("Retrying without artist name...")
                song = genius.search_song(song_name)
        else:
            print(f"Searching: {song_name}")
            song = genius.search_song(song_name)

        if not song:
            print("Not found on Genius. Using placeholder.")
            return _placeholder(song_name, artist_name)

        lines = [l.strip() for l in song.lyrics.split("\n") if l.strip()]

        if lines and "lyrics" in lines[0].lower():
            lines = lines[1:]
        if lines and "embed" in lines[-1].lower():
            lines = lines[:-1]

        # Detect if translation is needed
        translated = False
        original_lines = lines.copy()

        if translate and needs_translation(lines):
            print("Non-English lyrics detected.")
            lines = translate_lyrics_batch(lines)
            translated = True
            print("Translation complete.")
        else:
            print("English lyrics detected — no translation needed.")

        result = {
            "title": song.title,
            "artist": song.artist if song.artist else (artist_name or "Unknown"),
            "lines": lines,
            "translated": translated,
            "original_lines": original_lines if translated else []
        }

        out = Path(__file__).parent.parent / "outputs" / "lyrics.json"
        out.parent.mkdir(exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Found {len(lines)} lines.")
        print(f"Translated: {translated}")
        print(f"Saved to: {out}")
        return result

    except Exception as e:
        print(f"Error: {e}")
        return _placeholder(song_name, artist_name)


def _placeholder(song_name: str, artist_name: str = None) -> dict:
    return {
        "title": song_name,
        "artist": artist_name if artist_name else "Unknown",
        "lines": [song_name, "Lyrics not found", "Add manually to outputs/lyrics.json"],
        "translated": False,
        "original_lines": []
    }


if __name__ == "__main__":
    result = fetch_lyrics("Gurenge", "LiSA")
    print(f"\nTitle: {result['title']}")
    print(f"Artist: {result['artist']}")
    print(f"Translated: {result['translated']}")
    print("\nFirst 10 lines:")
    for line in result["lines"][:10]:
        print(line)