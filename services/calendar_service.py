from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

class CalendarService:
    def __init__(self):
        self.creds = None
        self.service = None
        
    def authenticate(self):
        """Shows basic usage of the Google Calendar API."""
        # Calculate absolute paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        token_path = os.path.join(base_dir, 'token.json')
        creds_path = os.path.join(base_dir, 'credentials.json')

        if os.path.exists(token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception:
                self.creds = None
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    self.creds = None
            
            if not self.creds:
                if os.path.exists(creds_path):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            creds_path, SCOPES)
                        # Run local server for auth
                        self.creds = flow.run_local_server(port=0)
                        # Save the credentials for the next run
                        with open(token_path, 'w') as token:
                            token.write(self.creds.to_json())
                    except Exception as e:
                        logger.error(f"Failed to auth flow: {e}")
                        return False
                else:
                    logger.warning(f"No credentials.json found at {creds_path}. Calendar disabled.")
                    return False

        try:
            self.service = build('calendar', 'v3', credentials=self.creds)
            logger.info("Calendar service initialized.")
            return True
        except Exception as e:
            logger.error(f"Failed to build calendar service: {e}")
            return False

    def get_upcoming_events(self, days_ahead=7):
        """
        Returns a pre-formatted string matching Google Calendar's Agenda View.
        Events are exploded: if an event spans 3 days, it appears in all 3 day buckets.
        """
        if not self.service:
            if not self.authenticate():
                return "No calendar access"

        try:
            # Timezones and Range
            tz = ZoneInfo("America/Argentina/Buenos_Aires")
            now = datetime.now(tz)
            start_range = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_range = start_range + timedelta(days=days_ahead)
            
            # API Query (pad query to catch spanning events)
            time_min = start_range.isoformat()
            time_max = end_time = end_range.replace(hour=23, minute=59).isoformat()
            
            # 1. Fetch from ALL calendars
            cal_list = self.service.calendarList().list().execute()
            calendars = cal_list.get('items', [])
            
            raw_events = []
            for cal in calendars:
                try:
                    res = self.service.events().list(
                        calendarId=cal['id'], timeMin=time_min, timeMax=time_max,
                        singleEvents=True, orderBy='startTime'
                    ).execute()
                    # Tag events with calendar color/name if needed (optional)
                    for e in res.get('items', []):
                        e['_cal_name'] = cal.get('summary')
                        raw_events.append(e)
                except: continue

            # 2. Bucket Logic (The "Explosion")
            # buckets = { datetime.date: [ (time_sort_key, string_representation) ] }
            daily_buckets = {}
            # Init buckets for the requested range
            curr = start_range.date()
            end_date_limit = end_range.date()
            while curr <= end_date_limit:
                daily_buckets[curr] = []
                curr += timedelta(days=1)

            for event in raw_events:
                summary = event.get('summary', 'Sin título')
                start = event['start']
                end = event['end']
                
                # Normalize to Date objects
                if 'date' in start:
                    # All Day
                    s_dt = datetime.strptime(start['date'], "%Y-%m-%d").date()
                    # Google end date is exclusive, so actual end is -1 day
                    e_dt = datetime.strptime(end['date'], "%Y-%m-%d").date() - timedelta(days=1)
                    is_all_day = True
                else:
                    # Timed
                    s_dt_full = datetime.fromisoformat(start['dateTime'])
                    e_dt_full = datetime.fromisoformat(end['dateTime'])
                    if s_dt_full.tzinfo is None: s_dt_full = s_dt_full.replace(tzinfo=tz)
                    else: s_dt_full = s_dt_full.astimezone(tz)
                    
                    s_dt = s_dt_full.date()
                    # For logic simplicity, treat timed events as single day if they don't span midnight drastically
                    # But if they do, we should explode. For now let's stick to start date for timed.
                    e_dt = s_dt 
                    is_all_day = False
                    start_time_str = s_dt_full.strftime("%H:%M")
                    end_time_str = e_dt_full.strftime("%H:%M")

                # Clamp to query range
                loop_start = max(s_dt, start_range.date())
                loop_end = min(e_dt, end_date_limit)
                
                # Iterate every day this event touches
                loop_curr = loop_start
                while loop_curr <= loop_end:
                    if loop_curr in daily_buckets:
                        if is_all_day:
                            # 🔵 Todo el día | Título
                            line = f"🔵 Todo el día | {summary}"
                            sort_k = "00:00"
                        else:
                            # 🔵 07:00 - 15:00 | Título
                            line = f"🔵 {start_time_str} - {end_time_str} | {summary}"
                            sort_k = start_time_str
                        
                        daily_buckets[loop_curr].append((sort_k, line))
                    loop_curr += timedelta(days=1)

            # 3. Format Output
            output_lines = []
            
            # Helper for Spanish months/days
            months_es = {1:"ENE", 2:"FEB", 3:"MAR", 4:"ABR", 5:"MAY", 6:"JUN", 7:"JUL", 8:"AGO", 9:"SEP", 10:"OCT", 11:"NOV", 12:"DIC"}
            days_es = {0:"LUN", 1:"MAR", 2:"MIÉ", 3:"JUE", 4:"VIE", 5:"SÁB", 6:"DOM"}

            sorted_dates = sorted(daily_buckets.keys())
            for d in sorted_dates:
                events_on_day = daily_buckets[d]
                if not events_on_day:
                    continue # Skip empty days or show "No events"? User image skips empty hours but shows days.
                
                # Header: 20 ENE, MAR
                day_str = days_es[d.weekday()]
                month_str = months_es[d.month]
                header = f"🗓 **{d.day} {month_str}, {day_str}**"
                output_lines.append(header)
                
                # Sort by time
                events_on_day.sort(key=lambda x: x[0])
                
                for _, line in events_on_day:
                    output_lines.append(line)
                
                output_lines.append("") # Spacer

            if not output_lines:
                return "No hay eventos próximos."
                
            return "\n".join(output_lines)

        except Exception as e:
            logger.error(f"Calendar fetch error: {e}")
            return f"Error leyendo calendario: {e}"

    def add_event(self, summary, start_time, end_time=None):
        """
        Creates a new event.
        start_time: datetime object or ISO string
        end_time: datetime object or ISO string (optional, defaults to +1 hour)
        """
        if not self.service:
            if not self.authenticate():
                return False

        try:
            # Ensure ISO format with Timezone Z if needed, or proper offset
            if isinstance(start_time, str):
                start_iso = start_time
            else:
                start_iso = start_time.isoformat()

            if not end_time:
                # Default 1 hour duration
                if isinstance(start_time, str):
                    s_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    e_dt = s_dt + timedelta(hours=1)
                    end_iso = e_dt.isoformat()
                else:
                    end_iso = (start_time + timedelta(hours=1)).isoformat()
            else:
                if isinstance(end_time, str):
                    end_iso = end_time
                else:
                    end_iso = end_time.isoformat()

            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_iso,
                    'timeZone': 'America/Argentina/Buenos_Aires',
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': 'America/Argentina/Buenos_Aires',
                },
            }

            event = self.service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f"Event created: {event.get('htmlLink')}")
            return True

        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return False

    def find_next_event(self, query):
        """Finds the next upcoming event matching query string."""
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            
            # Search next 30 days
            events_result = self.service.events().list(
                calendarId='primary', 
                timeMin=time_min,
                maxResults=50, singleEvents=True,
                orderBy='startTime').execute()
            events = events_result.get('items', [])
            
            query = query.lower()
            for event in events:
                summary = event.get('summary', '').lower()
                if query in summary:
                    return event
            return None
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None

    def delete_event(self, event_id):
        if not self.service:
            if not self.authenticate():
                return False
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            logger.info(f"Event {event_id} deleted.")
            return True
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return False
