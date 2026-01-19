from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token_tasks.json.
SCOPES = ['https://www.googleapis.com/auth/tasks']

class TasksService:
    def __init__(self):
        self.creds = None
        self.service = None
        
    def authenticate(self):
        """Authenticate with Google Tasks API."""
        if os.path.exists('token_tasks.json'):
            try:
                self.creds = Credentials.from_authorized_user_file('token_tasks.json', SCOPES)
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
                if os.path.exists('credentials.json'):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', SCOPES)
                        # Run local server for auth
                        self.creds = flow.run_local_server(port=0)
                        # Save the credentials for the next run
                        with open('token_tasks.json', 'w') as token:
                            token.write(self.creds.to_json())
                    except Exception as e:
                        logger.error(f"Failed to auth flow: {e}")
                        return False
                else:
                    logger.warning("No credentials.json found. Tasks disabled.")
                    return False

        try:
            self.service = build('tasks', 'v1', credentials=self.creds)
            logger.info("Tasks service initialized.")
            return True
        except Exception as e:
            logger.error(f"Failed to build tasks service: {e}")
            return False

    def get_all_tasks(self, max_results=20):
        """Get all pending tasks from all task lists."""
        if not self.service:
            if not self.authenticate():
                return "No tasks access"

        try:
            all_tasks = []
            
            # Get all task lists
            task_lists = self.service.tasklists().list().execute()
            lists = task_lists.get('items', [])
            
            if not lists:
                return "Sin listas de tareas"
            
            # Get tasks from each list
            for task_list in lists:
                list_id = task_list['id']
                list_name = task_list['title']
                
                tasks_result = self.service.tasks().list(
                    tasklist=list_id,
                    maxResults=max_results,
                    showCompleted=False,
                    showHidden=False
                ).execute()
                
                tasks = tasks_result.get('items', [])
                
                for task in tasks:
                    task_title = task.get('title', 'Sin título')
                    due_date = task.get('due', None)
                    notes = task.get('notes', '')
                    
                    task_info = f"📋 {task_title}"
                    if due_date:
                        # Parse due date
                        due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
                        due_dt_local = due_dt.astimezone(tz_argentina)
                        task_info += f" (vence: {due_dt_local.strftime('%d/%m/%Y')})"
                    
                    if list_name != "My Tasks":
                        task_info += f" [{list_name}]"
                    
                    all_tasks.append(task_info)
            
            if not all_tasks:
                return "Sin tareas pendientes"
            
            return "\n".join(all_tasks)

        except Exception as e:
            logger.error(f"Tasks fetch error: {e}")
            return "ErrorTasks"

    def create_task(self, title: str, notes: str = None, due_date: datetime = None, list_name: str = None):
        """Create a new task in Google Tasks."""
        if not self.service:
            if not self.authenticate():
                return False, "No tasks access"

        try:
            # Get task lists
            task_lists = self.service.tasklists().list().execute()
            lists = task_lists.get('items', [])
            
            if not lists:
                return False, "No hay listas de tareas disponibles"
            
            # Find the specified list or use the first one
            target_list_id = lists[0]['id']
            if list_name:
                for task_list in lists:
                    if task_list['title'].lower() == list_name.lower():
                        target_list_id = task_list['id']
                        break
            
            # Create task object
            task = {
                'title': title,
            }
            
            if notes:
                task['notes'] = notes
            
            if due_date:
                # Convert to RFC 3339 format
                task['due'] = due_date.isoformat()
            
            # Insert the task
            result = self.service.tasks().insert(
                tasklist=target_list_id,
                body=task
            ).execute()
            
            logger.info(f"Task created: {title}")
            return True, f"✅ Tarea creada: {title}"

        except Exception as e:
            logger.error(f"Task creation error: {e}")
            return False, f"Error al crear tarea: {e}"

    def get_todays_tasks(self):
        """Get tasks due today."""
        if not self.service:
            if not self.authenticate():
                return "No tasks access"

        try:
            tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
            today = datetime.now(tz_argentina).date()
            
            all_tasks = []
            
            # Get all task lists
            task_lists = self.service.tasklists().list().execute()
            lists = task_lists.get('items', [])
            
            if not lists:
                return "Sin listas de tareas"
            
            # Get tasks from each list
            for task_list in lists:
                list_id = task_list['id']
                list_name = task_list['title']
                
                tasks_result = self.service.tasks().list(
                    tasklist=list_id,
                    showCompleted=False,
                    showHidden=False
                ).execute()
                
                tasks = tasks_result.get('items', [])
                
                for task in tasks:
                    due_date = task.get('due', None)
                    
                    if due_date:
                        due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        due_dt_local = due_dt.astimezone(tz_argentina).date()
                        
                        if due_dt_local == today:
                            task_title = task.get('title', 'Sin título')
                            task_info = f"📋 {task_title}"
                            if list_name != "My Tasks":
                                task_info += f" [{list_name}]"
                            all_tasks.append(task_info)
            
            if not all_tasks:
                return "Sin tareas para hoy"
            
            return "\n".join(all_tasks)

        except Exception as e:
            logger.error(f"Tasks fetch error: {e}")
            return "ErrorTasks"

    def find_task(self, query):
        """Finds first pending task matching query."""
        if not self.service:
            if not self.authenticate():
                return None, "No auth"

        try:
            task_lists = self.service.tasklists().list().execute()
            lists = task_lists.get('items', [])
            
            query = query.lower()
            
            for task_list in lists:
                list_id = task_list['id']
                tasks_result = self.service.tasks().list(
                    tasklist=list_id,
                    showCompleted=False,
                    showHidden=False
                ).execute()
                
                tasks = tasks_result.get('items', [])
                for task in tasks:
                    title = task.get('title', '').lower()
                    if query in title:
                        return task, list_id
            return None, None
        except Exception as e:
            logger.error(f"Search task error: {e}")
            return None, None

    def delete_task(self, task_id, list_id):
        if not self.service:
            if not self.authenticate():
                return False
        try:
            self.service.tasks().delete(tasklist=list_id, task=task_id).execute()
            return True
        except Exception as e:
            logger.error(f"Delete task error: {e}")
            return False
