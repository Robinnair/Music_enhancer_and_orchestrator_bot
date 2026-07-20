from typing import TypedDict,Optional,List

class PipelineState(TypedDict):
    #song identity
    song: str
    artist: str
    window_mode: str
    genre: str

    #File paths
    audio_path: str
    stems_path: str
    final_audio: str
    video_path: str

    #Agent outputs
    analysis: dict
    lyrics: dict
    timed_lyrics: list

    #Scoring and retries
    alignment_score: float
    alignment_retry_count: int
    alignment_strategy: str

    #Upload result
    youtube_url: str

    #Status
    status:str
    error_message: str

    amp_log: list
