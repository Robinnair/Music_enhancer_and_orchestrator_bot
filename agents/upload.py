import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"


def get_authenticated_service(secrets_file: str):
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(
    video_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    category_id: str = "10",
    privacy: str = "private",
    secrets_file: str = "client_secrets.json"
) -> str:
    print("=" * 50)
    print("YOUTUBE UPLOAD AGENT")
    print("=" * 50)

    if not os.path.exists(secrets_file):
        print(f"client_secrets.json not found. Skipping upload.")
        return ""

    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return ""

    print("Authenticating with YouTube...")
    youtube = get_authenticated_service(secrets_file)

    if tags is None:
        tags = ["music", "restored", "AI"]

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5
    )

    print(f"Uploading: {title}")
    print(f"Privacy: {privacy}")

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  Upload progress: {pct}%")

    video_id = response.get("id", "")
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"\nUpload complete.")
    print(f"Video URL: {url}")
    return url


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python upload.py <video_path> <title>")
    else:
        upload_to_youtube(sys.argv[1], sys.argv[2])