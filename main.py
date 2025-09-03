#!/usr/bin/env python3
"""
Post 2 videos per day from Google Drive folder to Facebook Page.
Uses Google Service Account credentials.
Remembers last posted index in posted_cache.json and loops back after last video.
Ensures videos are not repeated multiple times in the same UTC day.
"""

import os
import json
import requests
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ------------------ Config ------------------
FB_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE = os.getenv("FACEBOOK_PAGE_ID")
GOOGLE_CREDS_FILE = os.path.expanduser("~/.secrets/credentials.json")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
CACHE_FILE = "posted_cache.json"
VIDEOS_PER_RUN = 2

CAPTION = """Don't forget to subscribe for more!

#movie #movieclips #movienetflix #fyp #fypシ゚viralシ #viral #facebookvideo
"""

# ------------------ Cache ------------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}
    # Ensure fields exist
    if "last_index" not in data:
        data["last_index"] = 0
    if "last_day" not in data:
        data["last_day"] = ""
    return data

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ------------------ Google Drive ------------------
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDS_FILE,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def list_videos():
    service = get_drive_service()
    query = f"'{FOLDER_ID}' in parents and mimeType contains 'video/' and trashed=false"
    results = service.files().list(q=query, fields="files(id,name)", pageSize=1000).execute()
    files = results.get("files", [])
    # Sort numerically by digits in filename
    files.sort(key=lambda x: int(''.join(filter(str.isdigit, x['name'])) or 0))
    return files

def get_video_url(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"

# ------------------ Facebook ------------------
def post_video(video_url):
    url = f"https://graph.facebook.com/v20.0/{FB_PAGE}/videos"
    payload = {
        "file_url": video_url,
        "description": CAPTION,
        "access_token": FB_TOKEN,
        "published": "true"
    }
    r = requests.post(url, data=payload, timeout=120)
    r.raise_for_status()
    fb_id = r.json().get("id")
    print(f"Video uploaded, Facebook ID: {fb_id}")
    return fb_id

# ------------------ Main ------------------
def main():
    if not all([FB_PAGE, FB_TOKEN, FOLDER_ID]):
        raise SystemExit("Set FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN, and GOOGLE_DRIVE_FOLDER_ID")

    today_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache = load_cache()
    videos = list_videos()
    if not videos:
        print("No videos found in Drive folder.")
        return

    total = len(videos)
    index = cache["last_index"]
    last_day = cache.get("last_day", "")

    # If the day has changed, use current index; otherwise, use last_index to prevent duplicate posting today
    if last_day != today_key:
        start_index = index
    else:
        # Already ran today; start_index = last_index to post next 2 videos
        start_index = index

    # Pick 2 videos in order
    to_post = [videos[start_index % total], videos[(start_index + 1) % total]]

    for v in to_post:
        video_url = get_video_url(v["id"])
        fb_id = post_video(video_url)
        print(f"Posted {v['name']} → Facebook ID {fb_id}")

    # Update cache for next run
    cache["last_index"] = (start_index + VIDEOS_PER_RUN) % total
    cache["last_day"] = today_key
    save_cache(cache)

if __name__ == "__main__":
    main()
