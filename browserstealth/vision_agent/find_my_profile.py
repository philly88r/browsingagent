
import os
import json

def find_p_profile():
    user_data_path = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data')
    local_state_path = os.path.join(user_data_path, 'Local State')
    
    if not os.path.exists(local_state_path):
        print(f"Error: Could not find Chrome data at {local_state_path}")
        return

    try:
        with open(local_state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            profiles = data.get('profile', {}).get('info_cache', {})
            
            print("\n--- PHILLIP: LOOK FOR THE FOLDER NAME BELOW ---")
            found = False
            for folder, info in profiles.items():
                name = info.get('name', 'Unknown')
                if name == "P" or "P" in name:
                    print(f"FOUND IT! Folder Name: {folder} (Display Name: {name})")
                    found = True
                else:
                    print(f"Other Profile: {folder} (Name: {name})")
            
            if not found:
                print("\nCould not find a profile named exactly 'P'.")
                print("Please tell me which 'Folder Name' (e.g. Profile 3) you use for KDP.")
            print("-----------------------------------------------\n")
    except Exception as e:
        print(f"Error reading Chrome config: {e}")

if __name__ == "__main__":
    find_p_profile()
