import time
import os
import re
import json
import base64
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
        def __init__(self, **kwargs): pass
        def analyze_screenshot(self, *args, **kwargs): return {"action": "wait"}
        def plan_page(self, *args, **kwargs): return "Plan"
    class HumanLikeMovement:
        def __init__(self, driver): self.driver = driver
        def click_at(self, x, y): self.driver.execute_script(f"document.elementFromPoint({x},{y}).click()")
    class VerificationHandler:
        def __init__(self, a): pass
    class AgentMemory:
        def recall(self, u): return ""

class BrowserAgent:
    def __init__(self, headless=False, window_size=(1280, 720), model=None, instance_id=None, log_callback=None):
        self.headless, self.window_size = headless, window_size
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
        else: print(m)

    def scan_and_plan_page(self, task):
        self.log("\n📋 [Planner] Building plan...")
        path = self.take_screenshot("full_page_scan.png")
        url = self.driver.current_url if self.driver else ""
        self.current_page_plan = self.vision.plan_page([path], task, self.memory.recall(url))
        return self.current_page_plan

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
                        role, name = n.get('role', {}).get('value', ''), n.get('name', {}).get('value', '').strip()
                        if name and role in {'button','link','textbox','checkbox','combobox','listbox'}:
                            bid = n.get('backendDOMNodeId')
                            try:
                                box = self.driver.execute_cdp_cmd("DOM.getBoxModel", {"backendNodeId": bid})
                                c = box['model']['content']
                                found.append({"id": f"{pref}e{len(all_els)+len(found)+1}", "role": role, "name": name, "center": [int(sum(c[0::2])/4), int(sum(c[1::2])/4)]})
                            except: continue
                    return found
                except: return []
            all_els.extend(scan())
            for i, f in enumerate(self.driver.find_elements("tag name", "iframe")):
                try:
                    self.driver.switch_to.frame(f)
                    all_els.extend(scan(f"f{i+1}-"))
                    self.driver.switch_to.parent_frame()
                except: self.driver.switch_to.default_content()
            self.last_semantic_map = all_els
            return "--- SEMANTIC PAGE MAP ---\n" + "\n".join([f"[{e['id']}] {e['role']} \"{e['name']}\"" for e in all_els])
        except Exception as e: return f"Map failed: {e}"



    def start_browser(self):
        opts = Options()
        if self.headless: opts.add_argument('--headless=new')
        opts.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--remote-debugging-pipe')
        opts.add_argument('--process-per-site')
        opts.add_argument('--disable-features=site-per-process,IsolateOrigins')
        opts.add_argument('--disable-extensions')
        opts.add_argument('--disable-background-networking')
        opts.add_argument('--disable-background-timer-throttling')
        opts.add_argument('--disable-backgrounding-occluded-windows')
        opts.add_argument('--disable-renderer-backgrounding')
        
        # Copy profile to temp to avoid lock conflicts
        import tempfile, shutil
        user_data = r"C:\Users\info\AppData\Local\Google\Chrome\User Data"
        profile_folder = self.chrome_profile_dir or os.getenv('CHROME_PROFILE', 'Default')
        temp_dir = tempfile.mkdtemp(prefix="chrome_agent_")
        src_profile = os.path.join(user_data, profile_folder)
        if os.path.exists(src_profile):
            self.log(f"   [Setup] Copying profile '{profile_folder}' to temp dir...")
            shutil.copytree(src_profile, os.path.join(temp_dir, profile_folder), dirs_exist_ok=True)
            self.log(f"   [Setup] Profile copied to {temp_dir}")
        else:
            self.log(f"   [Setup] Profile not found, using clean temp profile")
        opts.add_argument(f"--user-data-dir={temp_dir}")
        opts.add_argument(f"--profile-directory={profile_folder}")
        self._temp_profile_dir = temp_dir
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
        except Exception as e:
            self.log(f"   [Driver] Profile error (likely locked): {e}")
            self.log("   [Driver] Starting STABLE fallback session...")
            fallback_opts = Options()
            if self.headless: fallback_opts.add_argument('--headless=new')
            fallback_opts.add_argument('--no-sandbox')
            self.driver = webdriver.Chrome(options=fallback_opts)
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.log(f"✓ Browser session established.")

    def ensure_browser_geometry(self):
        try:
            self.driver.set_window_size(self.window_size[0], self.window_size[1])
            self.driver.execute_script("if(document.body) document.body.style.zoom='100%'")
        except: pass
        self.movement = HumanLikeMovement(self.driver)
        self.verification = VerificationHandler(self)



    def take_screenshot(self, name=None):
        if name is None: name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.screenshot_dir, name)
        if self.driver: self.driver.save_screenshot(filepath)
        return filepath

    def execute_action(self, action):
        atype, params = action.get('action'), action.get('parameters', {})
        if atype == 'navigate': self.driver.get(params.get('url')); return True
        elif atype == 'click':
            match = next((e for e in self.last_semantic_map if e['id'] == params.get('semantic_id')), None)
            if match:
                self.driver.execute_script(f"window.scrollTo({{top: {match['center'][1]-200}, behavior: 'instant'}})")
                time.sleep(0.5)
                self.driver.execute_script(f"document.elementFromPoint({match['center'][0]},{match['center'][1]}).click()")
                return True
        elif atype == 'complete': return True
        return False

    def run_task(self, task, starting_url=None):
        self.log(f"🎯 TASK: {task}")
        if self.driver is None: self.start_browser()
        if starting_url: self.driver.get(starting_url)
        for iteration in range(1, self.max_iterations + 1):
            self.log(f"\n🔄 Iteration {iteration}")
            snap = self.take_screenshot()
            sem = self.get_semantic_map()
            action = self.vision.analyze_screenshot(snap, task, f"Plan: {self.current_page_plan}", semantic_map=sem)
            if self.execute_action(action) is True: break
            time.sleep(2)

    def close(self):
        if self.driver: self.driver.quit()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

if __name__ == "__main__":
    with BrowserAgent() as agent:
        agent.run_task("Test", "https://kdp.amazon.com/marketing/manager")
