from garminconnect import Garmin
from config import settings
from datetime import date
import logging

logger = logging.getLogger(__name__)

class GarminService:
    def __init__(self):
        self.email = settings.GARMIN_EMAIL
        self.password = settings.GARMIN_PASSWORD
        self.client = None

    def connect(self):
        if not self.client:
            try:
                self.client = Garmin(self.email, self.password)
                self.client.login()
                logger.info("Garmin connected successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to Garmin: {e}")
                raise e

    def get_todays_metrics(self):
        try:
            self.connect()
            today = date.today().isoformat()
            stats = self.client.get_stats(today)
            
            # Extract relevant fields based on our analysis
            return {
                "body_battery": stats.get("bodyBatteryMostRecentValue"),
                "stress_avg": stats.get("averageStressLevel"),
                "sleep_score": stats.get("sleepScore"), # Might be null depending on device
                "resting_hr": stats.get("restingHeartRate")
            }
        except Exception as e:
            logger.error(f"Error fetching Garmin stats: {e}")
            return None
