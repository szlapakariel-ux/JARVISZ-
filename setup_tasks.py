"""
Script para configurar la autenticación de Google Tasks
Este script abrirá un navegador para que autorices el acceso a tus tareas
"""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path

# If modifying these scopes, delete the file token_tasks.json.
SCOPES = ['https://www.googleapis.com/auth/tasks']

def main():
    creds = None
    
    # Check if we already have a token
    if os.path.exists('token_tasks.json'):
        print("✅ Ya existe un token_tasks.json")
        try:
            creds = Credentials.from_authorized_user_file('token_tasks.json', SCOPES)
            print("✅ Token cargado correctamente")
        except Exception as e:
            print(f"❌ Error al cargar token: {e}")
            creds = None
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refrescando token expirado...")
            try:
                creds.refresh(Request())
                print("✅ Token refrescado correctamente")
            except Exception as e:
                print(f"❌ Error al refrescar token: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists('credentials.json'):
                print("❌ No se encontró credentials.json")
                print("Por favor, descarga las credenciales de Google Cloud Console")
                return
            
            print("🌐 Iniciando flujo de autenticación...")
            print("Se abrirá un navegador para que autorices el acceso a Google Tasks")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token_tasks.json', 'w') as token:
                token.write(creds.to_json())
            print("✅ Token guardado en token_tasks.json")
    
    # Test the Tasks API
    try:
        service = build('tasks', 'v1', credentials=creds)
        print("\n🎉 ¡Autenticación exitosa!")
        print("Probando acceso a Google Tasks...")
        
        # Get task lists
        task_lists = service.tasklists().list().execute()
        lists = task_lists.get('items', [])
        
        if not lists:
            print('📋 No hay listas de tareas.')
        else:
            print(f'📋 Listas de tareas encontradas: {len(lists)}')
            for task_list in lists:
                print(f"  - {task_list['title']}")
                
                # Get tasks from this list
                tasks_result = service.tasks().list(
                    tasklist=task_list['id'],
                    maxResults=5,
                    showCompleted=False
                ).execute()
                tasks = tasks_result.get('items', [])
                
                if tasks:
                    print(f"    Tareas pendientes: {len(tasks)}")
                    for task in tasks[:3]:  # Show first 3
                        title = task.get('title', 'Sin título')
                        due = task.get('due', None)
                        if due:
                            print(f"      ✓ {title} (vence: {due[:10]})")
                        else:
                            print(f"      ✓ {title}")
                else:
                    print(f"    Sin tareas pendientes")
        
        print("\n✅ ¡Google Tasks está configurado correctamente!")
        print("Ahora JARVISZ puede leer y crear tareas.")
        
    except Exception as e:
        print(f"❌ Error al probar Google Tasks: {e}")

if __name__ == '__main__':
    main()
