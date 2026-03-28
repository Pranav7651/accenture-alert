"""
Accenture India Job Alert — Telegram Edition
=============================================
Polls Accenture's Workday careers portal for new India jobs every hour.
Sends a Telegram message the moment a new listing appears.

Setup:
    pip install requests

Run once manually:
    python accenture_job_alert.py

Run continuously (checks every hour):
    python accenture_job_alert.py --watch

Send a test message to verify setup:
    python accenture_job_alert.py --test
"""

import requests
import json
import os
import time
import argparse
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG — Edit these values
# ─────────────────────────────────────────────

CONFIG = {
    # Telegram Bot Token — get from @BotFather on Telegram
    # Example: "7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    "telegram_bot_token": "8532589827:AAGGX7ffzD3L5ZD2EmOx1Yje-ncArgQEvQE",

    # Your Telegram Chat ID — get from @userinfobot on Telegram
    # Example: "987654321"
    "telegram_chat_id": "1259701853",

    # ── Job Filters ──────────────────────────
    # Keywords to search (leave empty "" to get ALL India jobs)
    "search_keyword": "Web Developer",

    # Location filter
    "location": "India",

    # How many jobs to fetch per check (max 20 recommended)
    "jobs_per_page": 20,

    # How often to check in minutes (default: 60)
    "check_interval_minutes": 60,

    # File to store seen job IDs between runs
    "state_file": "seen_jobs.json",
}

# ─────────────────────────────────────────────
#  Workday API — Accenture's internal endpoint
# ─────────────────────────────────────────────

WORKDAY_API = "https://accenture.wd103.myworkdayjobs.com/wday/cxs/accenture/AccentureCareers/jobs"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://accenture.wd103.myworkdayjobs.com/AccentureCareers",
}


# ─────────────────────────────────────────────
#  Telegram
# ─────────────────────────────────────────────

def send_telegram(message: str, cfg: dict):
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{cfg['telegram_bot_token']}/sendMessage"
    payload = {
        "chat_id": cfg["telegram_chat_id"],
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        print(f"[✓] Telegram message sent.")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Telegram send failed: {e}")


def test_telegram(cfg: dict):
    """Send a test message to verify setup."""
    msg = (
        "✅ <b>Accenture Job Alert is active!</b>\n\n"
        f"🔍 Watching for: <b>{cfg['search_keyword'] or 'all roles'}</b>\n"
        f"📍 Location: <b>{cfg['location']}</b>\n"
        f"⏱ Checking every <b>{cfg['check_interval_minutes']} min</b>\n\n"
        "You'll be notified here the moment new jobs are posted. 🚀"
    )
    send_telegram(msg, cfg)


# ─────────────────────────────────────────────
#  Job Fetching
# ─────────────────────────────────────────────

def fetch_jobs(keyword: str, location: str, limit: int) -> list[dict]:
    """Fetch jobs from Accenture's Workday API."""
    search_text = f"{keyword} {location}".strip() if keyword else location

    payload = {
        "appliedFacets": {},
        "limit": limit,
        "offset": 0,
        "searchText": search_text,
    }

    try:
        resp = requests.post(WORKDAY_API, headers=HEADERS, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("jobPostings", [])
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch jobs: {e}")
        return []


def build_job_url(job: dict) -> str:
    """Construct a direct link to the Accenture job listing."""
    path = job.get("externalPath", "")
    if path:
        return f"https://accenture.wd103.myworkdayjobs.com/AccentureCareers{path}"
    return "https://accenture.wd103.myworkdayjobs.com/AccentureCareers"


def load_seen_jobs(state_file: str) -> set:
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_jobs(state_file: str, seen: set):
    with open(state_file, "w") as f:
        json.dump(list(seen), f)


# ─────────────────────────────────────────────
#  Core Check Loop
# ─────────────────────────────────────────────

def run_check(cfg: dict) -> int:
    """Run one check cycle. Returns number of new jobs found."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking Accenture careers portal...")

    jobs = fetch_jobs(cfg["search_keyword"], cfg["location"], cfg["jobs_per_page"])
    print(f"  → Fetched {len(jobs)} jobs from portal")

    if not jobs:
        print("  → No jobs returned (API may be temporarily unavailable). Skipping.")
        return 0

    seen = load_seen_jobs(cfg["state_file"])
    new_jobs = []

    for job in jobs:
        unique_key = f"{job.get('title', '')}|{job.get('locationsText', '')}"
        if unique_key not in seen:
            new_jobs.append(job)
            seen.add(unique_key)

    if new_jobs:
        print(f"  → 🎉 {len(new_jobs)} NEW job(s) found! Sending Telegram alert...")

        for job in new_jobs:
            title    = job.get("title", "N/A")
            location = job.get("locationsText", "India")
            posted   = job.get("postedOn", "")
            url      = build_job_url(job)

            msg = (
                f"🔔 <b>New Accenture Job!</b>\n\n"
                f"💼 <b>{title}</b>\n"
                f"📍 {location}\n"
                + (f"🗓 {posted}\n" if posted else "")
                + f"\n<a href='{url}'>👉 Apply Now</a>"
            )
            send_telegram(msg, cfg)
            print(f"     • {title} — {location}")
            time.sleep(0.5)  # avoid Telegram rate limit on burst
    else:
        print("  → No new jobs since last check.")

    save_seen_jobs(cfg["state_file"], seen)
    return len(new_jobs)


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Accenture India Job Alert — Telegram")
    parser.add_argument("--watch", action="store_true",
                        help="Run continuously every N minutes")
    parser.add_argument("--test", action="store_true",
                        help="Send a test Telegram message and exit")
    args = parser.parse_args()

    print("=" * 52)
    print("  Accenture India Job Alert — Telegram Edition")
    print("=" * 52)
    print(f"  Keyword  : {CONFIG['search_keyword'] or '(all roles)'}")
    print(f"  Location : {CONFIG['location']}")
    print(f"  Chat ID  : {CONFIG['telegram_chat_id']}")
    print(f"  Interval : every {CONFIG['check_interval_minutes']} min")
    print("=" * 52)

    if args.test:
        print("\n▶ Sending test message to Telegram...")
        test_telegram(CONFIG)
        return

    if args.watch:
        print("\n▶ Watch mode ON. Press Ctrl+C to stop.\n")
        send_telegram(
            f"▶️ <b>Job Alert started!</b>\n"
            f"Watching Accenture India for <b>{CONFIG['search_keyword'] or 'all roles'}</b>\n"
            f"Checking every {CONFIG['check_interval_minutes']} min ⏱",
            CONFIG
        )
        while True:
            run_check(CONFIG)
            print(f"  Sleeping {CONFIG['check_interval_minutes']} min...\n")
            time.sleep(CONFIG["check_interval_minutes"] * 60)
    else:
        run_check(CONFIG)
        print("\n  Tip: Run with --watch to poll continuously.")


if __name__ == "__main__":
    main()


# ═══════════════════════════════════════════════════════════════════
#  SETUP GUIDE
# ═══════════════════════════════════════════════════════════════════
#
#  STEP 1 — Create a Telegram Bot (takes 1 minute)
#  ──────────────────────────────────────────────────
#  1. Open Telegram → search @BotFather → tap START
#  2. Send:  /newbot
#  3. Give it a name e.g.  Accenture Job Alert
#  4. Give it a username e.g.  accenture_jobs_pranav_bot
#  5. BotFather gives you a token like:
#       7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#  6. Paste it into CONFIG["telegram_bot_token"] above
#
#  STEP 2 — Get your Chat ID
#  ──────────────────────────
#  1. Open Telegram → search @userinfobot → tap START
#  2. It instantly replies with your ID e.g.  987654321
#  3. Paste it into CONFIG["telegram_chat_id"] above
#
#  STEP 3 — Start your bot (one time only)
#  ─────────────────────────────────────────
#  Search your bot's username on Telegram and press START.
#  (Without this, the bot can't message you.)
#
#  STEP 4 — Install dependency & test
#  ────────────────────────────────────
#  pip install requests
#  python accenture_job_alert.py --test
#
#  You should get a Telegram message within seconds.
#
#  STEP 5 — Run it
#  ─────────────────
#  python accenture_job_alert.py --watch
#
#  To run 24/7 for free → deploy on Railway.app or Render.com
# ═══════════════════════════════════════════════════════════════════
