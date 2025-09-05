#!/usr/bin/env python3
import os
import json
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

CACHE_FILE = "posted_cache.json"
# Folder ID of your Google Drive folder with videos
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

# Load Drive API credentials from service account
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)

def load_cache():
    """Load cache file, or initialize if missing/broken."""
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

def fetch_videos_from_drive():
    """Fetch all video files in folder, oldest to newest."""
    service = build("drive", "v3", credentials=creds)
    query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed=false"
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

    next_index = (last_index + 1) % len(videos)
    video = videos[next_index]

    cache["last_index"] = next_index
    save_cache(cache)

    return video

def main():
    video = get_next_video()

    # === Replace with your posting logic ===
    print(f"[DEBUG] Selected video: {video['name']} ({video['id']})")
    # Example: download_and_post(video['id'])
    # =======================================

if __name__ == "__main__":
    main()
