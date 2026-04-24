import time
import os
import json
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

try:
    from vision_analyzer import VisionAnalyzer
except ImportError:
    class VisionAnalyzer:
        def __init__(self, **kwargs): pass
        def analyze_screenshot(self, *args, **kwargs): return {"action": "wait"}
        def plan_page(self, *args, **kwargs): return "Plan"

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
        self.current_page_plan = ""
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), 'screenshots', self.instance_id)
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def log(self, m):
        if self.log_callback: self.log_callback(m)
        else: print(m)

    
    def start_browser(self):
        opts = Options()
        if self.headless: opts.add_argument('--headless')
        opts.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        
        # INJECTING LOCAL PROFILE PATH
        user_data_dir = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data')
        opts.add_argument(f'--user-data-dir={user_data_dir}')
        # Using the profile directory if specified, otherwise 'Default'
        profile = os.getenv('CHROME_PROFILE', 'Default')
        opts.add_argument(f'--profile-directory={profile}')
        
        try:
            srv = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=srv, options=opts)
        except: 
            self.driver = webdriver.Chrome(options=opts)
        self.log(f"✓ Browser started with profile: {profile}")


    def get_semantic_map(self):
        if not self.driver: return ""
        # Explicit timeout to prevent hanging
        start_time = time.time()
        try:
            self.driver.execute_cdp_cmd("Accessibility.enable", {})
            self.driver.execute_cdp_cmd("DOM.enable", {})
            
            all_els = []
            def scan(pref=""):
                if time.time() - start_time > 10: return [] # Safety timeout
                try:
                    tree = self.driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})
                    nodes = tree.get('nodes', [])
                    found = []
                    for n in nodes:
                        role = n.get('role', {}).get('value', '')
                        name = n.get('name', {}).get('value', '').strip()
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
            iframes = self.driver.find_elements("tag name", "iframe")
            for i, f in enumerate(iframes[:3]): # Cap at 3 iframes to prevent recursion loops
                try:
                    self.driver.switch_to.frame(f)
                    all_els.extend(scan(f"f{i+1}-"))
                    self.driver.switch_to.parent_frame()
                except: self.driver.switch_to.default_content()
            
            self.last_semantic_map = all_els
            return "--- MAP ---\n" + "\n".join([f"[{e['id']}] {e['role']} '{e['name']}'" for e in all_els])
        except Exception as e: 
            self.log(f"Map Error: {e}")
            return ""

    def run_task(self, task, start_url=None):
        if not self.driver: self.start_browser()
        if start_url: self.driver.get(start_url)
        for i in range(1, self.max_iterations + 1):
            self.log(f"\\n🔄 Iteration {i}/{self.max_iterations}")
            snap = os.path.join(self.screenshot_dir, f"step_{i}.png")
            try:
                self.driver.save_screenshot(snap)
                sem = self.get_semantic_map()
                # ENSURE we actually call the vision analyzer and use its result
                action = self.vision.analyze_screenshot(snap, task, f"Plan: {self.current_page_plan}", semantic_map=sem)
                
                atype = action.get('action')
                params = action.get('parameters', {})
                self.log(f"🤖 Agent Choice: {atype}")
                
                if atype == 'scroll':
                    self.driver.execute_script(f"window.scrollBy(0, {params.get('amount', 500)})")
                elif atype == 'click':
                    sid = params.get('semantic_id')
                    match = next((e for e in self.last_semantic_map if e['id'] == sid), None)
                    if match:
                        self.driver.execute_script(f"window.scrollTo({{top: {match['center'][1]-200}, behavior: 'instant'}})")
                        time.sleep(0.5)
                        self.driver.execute_script(f"document.elementFromPoint({match['center'][0]},{match['center'][1]}).click()")
                elif atype == 'complete':
                    self.log("✅ Task reported complete.")
                    break
            except Exception as e:
                self.log(f"Iteration Error: {e}")
            time.sleep(2)
