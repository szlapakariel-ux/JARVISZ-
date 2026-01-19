import google.generativeai as genai
from config import settings
import os

# Manually set the key here to be sure, or load from settings
key = settings.GEMINI_API_KEY.get_secret_value()
genai.configure(api_key=key)

print(f"Checking models for key ending in ...{key[-4:]}")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")
