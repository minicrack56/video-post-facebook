#!/usr/bin/env python3
import os
import json
import time
import requests
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import base64

# --- Environment Variables ---
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_SERVICE_ACCOUNT_JSON_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

CACHE_FILE = "posted_cache.json"
CAPTION = ("Don't forget to subscribe for more!\n\n"
           "#movie #movieclips #movienetflix #fyp #fypシ゚viralシ #viral #facebookvideo")

# --- Load Google Service Account Credentials ---
if not GOOGLE_SERVICE_ACCOUNT_JSON_B64:
    raise RuntimeError("Missing GOOGLE_SERVICE_ACCOUNT_JSON env variable")
GOOGLE_SERVICE_ACCOUNT_JSON = base64.b64decode(GOOGLE_SERVICE_ACCOUNT_JSON_B64)
creds = Credentials.from_service_account_info(json.loads(GOOGLE_SERVICE_ACCOUNT_JSON), scopes=["https://www.googleapis.com/auth/drive.readonly"])

# --- Load / Save Cache ---
def load_cache():
    if Path(CACHE_FILE).exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"last_index": -1, "posted_ids": []}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

# --- Fetch Videos from Google Drive ---
def fetch_videos_from_drive():
    service = build("drive", "v3", credentials=creds)
    query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed=false"
    results = service.files().list(q=query, orderBy="createdTime asc", fields="files(id, name)").execute()
    return results.get("files", [])

# --- Get Next Video to Post ---
def get_next_video():
    cache = load_cache()
    last_index = cache.get("last_index", -1)
    posted_ids = cache.get("posted_ids", [])

    videos = fetch_videos_from_drive()
    if not videos:
        raise RuntimeError("⚠️ No videos found in Drive folder!")

    # Find next video index not posted yet, loop if all posted
    total_videos = len(videos)
    for i in range(1, total_videos + 1):
        next_index = (last_index + i) % total_videos
        if videos[next_index]["id"] not in posted_ids:
            video = videos[next_index]
            cache["last_index"] = next_index
            posted_ids.append(video["id"])
            # Keep only last 'total_videos' IDs
            if len(posted_ids) > total_videos:
                posted_ids = posted_ids[-total_videos:]
            cache["posted_ids"] = posted_ids
            save_cache(cache)
            return video

    # All videos posted, reset loop
    cache["posted_ids"] = []
    cache["last_index"] = -1
    save_cache(cache)
    return get_next_video()

# --- Post Video to Facebook ---
def post_video_to_facebook(video_id, video_name):
    # Use the public download URL format
    video_url = f"https://drive.google.com/uc?export=download&id={video_id}"

    data = {
        "file_url": video_url,
        "caption": CAPTION,
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        "published": True
    }

    # Retry logic
    for attempt in range(3):
        response = requests.post(f"https://graph.facebook.com/v16.0/{FACEBOOK_PAGE_ID}/videos", data=data)
        if response.status_code == 200:
            print(f"✅ Posted video '{video_name}' successfully")
            return
        else:
            print(f"[WARN] Attempt {attempt+1} failed: {response.text}")
            time.sleep(5)
    raise RuntimeError(f"Failed to post video '{video_name}' after 3 attempts")

# --- Main Execution ---
def main():
    video = get_next_video()
    print(f"[DEBUG] Selected video: {video['name']} ({video['id']})")
    post_video_to_facebook(video["id"], video["name"])

if __name__ == "__main__":
    main()
