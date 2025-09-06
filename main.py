#!/usr/bin/env python3
import os
import json
import base64
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import requests

# === Configuration from GitHub Secrets ===
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")  # Base64 encoded

# === Constants ===
CACHE_FILE = "posted_cache.json"
CAPTION = "Don't forget to subscribe for more!\n\n#movie #movieclips #movienetflix #fyp #fypシ゚viralシ #viral #facebookvideo"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# === Load service account credentials ===
decoded_json = base64.b64decode(GOOGLE_SERVICE_ACCOUNT_JSON).decode("utf-8")
service_account_info = json.loads(decoded_json)
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

# === Cache handling ===
def load_cache():
    if Path(CACHE_FILE).exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"last_index": -1}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

# === Google Drive API ===
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
    last_index = cache.get("last_index", -1)

    videos = fetch_videos_from_drive()
    if not videos:
        raise RuntimeError("⚠️ No videos found in Drive folder!")

    # Loop from oldest to newest, then restart
    next_index = (last_index + 1) % len(videos)
    video = videos[next_index]

    cache["last_index"] = next_index
    save_cache(cache)

    return video

# === Facebook upload ===
def post_video_to_facebook(video_id, video_name):
    """Post video using upload URL"""
    url = f"https://graph.facebook.com/v17.0/{FACEBOOK_PAGE_ID}/videos"
    data = {
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        "description": CAPTION,
        "published": "true"  # Ensure it publishes immediately
    }
    files = {
        "file": requests.get(f"https://drive.google.com/uc?id={video_id}&export=download", stream=True).raw
    }

    response = requests.post(url, data=data, files=files)
    if response.status_code != 200:
        raise RuntimeError(f"Facebook upload failed: {response.text}")
    print(f"[SUCCESS] Posted video: {video_name}")

def main():
    video = get_next_video()
    print(f"[DEBUG] Selected video: {video['name']} ({video['id']})")
    post_video_to_facebook(video['id'], video['name'])

if __name__ == "__main__":
    main()
