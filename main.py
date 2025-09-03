#!/usr/bin/env python3
"""
Post 2 videos per day from Google Drive folder to Facebook Page.
Remembers last posted index in posted_cache.json and loops back after last video.
Ensures no duplicates in the same UTC day.
"""

import os
import json
import requests
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ---------------- CONFIG ----------------
FB_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE = os.getenv("FACEBOOK_PAGE_ID")
GOOGLE_CREDS_FILE = os.path.expanduser("~/.secrets/credentials.json")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
CACHE_FILE = "posted_cache.json"
VIDEOS_PER_RUN = 2

CAPTION = """Don't forget to subscribe for more!

#movie #movieclips #movienetflix #fyp #fypシ゚viralシ #viral #facebookvideo
"""

# ---------------- CACHE ----------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"last_index": 0, "last_date": ""}
    return {"last_index": 0, "last_date": ""}

def save_cache(last_index, last_date):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_index": last_index, "last_date": last_date}, f, indent=2)

# ---------------- GOOGLE DRIVE ----------------
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
    files.sort(key=lambda x: int(''.join(filter(str.isdigit, x['name'])) or 0))
    return files

def get_video_url(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"

# ---------------- FACEBOOK ----------------
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

# ---------------- MAIN ----------------
def main():
    if not all([FB_PAGE, FB_TOKEN, FOLDER_ID]):
        raise SystemExit("Set FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN, and GOOGLE_DRIVE_FOLDER_ID")

    videos = list_videos()
    if not videos:
        print("No videos found in Drive folder.")
        return

    total = len(videos)
    cache = load_cache()
    index = cache.get("last_index", 0)
    last_date = cache.get("last_date", "")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Prevent posting the same videos multiple times per day
    if last_date == today_str:
        print(f"Videos already posted today ({today_str}). Exiting.")
        return

    # pick 2 videos in order
    to_post = [videos[index % total], videos[(index + 1) % total]]

    for v in to_post:
        video_url = get_video_url(v["id"])
        fb_id = post_video(video_url)
        print(f"Posted {v['name']} → Facebook ID {fb_id}")

    # update index for next run and save today's date
    new_index = (index + VIDEOS_PER_RUN) % total
    save_cache(new_index, today_str)

if __name__ == "__main__":
    main()
