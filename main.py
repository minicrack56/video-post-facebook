#!/usr/bin/env python3
import os
import json
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import requests

# --- Configuration ---
CACHE_FILE = "posted_cache.json"
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# Caption for Facebook videos
VIDEO_CAPTION = (
    "Don't forget to subscribe for more!\n\n"
    "#movie #movieclips #movienetflix #fyp #fypシ゚viralシ #viral #facebookvideo"
)

# --- Google Drive API setup ---
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
creds = Credentials.from_service_account_info(json.loads(GOOGLE_SERVICE_ACCOUNT_JSON), scopes=SCOPES)

# --- Cache handling ---
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

# --- Fetch videos from Drive ---
def fetch_videos_from_drive():
    """Fetch all video files in folder, oldest to newest."""
    service = build("drive", "v3", credentials=creds)
    query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed=false"
    results = (
        service.files()
        .list(q=query, orderBy="createdTime asc", fields="files(id, name)")
        .execute()
    )
    return results.get("files", [])

# --- Get next video to post ---
def get_next_video():
    cache = load_cache()
    posted_ids = cache.get("posted_ids", [])
    videos = fetch_videos_from_drive()

    if not videos:
        raise RuntimeError("⚠️ No videos found in Drive folder!")

    # Find first unposted video
    for video in videos:
        if video["id"] not in posted_ids:
            posted_ids.append(video["id"])
            cache["posted_ids"] = posted_ids
            save_cache(cache)
            return video

    # If all videos were posted, loop back to the oldest video
    print("[INFO] All videos have been posted. Looping back to the first video.")
    video = videos[0]
    cache["posted_ids"] = [video["id"]]
    save_cache(cache)
    return video

# --- Post video to Facebook ---
def post_to_facebook(video_id, video_name):
    url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/videos"
    params = {
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        "description": VIDEO_CAPTION,
        "file_url": f"https://drive.google.com/uc?id={video_id}&export=download"
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        print(f"[SUCCESS] Posted video '{video_name}' to Facebook!")
    else:
        print(f"[ERROR] Failed to post video '{video_name}': {response.text}")

# --- Main function ---
def main():
    video = get_next_video()
    print(f"[DEBUG] Selected video: {video['name']} ({video['id']})")
    post_to_facebook(video['id'], video['name'])

if __name__ == "__main__":
    main()
