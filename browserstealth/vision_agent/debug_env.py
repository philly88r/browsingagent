"""
Debug script to check what API key is being loaded
"""
import os
from dotenv import load_dotenv

print("Current working directory:", os.getcwd())
print()

# Check if .env file exists
env_path = os.path.join(os.getcwd(), '.env')
print(f".env file exists: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        print(f".env contents:\n{f.read()}")

print("\n" + "="*60)
print("Loading .env file...")
load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f"Loaded API key: {api_key}")
print(f"Key length: {len(api_key) if api_key else 0}")
print(f"First 20 chars: {api_key[:20] if api_key else 'None'}...")
