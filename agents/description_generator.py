import wikipediaapi
import json
from pathlib import Path
from langchain_ollama import OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

llm = OllamaLLM(model="llama3.2")
embeddings = OllamaEmbeddings(model="nomic-embed-text")


def fetch_wikipedia_info(song_name: str, artist_name: str) -> list:
    wiki = wikipediaapi.Wikipedia(
        language="en",
        user_agent="MusicUploaderBot/1.0"
    )

    documents = []

    song_page = wiki.page(f"{song_name} {artist_name} song")
    if song_page.exists():
        documents.append(Document(
            page_content=song_page.text[:3000],
            metadata={"type": "song"}
        ))
        print(f"Found song page: {song_page.title}")

    artist_page = wiki.page(artist_name)
    if artist_page.exists():
        documents.append(Document(
            page_content=artist_page.text[:2000],
            metadata={"type": "artist"}
        ))
        print(f"Found artist page: {artist_page.title}")

    return documents


def fetch_pop_culture_references(song_name: str, artist_name: str) -> str:
    print("Searching for pop culture references...")
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(f'"{song_name}" "{artist_name}" TV show movie 2024 2025 2026', max_results=3):
                results.append(r.get("body", ""))
            for r in ddgs.text(f'"{song_name}" {artist_name} TikTok viral trend 2025 2026', max_results=3):
                results.append(r.get("body", ""))
        combined = " ".join(results)[:2000]
        print(f"Found {len(results)} references")
        return combined
    except Exception as e:
        print(f"Pop culture search skipped: {e}")
        return ""


def extract_hashtags(song_name: str, artist_name: str, references: str) -> list:
    if not references:
        return []
    prompt = f"""Based on this text about "{song_name}" by {artist_name}, list any TV shows, movies, or viral TikTok trends mentioned.

TEXT: {references}

Return only a Python list like: ["Stranger Things", "Wednesday"]
If nothing found return: []"""
    try:
        response = llm.invoke(prompt).strip()
        if response.startswith("["):
            items = json.loads(response)
            return [f"#{item.strip().replace(' ', '').replace('-', '')}" for item in items if item.strip()]
    except Exception:
        pass
    return []


def generate_description(song_name: str, artist_name: str, analysis: dict) -> tuple:
    print("=" * 50)
    print("DESCRIPTION GENERATOR AGENT")
    print("=" * 50)

    documents = fetch_wikipedia_info(song_name, artist_name)
    references = fetch_pop_culture_references(song_name, artist_name)
    pop_hashtags = extract_hashtags(song_name, artist_name, references)

    if pop_hashtags:
        print(f"Pop culture hashtags: {pop_hashtags}")

    base_tags = [
        "#Shorts", "#AIMusic", "#AudioRestoration", "#music",
        f"#{artist_name.replace(' ', '')}",
        f"#{song_name.replace(' ', '')}",
        "#restored", "#orchestrated", "#lyrics"
    ]
    all_tags = base_tags + pop_hashtags

    if not documents:
        print("No Wikipedia data. Using basic description.")
        desc = (
            f"{song_name} by {artist_name} — restored and orchestrated using AI.\n\n"
            f"Processed through a multi-agent audio pipeline: source separation via Demucs, "
            f"frequency super-resolution, orchestral EQ mapping, and analysis-driven mixing.\n\n"
            f"Original rights belong to {artist_name}. Educational purposes only.\n\n"
            f"{' '.join(all_tags)}"
        )
        return desc, all_tags

    vectorstore = FAISS.from_documents(documents, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    relevant_docs = retriever.invoke(f"{song_name} {artist_name} meaning chart history")
    context = "\n\n".join([d.page_content for d in relevant_docs])

    tempo = analysis.get("tempo_bpm", "unknown")
    energy = analysis.get("average_energy", 0)
    energy_desc = "quiet and intimate" if energy < 0.2 else "powerful and energetic" if energy > 0.5 else "balanced"

    pop_context = f"\nRECENT POP CULTURE USAGE:\n{references[:500]}" if references else ""

    prompt = f"""You are writing a YouTube Shorts description for an AI audio restoration and enhancement video.

SONG INFO FROM WIKIPEDIA:
{context}
{pop_context}

AUDIO ANALYSIS:
- Song: {song_name} by {artist_name}
- Tempo: {tempo} BPM
- Energy level: {energy_desc}

Write a YouTube description that:
1. start with some general introduction about the artist
2. explain why this song stands out in the artists catalogue
3. Briefly explains what AI audio restoration pipeline did to this song(which was spliting the song into its audio stems cleaning each stem and then combining the stems back to gather to recreate the original but augmenting the volcal, base and drums by a set margin based on factors such as the average enrgy or brightness of the song,etc) did to this specific song
4. Naturally mentions if it was recently in a TV show or movie
5. Ends with: Drop a comment if you felt that

Under 200 words. Write like a human music fan, not a robot.
No bullet points. Flowing paragraphs only.
Do not start with I or This video.
Do not include hashtags in the body."""

    description = llm.invoke(prompt).strip()
    full_description = description + "\n\n" + " ".join(all_tags)

    print(f"Preview: {description[:150]}...")
    print(f"Tags: {all_tags}")

    return full_description, all_tags


if __name__ == "__main__":
    test_analysis = {"tempo_bpm": 137.2, "average_energy": 0.258}
    desc, tags = generate_description("Megalovania", "Toby Fox", test_analysis)
    print("\nFULL DESCRIPTION:")
    print(desc)