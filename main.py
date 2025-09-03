#!/usr/bin/env python3
"""
Post 2 videos per day from Google Drive folder to Facebook Page.
Keeps track of last posted index and loops back automatically.
"""

import os
import json
import requests
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

# ------------------ Cache Handling ------------------
def load_index():
    """Load last posted index, auto-initialize if missing or corrupted."""
    if not os.path.exists(CACHE_FILE):
        save_index(0)
        return 0
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_index", 0)
    except Exception:
        save_index(0)
        return 0

def save_index(index):
    """Save last posted index to cache."""
    with open(CACHE_FILE, "w") as f:
        json.dump({"last_index": index}, f)

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
    # sort numerically if filenames contain numbers
    files.sort(key=lambda x: int(''.join(filter(str.isdigit, x['name'])) or 0))
    return files

def get_video_url(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"

# ------------------ Facebook ------------------
def post_video(video_url, video_name):
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
    print(f"[OK] Posted '{video_name}' → Facebook ID: {fb_id}")
    return fb_id

# ------------------ Main ------------------
def main():
    if not all([FB_PAGE, FB_TOKEN, FOLDER_ID]):
        raise SystemExit("Set FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN, and GOOGLE_DRIVE_FOLDER_ID")

    videos = list_videos()
    if not videos:
        print("[WARN] No videos found in Drive folder.")
        return

    total = len(videos)
    index = load_index()
    print(f"[INFO] Last posted index: {index}, total videos: {total}")

    # pick next set of videos
    to_post = [videos[(index + i) % total] for i in range(VIDEOS_PER_RUN)]
    print("[INFO] Videos scheduled for posting today:")
    for v in to_post:
        print(f"  - {v['name']}")

    for v in to_post:
        video_url = get_video_url(v["id"])
        post_video(video_url, v["name"])

    # update index for next run
    new_index = (index + VIDEOS_PER_RUN) % total
    save_index(new_index)
    print(f"[INFO] Updated last_index to {new_index} for next run")

if __name__ == "__main__":
    main()
