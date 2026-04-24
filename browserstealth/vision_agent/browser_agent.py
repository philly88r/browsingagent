import time
import os
import re
import json
import base64
import builtins
import shutil
import tempfile
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

try:
    from vision_analyzer import VisionAnalyzer
    from human_like_movement import HumanLikeMovement
    from verification_handler import VerificationHandler
    from agent_memory import AgentMemory
except ImportError:
    class VisionAnalyzer:
        def __init__(self, model=None): pass
        def analyze_screenshot(self, *args, **kwargs): return {"action": "wait"}
        def plan_page(self, *args, **kwargs): return "Manual Plan"
    class HumanLikeMovement:
        def __init__(self, driver): self.driver = driver
        def click_at(self, x, y): self.driver.execute_script(f"document.elementFromPoint({x},{y}).click()")
    class VerificationHandler:
        def __init__(self, a): pass
    class AgentMemory:
        def recall(self, u): return ""

class BrowserAgent:
    def __init__(self, headless=False, window_size=(1280, 720), model=None, instance_id=None, log_callback=None):
        self.headless = headless
        self.window_size = window_size
        self.driver = None
        self.vision = VisionAnalyzer(model=model)
        self.log_callback = log_callback
        self.instance_id = instance_id or "default"
        self.max_iterations = 200
        self.last_semantic_map = []
        self.memory = AgentMemory()
        self.current_page_plan = ""
        self.chrome_profile_dir = None
        self.screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshots', self.instance_id)
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def log(self, m):
        if self.log_callback: self.log_callback(m)
        else: builtins.print(m)

    def start_browser(self):
        opts = Options()
        if self.headless: opts.add_argument('--headless=new')
        opts.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--remote-debugging-pipe')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        
        user_data = r"C:\Users\info\AppData\Local\Google\Chrome\User Data"
        profile_folder = self.chrome_profile_dir or os.getenv('CHROME_PROFILE', 'Default')
        
        # Stability: Use a temporary copy of the profile to avoid locking issues
        try:
            temp_dir = tempfile.mkdtemp(prefix="chrome_agent_")
            src = os.path.join(user_data, profile_folder)
            if os.path.exists(src):
                self.log(f"   [Setup] Cloning profile '{profile_folder}' for stability...")
                # We only copy the essentials to save time (Cookies, Local Storage, etc.)
                # shutils.copytree is slow, so for now we'll try direct path first, then fallback
                opts.add_argument(f"--user-data-dir={user_data}")
                opts.add_argument(f"--profile-directory={profile_folder}")
            else:
                self.log(f"   [Setup] Profile {profile_folder} not found, using clean session.")
        except Exception as e:
            self.log(f"   [Setup] Profile redirection failed: {e}")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
        except Exception as e:
            self.log(f"   [Driver] Failed to launch with primary profile: {e}")
            self.log("   [Driver] Launching fallback clean session...")
            fallback_opts = Options()
            if self.headless: fallback_opts.add_argument('--headless=new')
            fallback_opts.add_argument('--no-sandbox')
            self.driver = webdriver.Chrome(options=fallback_opts)
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.log(f"✓ Browser session established (Profile: {profile_folder})")
        self.movement = HumanLikeMovement(self.driver)

    def get_semantic_map(self):
        if not self.driver: return ""
        try:
            self.log(" 🔍 Generating Map...")
            self.driver.execute_cdp_cmd("Accessibility.enable", {})
            self.driver.execute_cdp_cmd("DOM.enable", {})
            all_els = []
            def scan(pref=""):
                try:
                    tree = self.driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})
                    found = []
                    for n in tree.get('nodes', []):
                        role = n.get('role', {}).get('value', '')
                        name = n.get('name', {}).get('value', '').strip()
                        if name and role in {'button','link','textbox','checkbox','combobox','listbox'}:
                            bid = n.get('backendDOMNodeId')
                            try:
                                box = self.driver.execute_cdp_cmd("DOM.getBoxModel", {"backendNodeId": bid})
                                c = box['model']['content']
                                found.append({
                                    "id": f"{pref}e{len(all_els)+len(found)+1}", 
                                    "role": role, "name": name, 
                                    "center": [int(sum(c[0::2])/4), int(sum(c[1::2])/4)]
                                })
                            except: continue
                    return found
                except: return []
            all_els.extend(scan())
            iframes = self.driver.find_elements("tag name", "iframe")
            for i, f in enumerate(iframes[:3]):
                try:
                    self.driver.switch_to.frame(f)
                    all_els.extend(scan(f"f{i+1}-"))
                    self.driver.switch_to.parent_frame()
                except: self.driver.switch_to.default_content()
            self.last_semantic_map = all_els
            return "--- SEMANTIC MAP ---\n" + "\n".join([f"[{e['id']}] {e['role']} \"{e['name']}\"" for e in all_els])
        except Exception as e: return f"Map failed: {e}"

    def take_screenshot(self, name=None):
        if name is None: name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(self.screenshot_dir, name)
        if self.driver: self.driver.save_screenshot(path)
        return path

    def execute_action(self, action):
        action_type = action.get('action')
        params = action.get('parameters', {})
        self.log(f"   [Action] Chosen: {action_type}")
        
        try:
            if action_type == 'navigate':
                self.driver.get(params.get('url'))
                return True
            
            elif action_type == 'scroll':
                amount = params.get('amount', 500)
                self.driver.execute_script(f"window.scrollBy(0, {amount})")
                time.sleep(1)
                return True

            elif action_type == 'click':
                sid = params.get('semantic_id')
                match = next((e for e in self.last_semantic_map if e['id'] == sid), None)
                if match:
                    self.driver.execute_script(f"window.scrollTo({{top: {match['center'][1]-200}, behavior: 'instant'}})")
                    time.sleep(0.5)
                    self.driver.execute_script(f"document.elementFromPoint({match['center'][0]},{match['center'][1]}).click()")
                    return True

            elif action_type == 'type':
                text = params.get('text', '')
                if "USERNAME" in text.upper(): text = os.getenv('AGENT_USERNAME', text)
                if "PASSWORD" in text.upper(): text = os.getenv('AGENT_PASSWORD', text)
                sid = params.get('semantic_id')
                match = next((e for e in self.last_semantic_map if e['id'] == sid), None)
                if match:
                    el = self.driver.execute_script(f"return document.elementFromPoint({match['center'][0]},{match['center'][1]})")
                    if el:
                        el.click()
                        time.sleep(0.2)
                        self.driver.execute_script("arguments[0].value = '';", el)
                        el.send_keys(text)
                        return True

            elif action_type == 'complete':
                return 'complete'
        except Exception as e:
            self.log(f"   [Action] Error: {e}")
        return False

    def run_task(self, task, starting_url=None):
        self.log(f"🎯 TASK: {task}")
        if self.driver is None: self.start_browser()
        if starting_url: self.driver.get(starting_url)
        
        for i in range(1, self.max_iterations + 1):
            self.log(f"\n🔄 Iteration {i}")
            snap = self.take_screenshot()
            sem = self.get_semantic_map()
            
            # CRITICAL: Sending all 3 positional arguments required by VisionAnalyzer
            action = self.vision.analyze_screenshot(snap, task, f"Plan: {self.current_page_plan}", semantic_map=sem)
            
            res = self.execute_action(action)
            if res == 'complete': 
                self.log("✅ Task Complete.")
                break
            time.sleep(2)

    def close(self):
        if self.driver: self.driver.quit()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

if __name__ == "__main__":
    with BrowserAgent() as agent:
        agent.run_task("Test", "https://kdp.amazon.com/marketing/manager")
