#!/usr/bin/env python3
import os
import json
import io
import requests
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
CACHE_FILE = "posted_cache.json"

# Secrets
DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
creds = Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]), scopes=SCOPES
)

# ---------------- CACHE HANDLING ----------------
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

# ---------------- GOOGLE DRIVE ----------------
def fetch_videos_from_drive():
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

def download_video(file_id, file_name):
    service = build("drive", "v3", credentials=creds)
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")
    return file_name

# ---------------- FACEBOOK ----------------
def post_to_facebook(video_path, caption=""):
    url = f"https://graph-video.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/videos"
    params = {
        "access_token": FACEBOOK_ACCESS_TOKEN,
        "published": "true",
        "description": caption,
    }
    with open(video_path, "rb") as f:
        files = {"source": f}
        response = requests.post(url, data=params, files=files)
    print("Facebook response:", response.json())
    return response.json()

# ---------------- MAIN ----------------
def main():
    try:
        video = get_next_video()
    except RuntimeError as e:
        print(str(e))
        return

    print(f"[DEBUG] Selected video: {video['name']} ({video['id']})")

    # Download video
    file_name = download_video(video["id"], video["name"])

    # Post to Facebook
    caption = (
        "Don't forget to subscribe for more!\n\n"
        "#movie #movieclips #movienetflix #fyp #fypシ゚viralシ #viral #facebookvideo"
    )
    result = post_to_facebook(file_name, caption)
    print("[DONE] Video posted:", result)

    # Delete local video to keep runner clean
    try:
        os.remove(file_name)
        print(f"Deleted local file: {file_name}")
    except Exception as e:
        print(f"Failed to delete {file_name}: {e}")

if __name__ == "__main__":
    main()
