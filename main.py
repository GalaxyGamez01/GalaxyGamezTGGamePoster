"""
Galaxy Gamez - Blogger to Telegram Auto Poster
Core posting engine. Uses plain HTTP requests to the Telegram API
(no async library), so every send either truly succeeds or truly
fails - checked against Telegram's own "ok" field every time.
"""

import os
import json
import random
import time
from datetime import date
import requests
import feedparser
from bs4 import BeautifulSoup

# ---------------- SETTINGS ----------------

BLOG_FEED_URL = "https://galaxygamez01.blogspot.com/feeds/posts/default?max-results=500"
CHANNEL_IDS = [
    -1002328517911,  # main channel
    -1001959406158,
    -1002392805703,
    -1002685110307,
    -1002353908594,
    -1002721819829,
]

WHATSAPP_LINKS = [
    "https://whatsapp.com/channel/0029Vb46RraF6smzVwGhZL2H",
    "https://whatsapp.com/channel/0029Vb56sG2IHphDA7uhWJ3C",
]
TELEGRAM_LINK = "https://t.me/GALAXYGAMEZ01"
WEBSITE_LINK = "https://galaxygamez01.blogspot.com"

POSTS_PER_CYCLE = 3
DELAY_BETWEEN_CHANNELS = 2       # seconds
DELAY_BETWEEN_POSTS_MIN = 5      # seconds
DELAY_BETWEEN_POSTS_MAX = 6
RETRY_ATTEMPTS = 5

POSTED_FILE = "posted_posts.json"
STATE_FILE = "state.json"
STATS_FILE = "stats.json"
LOG_FILE = "last_run_log.txt"

# -------------------------------------------

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

_log_lines = []


def log(line):
    print(line)
    _log_lines.append(line)


def save_log():
    with open(LOG_FILE, "w") as f:
        f.write("\n".join(_log_lines[-200:]))


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_state():
    return load_json(STATE_FILE, {"paused": False, "last_update_id": 0})


def save_state(state):
    save_json(STATE_FILE, state)


def today_str():
    return date.today().isoformat()


def load_stats():
    stats = load_json(STATS_FILE, {})
    if stats.get("date") != today_str():
        stats = {"date": today_str(), "posts_sent": 0, "success": 0, "failed": 0}
    return stats


def save_stats(stats):
    save_json(STATS_FILE, stats)


def get_all_feed_entries():
    feed = feedparser.parse(BLOG_FEED_URL)
    return feed.entries


def get_new_posts(count=POSTS_PER_CYCLE):
    """Returns (posts_to_send, posted_list). Auto-resets tracker if everything
    has already been posted, so the cycle restarts from the oldest posts."""
    entries = get_all_feed_entries()
    posted = load_json(POSTED_FILE, [])

    unposted = [e for e in entries if e.link not in posted]

    if not unposted and entries:
        log("All posts already published - clearing tracker and restarting cycle.")
        posted = []
        unposted = list(entries)

    random.shuffle(unposted)
    return unposted[:count], posted


def extract_image(entry):
    html = entry.get("summary", "")
    soup = BeautifulSoup(html, "html.parser")
    img = soup.find("img")
    return img["src"] if img and img.get("src") else None


def build_caption(entry):
    title = entry.title
    whatsapp_block = "\nAND\n".join(WHATSAPP_LINKS)
    return (
        f"☠️ GAME NAME:\n{title}\n\n"
        f"Download:\nLatest Update Highly Compressed HD Graphics\n\n"
        f"📂 Download Link\n{entry.link}\n\n"
        f"🔥 Follow us on WhatsApp\n{whatsapp_block}\n\n"
        f"🔥 Follow us on Telegram\n{TELEGRAM_LINK}\n\n"
        f"🔥 Visit For More Games\n{WEBSITE_LINK}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"POWERED BY GALAXY GAMEZ™\n"
        f"━━━━━━━━━━━━━━━━━"
    )


def send_once(channel_id, image_url, caption):
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

    if data.get("ok"):
        return True, "Sent"
    return False, data.get("description", "Unknown Telegram error")


def send_with_retry(channel_id, image_url, caption):
    delay = 1
    last_message = ""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        success, message = send_once(channel_id, image_url, caption)
        if success:
            return True, message
        last_message = message
        if attempt < RETRY_ATTEMPTS:
            time.sleep(delay)
            delay *= 2
    return False, last_message


def run_posting_cycle(manual=False):
    """Runs one full posting cycle. Returns a summary dict."""
    if not BOT_TOKEN:
        log("Missing TELEGRAM_BOT_TOKEN.")
        return {"error": "Missing TELEGRAM_BOT_TOKEN"}

    state = load_state()
    if state.get("paused") and not manual:
        log("Posting is paused. Skipping this scheduled cycle.")
        return {"skipped": "paused"}

    stats = load_stats()
    new_posts, posted = get_new_posts()

    if not new_posts:
        log("No posts found in the feed at all.")
        return {"posted": 0}

    for i, entry in enumerate(new_posts):
        image_url = extract_image(entry)
        caption = build_caption(entry)

        log(f"\nPosting: {entry.title}")
        all_ok = True

        for idx, channel_id in enumerate(CHANNEL_IDS):
            success, message = send_with_retry(channel_id, image_url, caption)
            status = "✓" if success else "✗"
            log(f"  {status} Channel {channel_id}: {message}")
            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
                all_ok = False
            if idx < len(CHANNEL_IDS) - 1:
                time.sleep(DELAY_BETWEEN_CHANNELS)

        if all_ok:
            posted.append(entry.link)
            stats["posts_sent"] += 1

        if i < len(new_posts) - 1:
            time.sleep(random.randint(DELAY_BETWEEN_POSTS_MIN, DELAY_BETWEEN_POSTS_MAX))

    save_json(POSTED_FILE, posted)
    save_stats(stats)
    save_log()

    log("\nDone. Posted history and stats updated.")
    return {"posted": len(new_posts), "stats": stats}


if __name__ == "__main__":
    run_posting_cycle()
