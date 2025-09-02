#!/usr/bin/env python3
"""
Upload 2 videos per day from Google Drive to Facebook Page.
Loops back to Video1 after the last video.
"""

import os
import json
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account

# --------------------------------------------------------------
FB_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE  = os.getenv("FACEBOOK_PAGE_ID")

# Path to Google service account credentials JSON
GOOGLE_CREDS = "credentials.json"
FOLDER_ID    = os.getenv("GOOGLE_DRIVE_FOLDER_ID")  # folder where videos are stored

CACHE_FILE = "posted_cache.json"

CAPTION = """Don't forget to subscribe for more!

#movie #movieclips #movienetflix #fyp #fypシ゚viralシ #viral #facebookvideo
"""
# --------------------------------------------------------------


def load_index():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f).get("index", 0)
    return 0


def save_index(index):
    with open(CACHE_FILE, "w") as f:
        json.dump({"index": index}, f)


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDS,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds)


def list_videos():
    """Return sorted list of (id, name) for videos in Drive folder."""
    service = get_drive_service()
    query = f"'{FOLDER_ID}' in parents and mimeType contains 'video/'"
    results = (
        service.files()
        .list(q=query, fields="files(id, name)", pageSize=1000)
        .execute()
    )
    files = results.get("files", [])
    # Sort by filename like Video1, Video2, ...
    files.sort(key=lambda x: int(''.join(filter(str.isdigit, x['name']))))
    return files


def get_video_url(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def post_video(video_url):
    url = f"https://graph.facebook.com/v20.0/{FB_PAGE}/videos"
    payload = {
        "file_url": video_url,
        "description": CAPTION,
        "access_token": FB_TOKEN,
    }
    r = requests.post(url, data=payload, timeout=60)
    r.raise_for_status()
    return r.json().get("id")


def main():
    videos = list_videos()
    if not videos:
        print("No videos found in Drive folder.")
        return

    total = len(videos)
    index = load_index()

    # pick 2 videos in order
    to_post = [videos[index % total], videos[(index + 1) % total]]

    for v in to_post:
        url = get_video_url(v["id"])
        fb_id = post_video(url)
        print(f"Posted {v['name']} -> Facebook ID {fb_id}")

    # update index
    save_index((index + 2) % total)


if __name__ == "__main__":
    main()
