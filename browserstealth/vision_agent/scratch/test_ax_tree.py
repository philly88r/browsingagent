import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def test_ax_tree():
    options = Options()
    # options.add_argument("--headless") # Keep it visible for now
    
    # Initialize with fallback same as main agent
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"   [!] ChromeDriverManager failed ({e}), trying default chromedriver...")
        driver = webdriver.Chrome(options=options)
    
    try:
        driver.get("https://www.google.com") # Start with something simple
        time.sleep(2)
        
        # 1. Enable Accessibility
        driver.execute_cdp_cmd("Accessibility.enable", {})
        
        # 2. Get Full Tree
        print("Fetching AXTree...")
        ax_tree = driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})
        
        # 3. Analyze structure
        nodes = ax_tree.get('nodes', [])
        print(f"Total nodes found: {len(nodes)}")
        
        # Look for interactive nodes
        interactive_roles = {"button", "link", "textbox", "checkbox", "combobox", "menuitem"}
        
        print("\n--- SAMPLE INTERACTIVE NODES ---")
        found = 0
        for node in nodes:
            role = node.get('role', {}).get('value', '')
            name = node.get('name', {}).get('value', '')
            if role in interactive_roles and name:
                bounds = node.get('bounds')
                print(f"[{role}] \"{name}\" at {bounds}")
                found += 1
                if found > 10: break
                
        # Save a sample to inspect the full structure
        with open("scratch/ax_tree_sample.json", "w", encoding="utf-8") as f:
            json.dump(ax_tree, f, indent=2)
        print("\nFull sample saved to scratch/ax_tree_sample.json")

    finally:
        driver.quit()

if __name__ == "__main__":
    if not os.path.exists("scratch"): os.makedirs("scratch")
    test_ax_tree()
