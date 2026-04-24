import os
import json

def list_chrome_profiles():
    local_app_data = os.environ.get('LOCALAPPDATA')
    if not local_app_data:
        print("Could not find LOCALAPPDATA environment variable.")
        return

    path = os.path.join(local_app_data, 'Google', 'Chrome', 'User Data', 'Local State')
    if not os.path.exists(path):
        print(f"Could not find Local State file at {path}")
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
            profiles = state.get('profile', {}).get('info_cache', {})
            print("\n--- AVAILABLE CHROME PROFILES ---")
            for folder, info in profiles.items():
                name = info.get('name')
                email = info.get('user_name')
                print(f"Folder: {folder} | Name: {name} | Email: {email}")
            print("----------------------------------\n")
    except Exception as e:
        print(f"Error reading Local State: {e}")

if __name__ == "__main__":
    list_chrome_profiles()
