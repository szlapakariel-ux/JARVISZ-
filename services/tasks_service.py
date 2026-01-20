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
        # Calculate absolute paths - Fixes the Relative Path Bug
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        token_path = os.path.join(base_dir, 'token_tasks.json')
        creds_path = os.path.join(base_dir, 'credentials.json')
        
        logger.info(f"Authenticating Tasks Service. Token path: {token_path}, Creds path: {creds_path}")

        # 1. Try Environment Variables (Priority for Server)
        # Check for specific Tasks token, otherwise reuse generic or calendar token logic if user prefers, 
        # but sticking to plan: check GOOGLE_TOKEN_TASKS_JSON
        env_token_json = os.environ.get('GOOGLE_TOKEN_TASKS_JSON')
        # Fallback to generic if specific not found (optional, but helpful if they are same account)
        if not env_token_json:
             env_token_json = os.environ.get('GOOGLE_TOKEN_JSON')

        env_creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')

        if env_token_json:
            try:
                import json
                info = json.loads(env_token_json)
                self.creds = Credentials.from_authorized_user_info(info, SCOPES)
                logger.info("Loaded Tasks credentials from Env Var.")
            except Exception as e:
                logger.error(f"Failed to load tasks token from env var: {e}")
                self.creds = None

        # 2. Try Local File
        if not self.creds and os.path.exists(token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                logger.info("Loaded Tasks credentials from local file.")
            except Exception:
                self.creds = None
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    logger.info("Refreshed Tasks token.")
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    self.creds = None
            
            if not self.creds:
                # Try to get client config from Env Var or File
                client_config = None
                
                if env_creds_json:
                     try:
                        import json
                        client_config = json.loads(env_creds_json)
                        logger.info("Loaded Client Config from GOOGLE_CREDENTIALS_JSON env var.")
                     except Exception as e:
                        logger.error(f"Failed to parse creds env var: {e}")

                if client_config:
                     try:
                        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                        self.creds = flow.run_local_server(port=0)
                     except Exception as e:
                         logger.error(f"Failed flow from client config: {e}") # Likely to fail on headless server without token

                elif os.path.exists(creds_path):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            creds_path, SCOPES)
                        # Run local server for auth
                        self.creds = flow.run_local_server(port=0)
                        # Save the credentials for the next run
                        with open(token_path, 'w') as token:
                            token.write(self.creds.to_json())
                        logger.info("Generated new token_tasks.json locally.")
                    except Exception as e:
                        logger.error(f"Failed to auth flow: {e}")
                        return False
                else:
                    logger.warning("No credentials found. Tasks disabled.")
                    return False

        try:
            self.service = build('tasks', 'v1', credentials=self.creds)
            logger.info("Tasks service initialized successfully.")
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
