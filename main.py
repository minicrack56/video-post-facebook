#!/usr/bin/env python3
import os
import json
import base64
from pathlib import Path
import requests
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# -----------------------------
# Configuration via environment
# -----------------------------
CACHE_FILE = "posted_cache.json"
GOOGLE_SERVICE_ACCOUNT_JSON_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

# Google Drive API scopes
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Caption for all posts
CAPTION = (
    "Don't forget to subscribe for more!\n\n"
    "#movie #movieclips #movienetflix #fyp #fypシ゚viralシ #viral #facebookvideo"
)

# -----------------------------
# Google Drive authentication
# -----------------------------
if not GOOGLE_SERVICE_ACCOUNT_JSON_B64:
    raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set!")

GOOGLE_SERVICE_ACCOUNT_JSON = base64.b64decode(GOOGLE_SERVICE_ACCOUNT_JSON_B64)
creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)

# -----------------------------
# Cache helpers
# -----------------------------
def load_cache():
    if Path(CACHE_FILE).exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"posted_ids": []}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

# -----------------------------
# Google Drive helpers
# -----------------------------
def fetch_videos_from_drive():
    service = build("drive", "v3", credentials=creds)
    query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed=false"
    results = (
        service.files()
        .list(q=query, orderBy="createdTime asc", fields="files(id, name)")
        .execute()
    )
    return results.get("files", [])

def get_next_video():
    cache = load_cache()
    posted_ids = set(cache.get("posted_ids", []))
    videos = fetch_videos_from_drive()
    if not videos:
        raise RuntimeError("⚠️ No videos found in Drive folder!")

    # Pick first unposted video
    for video in videos:
        if video["id"] not in posted_ids:
            posted_ids.add(video["id"])
            cache["posted_ids"] = list(posted_ids)
            save_cache(cache)
            return video

    # All videos posted, reset
    cache["posted_ids"] = []
    save_cache(cache)
    return videos[0]

# -----------------------------
# Facebook helpers
# -----------------------------
def post_video_to_facebook(video_id, video_name):
    """Post video to Facebook page via Drive file URL."""
    video_url = f"https://drive.google.com/uc?id={video_id}&export=download"
    url = f"https://graph.facebook.com/v16.0/{FACEBOOK_PAGE_ID}/videos"
    data = {
        "url": video_url,
        "caption": CAPTION,
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        "published": True
    }
    response = requests.post(url, data=data)
    if response.status_code != 200:
        raise RuntimeError(f"Facebook API error: {response.text}")
    print(f"✅ Posted '{video_name}' to Facebook.")

# -----------------------------
# Main script
# -----------------------------
def main():
    video = get_next_video()
    print(f"[DEBUG] Selected video: {video['name']} ({video['id']})")
    post_video_to_facebook(video["id"], video["name"])

if __name__ == "__main__":
    main()
