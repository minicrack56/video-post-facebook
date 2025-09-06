#!/usr/bin/env python3
import os
import json
from pathlib import Path
from datetime import date
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

CACHE_FILE = "posted_cache.json"

# Folder ID of your Google Drive folder with videos
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

# Load Drive API credentials from service account
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Load service account credentials from env var (GitHub secret)
service_account_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)


def load_cache():
    """Load cache file, or initialize if missing/broken."""
    if Path(CACHE_FILE).exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"last_index": -1, "last_date": ""}


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
    today = str(date.today())

    # Prevent reposting the same day
    if cache.get("last_date") == today:
        raise RuntimeError("⚠️ Already posted a video today, skipping.")

    last_index = cache.get("last_index", -1)
    videos = fetch_videos_from_drive()
    if not videos:
        raise RuntimeError("⚠️ No videos found in Drive folder!")

    next_index = (last_index + 1) % len(videos)
    video = videos[next_index]

    # Save new state
    cache["last_index"] = next_index
    cache["last_date"] = today
    save_cache(cache)

    return video


def main():
    try:
        video = get_next_video()
    except RuntimeError as e:
        print(str(e))
        return

    # === Replace with your posting logic ===
    print(f"[DEBUG] Selected video: {video['name']} ({video['id']})")
    # Example: download_and_post(video['id'])
    # =======================================


if __name__ == "__main__":
    main()
