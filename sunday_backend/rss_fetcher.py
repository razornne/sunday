import os
import time
from datetime import datetime, timezone
import feedparser
from dotenv import load_dotenv
from supabase import create_client, Client

from utils import aggressive_clean_html

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def entry_content(entry):
    if entry.get("content"):
        return entry["content"][0].get("value", "")
    return entry.get("summary") or entry.get("description") or ""


def entry_published_at(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc).isoformat()


def fetch_feed(feed):
    feed_url = feed["feed_url"]
    print(f"🔎 Fetching {feed_url}")
    parsed = feedparser.parse(feed_url)

    if parsed.bozo and not parsed.entries:
        error_msg = str(parsed.get("bozo_exception", "Unknown parse error"))
        print(f"   ❌ Parse error: {error_msg}")
        supabase.table("rss_feeds").update({
            "last_error": error_msg,
            "last_fetched_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", feed["id"]).execute()
        return

    updates = {"last_fetched_at": datetime.now(timezone.utc).isoformat(), "last_error": None}
    feed_title = parsed.feed.get("title")
    if feed_title and not feed.get("title"):
        updates["title"] = feed_title

    inserted = 0
    for entry in parsed.entries:
        external_id = entry.get("id") or entry.get("link")
        if not external_id:
            continue

        clean_text = aggressive_clean_html(entry_content(entry))
        if len(clean_text) > 20000:
            clean_text = clean_text[:20000] + "..."
        if not clean_text:
            continue

        row = {
            "user_id": feed["user_id"],
            "sender": feed.get("title") or feed_title or feed_url,
            "subject": entry.get("title", "Untitled"),
            "body_plain": clean_text,
            "source_type": "rss",
            "source_url": entry.get("link"),
            "external_id": external_id,
            "received_at": entry_published_at(entry),
            "processing_status": "pending",
        }

        try:
            supabase.table("raw_emails").insert(row).execute()
            inserted += 1
        except Exception as e:
            # Unique violation on (user_id, external_id) means we've already seen this item
            if "duplicate key" not in str(e).lower():
                print(f"   ⚠️ Insert error for '{row['subject']}': {e}")

    supabase.table("rss_feeds").update(updates).eq("id", feed["id"]).execute()
    print(f"   ✅ {inserted} new item(s)")


def main():
    print("🚀 Starting RSS fetch run...")
    feeds = supabase.table("rss_feeds").select("*").eq("is_active", True).execute().data

    if not feeds:
        print("💤 No active feeds.")
        return

    for feed in feeds:
        try:
            fetch_feed(feed)
        except Exception as e:
            print(f"❌ Unexpected error for feed {feed.get('feed_url')}: {e}")

    print("🏁 RSS fetch run complete.")


if __name__ == "__main__":
    main()
