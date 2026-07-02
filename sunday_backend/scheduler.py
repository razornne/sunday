import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

import pipeline

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def main():
    now = datetime.now(timezone.utc)
    cur_day = now.strftime("%A")
    cur_hour = now.strftime("%H")
    print(f"🚀 Sunday AI Scheduler | {cur_day} {cur_hour}:00 UTC")

    profiles = supabase.table("profiles").select("*").execute().data
    if not profiles:
        print("💤 No profiles.")
        return

    for profile in profiles:
        digest_day = profile.get("digest_day", "Sunday")
        digest_hour = str(profile.get("digest_time", "09:00"))[:2]

        if digest_day != cur_day or digest_hour != cur_hour:
            continue

        print(f"👤 Running digest for {profile.get('personal_email') or profile['id']}")
        try:
            pipeline.run_digest(profile["id"])
        except Exception as e:
            print(f"❌ Digest failed for {profile['id']}: {e}")

    print("🏁 Scheduler run complete.")


if __name__ == "__main__":
    main()
