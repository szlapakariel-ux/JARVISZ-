import asyncio
import json
from garminconnect import Garmin
from config import settings
from datetime import date

async def dump_garmin_data():
    email = settings.GARMIN_EMAIL
    password = settings.GARMIN_PASSWORD
    
    print(f"Connecting to Garmin...")
    try:
        client = Garmin(email, password)
        client.login()
        print("Login OK.")
        
        today = date.today().isoformat()
        print(f"Fetching stats for {today}...")
        
        # Get various endpoints to see where data is hiding
        stats = client.get_stats(today)
        user_summary = client.get_user_summary(today)
        body_battery = client.get_body_battery(today) # Specific endpoint if available
        
        full_dump = {
            "stats": stats,
            "user_summary": user_summary,
            "body_battery_endpoint": body_battery
        }
        
        with open("garmin_full_dump.json", "w", encoding="utf-8") as f:
            json.dump(full_dump, f, indent=4, default=str)
            
        print("Done. Saved to garmin_full_dump.json")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(dump_garmin_data())
