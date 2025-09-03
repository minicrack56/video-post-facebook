#!/usr/bin/env python3
"""
Post 2 videos per day from Google Drive folder to Facebook Page.
Keeps track of last posted index and loops back automatically.
Provides robust atomic writes for posted_cache.json and verbose logging.
"""

import os
import json
import tempfile
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ------------------ Config ------------------
FB_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE = os.getenv("FACEBOOK_PAGE_ID")
GOOGLE_CREDS_FILE = os.path.expanduser("~/.secrets/credentials.json")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
CACHE_FILE = "posted_cache.json"
VIDEOS_PER_RUN = int(os.getenv("VIDEOS_PER_RUN", 2))

CAPTION = """Don't forget to subscribe for more!

#movie #movieclips #movienetflix #fyp #viral #facebookvideo
"""

# ------------------ Cache Handling (robust + logging) ------------------
def load_index():
    """Load last posted index, auto-init if missing/corrupt, and log."""
    print("[CACHE] load_index()")
    if not os.path.exists(CACHE_FILE):
        print("[CACHE] not found, initializing to 0")
        save_index(0)
        return 0
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            idx = int(data.get("last_index", 0))
            print(f"[CACHE] read last_index = {idx}")
            return idx
    except Exception as e:
        print(f"[CACHE] error reading cache ({e}), resetting to 0")
        save_index(0)
        return 0

def save_index(index):
    """Save last posted index atomically and fsync to ensure file persisted."""
    print(f"[CACHE] save_index({index})")
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="posted_cache_", suffix=".json")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump({"last_index": int(index)}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, CACHE_FILE)
        with open(CACHE_FILE, "r") as f:
            print("[CACHE] after save: " + f.read())
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

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
    results = service.files().list(q=query, fields="files(id,name,createdTime)", pageSize=1000).execute()
    files = results.get("files", [])
    # Prefer stable sorting by createdTime, fallback to numeric name sorting
    try:
        files.sort(key=lambda x: x.get("createdTime", ""))  # ISO time sorts naturally
    except Exception:
        def numeric_sort_key(item):
            s = ''.join(filter(str.isdigit, item.get('name', '') or ''))
            return int(s) if s else 0
        files.sort(key=lambda x: (numeric_sort_key(x), x.get("name", "")))
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
        print(f"  - {v.get('name')}")

    success_count = 0
    for v in to_post:
        try:
            video_url = get_video_url(v["id"])
            post_video(video_url, v.get("name"))
            success_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to post {v.get('name')}: {e}")

    # update index for next run only if we posted at least one video
    # (this behavior can be changed — currently we advance regardless of partial failure)
    new_index = (index + VIDEOS_PER_RUN) % total
    save_index(new_index)
    print(f"[INFO] Updated last_index to {new_index} for next run (posted {success_count}/{len(to_post)})")

if __name__ == "__main__":
    main()
