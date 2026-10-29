import os
import google.generativeai as genai
import json

# API Key from settings or environment
API_KEY = os.environ.get("GEMINI_API_KEY", "")

try:
    genai.configure(api_key=API_KEY)
    
    print("Listing available models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            
except Exception as e:
    print(f"Error: {e}")
