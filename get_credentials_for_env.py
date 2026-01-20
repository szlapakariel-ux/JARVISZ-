import json
import os

def print_env_var(name, filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                content = json.load(f)
                # Dump to string with no whitespace to be safe for env vars
                json_str = json.dumps(content, separators=(',', ':'))
                print(f"\n--- [ {name} ] ---")
                print("Copia todo lo que está abajo de esta línea y pegalo en Railway:")
                print(json_str)
                print("------------------------------------------------------------")
        except Exception as e:
            print(f"Error leyendo {filename}: {e}")
    else:
        print(f"\n[FALTA] No se encontró el archivo {filename}. Asegurate de haber iniciado sesión localmente primero.")

if __name__ == "__main__":
    print("Generando valores para Variables de Entorno de Railway...")
    
    # GOOGLE_CREDENTIALS_JSON
    print_env_var("GOOGLE_CREDENTIALS_JSON", "credentials.json")
    
    # GOOGLE_TOKEN_JSON
    print_env_var("GOOGLE_TOKEN_JSON", "token.json")
    
    # GOOGLE_TOKEN_TASKS_JSON
    print_env_var("GOOGLE_TOKEN_TASKS_JSON", "token_tasks.json")
    
    print("\n\nLISTO. Agrega estas variables en la sección 'Variables' de tu proyecto en Railway.")
