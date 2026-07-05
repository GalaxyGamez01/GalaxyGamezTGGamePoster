"""
Galaxy Gamez - Blogger to Telegram Auto Poster
Fetches new posts from Blogger and posts them to all Telegram channels.
Uses plain HTTP requests to the Telegram API (no async library),
so a call either truly succeeds or truly fails - no silent no-ops.
"""

import os
import json
import random
import requests
import feedparser
from bs4 import BeautifulSoup

# ---------------- SETTINGS (edit these) ----------------

BLOG_FEED_URL = "https://galaxygamez01.blogspot.com/feeds/posts/default"

CHANNEL_IDS = [
    -1002328517911,  # main channel
    -1001959406158,
    -1002392805703,
    -1002685110307,
    -1002353908594,
    -1002721819829,
]

# EDIT THESE with your real links before running:
WHATSAPP_LINK = "https://chat.whatsapp.com/PUT-YOUR-LINK-HERE"
TELEGRAM_LINK = "https://t.me/PUT-YOUR-LINK-HERE"
WEBSITE_LINK = "https://galaxygamez01.blogspot.com"

POSTS_PER_CYCLE = 3
POSTED_FILE = "posted_posts.json"

# ---------------------------------------------------------

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r") as f:
            return json.load(f)
    return []


def save_posted(posted_list):
    with open(POSTED_FILE, "w") as f:
        json.dump(posted_list, f, indent=2)


def get_new_posts():
    feed = feedparser.parse(BLOG_FEED_URL)
    posted = load_posted()
    new_posts = [p for p in feed.entries if p.link not in posted]
    random.shuffle(new_posts)
    return new_posts[:POSTS_PER_CYCLE], posted


def extract_image(entry):
    html = entry.get("summary", "")
    soup = BeautifulSoup(html, "html.parser")
    img = soup.find("img")
    return img["src"] if img and img.get("src") else None


def build_caption(entry):
    title = entry.title
    return (
        f"🎮 {title}\n\n"
        f"📥 Download: {entry.link}\n\n"
        f"📱 WhatsApp: {WHATSAPP_LINK}\n"
        f"✈️ Telegram: {TELEGRAM_LINK}\n"
        f"🌐 Website: {WEBSITE_LINK}"
    )


def send_to_channel(channel_id, image_url, caption):
    """Sends one post to one channel. Returns (success, message)."""
    if not BOT_TOKEN:
        return False, "Missing TELEGRAM_BOT_TOKEN"

    if image_url:
        url = f"{API_BASE}/sendPhoto"
        payload = {"chat_id": channel_id, "photo": image_url, "caption": caption}
    else:
        url = f"{API_BASE}/sendMessage"
        payload = {"chat_id": channel_id, "text": caption}

    try:
        resp = requests.post(url, data=payload, timeout=30)
        data = resp.json()
    except Exception as e:
        return False, f"Request failed: {e}"

    # This is the real success check - Telegram's own "ok" field.
    # This is what the old bot never actually checked.
    if data.get("ok"):
        return True, "Sent"
    else:
        return False, data.get("description", "Unknown Telegram error")


def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is not set. Check your GitHub Secret.")
        return

    new_posts, posted = get_new_posts()

    if not new_posts:
        print("No new posts to send. Nothing to do.")
        return

    for entry in new_posts:
        image_url = extract_image(entry)
        caption = build_caption(entry)

        print(f"\nPosting: {entry.title}")
        all_ok = True

        for channel_id in CHANNEL_IDS:
            success, message = send_to_channel(channel_id, image_url, caption)
            status = "✓" if success else "✗"
            print(f"  {status} Channel {channel_id}: {message}")
            if not success:
                all_ok = False

        # Only mark as posted if it actually succeeded somewhere,
        # so a full failure doesn't get silently skipped forever.
        if all_ok:
            posted.append(entry.link)

    save_posted(posted)
    print("\nDone. Posted history updated.")


if __name__ == "__main__":
    main()
