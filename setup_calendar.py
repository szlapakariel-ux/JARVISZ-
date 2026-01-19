"""
Script para configurar la autenticación de Google Calendar
Este script abrirá un navegador para que autorices el acceso a tu calendario
"""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def main():
    creds = None
    
    # Check if we already have a token
    if os.path.exists('token.json'):
        print("✅ Ya existe un token.json")
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
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
            print("Se abrirá un navegador para que autorices el acceso")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            print("✅ Token guardado en token.json")
    
    # Test the calendar API
    try:
        service = build('calendar', 'v3', credentials=creds)
        print("\n🎉 ¡Autenticación exitosa!")
        print("Probando acceso al calendario...")
        
        # Get the next 5 events
        from datetime import datetime
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now,
            maxResults=5, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        if not events:
            print('📅 No hay eventos próximos.')
        else:
            print(f'📅 Próximos {len(events)} eventos:')
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f"  - {start}: {event['summary']}")
        
        print("\n✅ ¡Google Calendar está configurado correctamente!")
        print("Ahora JARVISZ puede acceder a tu calendario.")
        
    except Exception as e:
        print(f"❌ Error al probar el calendario: {e}")

if __name__ == '__main__':
    main()
