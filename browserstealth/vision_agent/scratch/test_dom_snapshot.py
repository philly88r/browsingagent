import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def test_dom_snapshot():
    options = Options()
    # options.add_argument("--headless")
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"   [!] ChromeDriverManager failed ({e}), trying default chromedriver...")
        driver = webdriver.Chrome(options=options)
    
    try:
        driver.get("https://www.google.com")
        time.sleep(2)
        
        # 1. Capture DOM Snapshot (includes Layout and Accessibility)
        print("Capturing DOM Snapshot...")
        snapshot = driver.execute_cdp_cmd("DOMSnapshot.captureSnapshot", {
            "computedStyles": ["display", "visibility", "opacity"],
            "includeAccessibilityTree": True
        })
        
        # 2. Analyze
        doc = snapshot['documents'][0]
        nodes = doc['nodes']
        layout = doc['layout']
        ax = doc['accessibilityTreeNodes']
        
        print(f"Found {len(nodes['nodeName'])} nodes and {len(layout['nodeIndex'])} layout objects.")
        
        # Map layout index back to node index
        node_to_layout = {node_idx: i for i, node_idx in enumerate(layout['nodeIndex'])}
        
        # Interactive roles we care about
        interactive_roles = {"button", "link", "textbox", "checkbox", "combobox", "menuitem"}
        
        print("\n--- SEMANTIC MAP ---")
        found = 0
        for i, node_name in enumerate(nodes['nodeName']):
            # Find associated AX node
            ax_node_index = nodes['accessibilitySearchId'].get(str(i)) # This might vary by Chrome version
            # Simplified for demo: find by index in ax tree
            
            # For now, let's just find anything with a role and name
            # (In the real implementation, we'll use a more robust mapping)
            pass

        # Save to inspect
        with open("scratch/dom_snapshot_sample.json", "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        print("\nFull snapshot saved to scratch/dom_snapshot_sample.json")

    finally:
        driver.quit()

if __name__ == "__main__":
    if not os.path.exists("scratch"): os.makedirs("scratch")
    test_dom_snapshot()
