from langgraph.graph import StateGraph, END
from pipeline_state import PipelineState
from pipeline_nodes import (
    node_downloader,
    node_analyser,
    node_genre_classifier,
    node_orchestrator,
    node_separator,
    node_restoration,
    node_stereo,
    node_mixer,
    node_lyrics,
    node_aligner,
    node_alignment_judge,
    node_video,
    node_description,
    node_upload,
    node_needs_review
)


# ── CONDITIONAL EDGE FUNCTIONS ────────────────────────────────────────────────

def route_after_downloader(state: PipelineState) -> str:
    if state.get("status") == "error":
        return "end"
    return "analyser"


def route_after_lyrics(state: PipelineState) -> str:
    genre = state.get("genre", "indie_alternative")
    lines = state.get("lyrics", {}).get("lines", [])

    # Skip alignment for instrumentals or empty lyrics
    if genre in ["video_game_instrumental", "electronic"] or not lines:
        return "video"
    return "aligner"


def route_after_judge(state: PipelineState) -> str:
    score = state.get("alignment_score", 0)
    retry = state.get("alignment_retry_count", 0)

    if score >= 0.75:
        return "video"
    elif retry < 3:
        return "aligner"
    else:
        return "needs_review"


def route_after_error(state: PipelineState) -> str:
    if state.get("status") == "error":
        return "end"
    return "continue"


# ── BUILD GRAPH ───────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    # Add all nodes
    graph.add_node("downloader", node_downloader)
    graph.add_node("analyser", node_analyser)
    graph.add_node("genre_classifier", node_genre_classifier)
    graph.add_node("orchestrator", node_orchestrator)
    graph.add_node("separator", node_separator)
    graph.add_node("restoration", node_restoration)
    graph.add_node("stereo", node_stereo)
    graph.add_node("mixer", node_mixer)
    graph.add_node("lyrics", node_lyrics)
    graph.add_node("aligner", node_aligner)
    graph.add_node("alignment_judge", node_alignment_judge)
    graph.add_node("video", node_video)
    graph.add_node("description", node_description)
    graph.add_node("upload", node_upload)
    graph.add_node("needs_review", node_needs_review)

    # Entry point
    graph.set_entry_point("downloader")

    # Linear edges
    graph.add_conditional_edges(
        "downloader",
        route_after_downloader,
        {"analyser": "analyser", "end": END}
    )
    graph.add_edge("analyser", "genre_classifier")
    graph.add_edge("genre_classifier", "orchestrator")
    graph.add_edge("orchestrator", "separator")
    graph.add_edge("separator", "restoration")
    graph.add_edge("restoration", "stereo")
    graph.add_edge("stereo", "mixer")

    def route_after_mixer(state: PipelineState) -> str:
        genre = state.get("genre", "indie_alternative")
        if genre in ["video_game_instrumental", "electronic"]:
            return "video"
        return "lyrics"

    graph.add_conditional_edges(
        "mixer",
        route_after_mixer,
        {"lyrics": "lyrics", "video": "video"}
    )

    # Conditional after lyrics — skip aligner for instrumentals
    graph.add_conditional_edges(
        "lyrics",
        route_after_lyrics,
        {"aligner": "aligner", "video": "video"}
    )

    # Aligner always goes to judge
    graph.add_edge("aligner", "alignment_judge")

    # Conditional after judge — retry loop or proceed
    graph.add_conditional_edges(
        "alignment_judge",
        route_after_judge,
        {
            "video": "video",
            "aligner": "aligner",
            "needs_review": "needs_review"
        }
    )

    # Linear to end
    graph.add_edge("video", "description")
    graph.add_edge("description", "upload")
    graph.add_edge("upload", END)
    graph.add_edge("needs_review", END)

    return graph.compile()


# Export compiled pipeline
pipeline = build_pipeline()