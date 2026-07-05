"""
Galaxy Gamez - Admin Command Handler
Runs every ~5 minutes via GitHub Actions. Checks for new messages sent
to the bot by the admin, and reacts to commands like /post, /health, etc.
This is NOT an always-on bot - it's a periodic check, so commands are
answered within a few minutes, not instantly.
"""

import os
import requests

from main import (
    BOT_TOKEN, API_BASE, CHANNEL_IDS, BLOG_FEED_URL,
    load_state, save_state, load_stats, load_json, save_json,
    get_all_feed_entries, run_posting_cycle, POSTED_FILE, LOG_FILE,
)

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")


def reply(chat_id, text):
    try:
        requests.post(
            f"{API_BASE}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=30,
        )
    except Exception as e:
        print(f"Failed to reply: {e}")


def get_updates(offset):
    try:
        resp = requests.get(
            f"{API_BASE}/getUpdates",
            params={"offset": offset, "timeout": 0},
            timeout=30,
        )
        return resp.json().get("result", [])
    except Exception as e:
        print(f"Failed to get updates: {e}")
        return []


# ---------------- COMMAND HANDLERS ----------------

def cmd_post(chat_id):
    reply(chat_id, "Starting a posting cycle now...")
    result = run_posting_cycle(manual=True)
    reply(chat_id, f"Done. Result: {result}")


def cmd_refresh(chat_id):
    entries = get_all_feed_entries()
    posted = load_json(POSTED_FILE, [])
    unposted = [e for e in entries if e.link not in posted]
    reply(chat_id, f"Feed refreshed.\nTotal posts: {len(entries)}\nUnposted: {len(unposted)}")


def cmd_skip(chat_id):
    entries = get_all_feed_entries()
    posted = load_json(POSTED_FILE, [])
    unposted = [e for e in entries if e.link not in posted]
    if not unposted:
        reply(chat_id, "Nothing to skip - no unposted posts found.")
        return
    skipped = unposted[0]
    posted.append(skipped.link)
    save_json(POSTED_FILE, posted)
    reply(chat_id, f"Skipped: {skipped.title}")


def cmd_reset(chat_id):
    save_json(POSTED_FILE, [])
    reply(chat_id, "Posted-posts tracker cleared. Next cycle starts fresh.")


def cmd_health(chat_id):
    lines = ["HEALTH CHECK"]

    try:
        r = requests.get(f"{API_BASE}/getMe", timeout=15).json()
        lines.append(f"Telegram: OK ({r['result']['username']})" if r.get("ok") else "Telegram: FAILED")
    except Exception:
        lines.append("Telegram: FAILED")

    try:
        entries = get_all_feed_entries()
        lines.append(f"Blogger: OK ({len(entries)} posts in feed)")
    except Exception:
        lines.append("Blogger: FAILED")

    posted = load_json(POSTED_FILE, [])
    lines.append(f"Tracked posted posts: {len(posted)}")

    state = load_state()
    lines.append(f"Posting paused: {state.get('paused', False)}")

    if GITHUB_TOKEN and GITHUB_REPOSITORY:
        try:
            r = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/runs?per_page=1",
                headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
                timeout=15,
            ).json()
            run = r["workflow_runs"][0]
            lines.append(f"Last automation run: {run['name']} - {run['conclusion'] or run['status']}")
            lines.append(f"Last run at: {run['created_at']}")
        except Exception:
            lines.append("GitHub Actions status: unavailable")

    reply(chat_id, "\n".join(lines))


def cmd_stats(chat_id):
    stats = load_stats()
    posted = load_json(POSTED_FILE, [])
    entries = get_all_feed_entries()
    remaining = len([e for e in entries if e.link not in posted])
    reply(
        chat_id,
        f"STATS FOR {stats['date']}\n"
        f"Posts sent today: {stats['posts_sent']}\n"
        f"Successful deliveries: {stats['success']}\n"
        f"Failed deliveries: {stats['failed']}\n"
        f"Posts remaining in feed: {remaining}\n"
        f"Total channels: {len(CHANNEL_IDS)}",
    )


def cmd_logs(chat_id):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            content = f.read()
        reply(chat_id, content[-3500:] if content else "Log file is empty.")
    else:
        reply(chat_id, "No logs yet - the poster hasn't run since this was set up.")


def cmd_test(chat_id):
    reply(chat_id, "Test message - the bot and command system are working.")


def cmd_channels(chat_id):
    lines = ["CHANNEL CHECK"]
    for cid in CHANNEL_IDS:
        try:
            r = requests.get(f"{API_BASE}/getChat", params={"chat_id": cid}, timeout=15).json()
            if r.get("ok"):
                title = r["result"].get("title", "Unknown")
                lines.append(f"✓ {cid} ({title}) - reachable")
            else:
                lines.append(f"✗ {cid} - {r.get('description', 'error')}")
        except Exception as e:
            lines.append(f"✗ {cid} - {e}")
    reply(chat_id, "\n".join(lines))


def cmd_pause(chat_id):
    state = load_state()
    state["paused"] = True
    save_state(state)
    reply(chat_id, "Automatic posting paused. Scheduled cycles will be skipped until you /resume.")


def cmd_resume(chat_id):
    state = load_state()
    state["paused"] = False
    save_state(state)
    reply(chat_id, "Automatic posting resumed.")


def cmd_restart(chat_id):
    reply(
        chat_id,
        "There's no persistent process to restart - each posting cycle runs fresh "
        "and shuts down when done, so it can never get stuck. Nothing to do here.",
    )


def cmd_help(chat_id):
    reply(
        chat_id,
        "COMMANDS\n"
        "/post - post now\n"
        "/refresh - check feed for new posts\n"
        "/skip - skip the next unposted post\n"
        "/reset - clear posted history\n"
        "/health - system status\n"
        "/stats - today's stats\n"
        "/logs - latest run logs\n"
        "/test - send a test message\n"
        "/channels - check channel access\n"
        "/pause - pause auto-posting\n"
        "/resume - resume auto-posting\n"
        "/restart - info only, not needed\n"
        "/help - this list\n\n"
        "Note: commands are checked every ~5 minutes, not instantly.",
    )


COMMANDS = {
    "/post": cmd_post,
    "/refresh": cmd_refresh,
    "/skip": cmd_skip,
    "/reset": cmd_reset,
    "/health": cmd_health,
    "/stats": cmd_stats,
    "/logs": cmd_logs,
    "/test": cmd_test,
    "/channels": cmd_channels,
    "/pause": cmd_pause,
    "/resume": cmd_resume,
    "/restart": cmd_restart,
    "/help": cmd_help,
}


def main():
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print("Missing TELEGRAM_BOT_TOKEN or ADMIN_CHAT_ID.")
        return

    state = load_state()
    offset = state.get("last_update_id", 0)

    updates = get_updates(offset)
    if not updates:
        print("No new commands.")
        return

    for update in updates:
        state["last_update_id"] = update["update_id"] + 1
        message = update.get("message")
        if not message:
            continue

        chat_id = str(message["chat"]["id"])
        if chat_id != str(ADMIN_CHAT_ID):
            continue  # ignore anyone who isn't the admin

        text = message.get("text", "").strip()
        handler = COMMANDS.get(text)
        if handler:
            handler(chat_id)
        elif text.startswith("/"):
            reply(chat_id, "Unknown command. Send /help to see the list.")

    save_state(state)


if __name__ == "__main__":
    main()
