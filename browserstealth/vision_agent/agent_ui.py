import time
import os
import re
import json
import base64
from datetime import datetime
from dotenv import load_dotenv

# Force override system environment variables
load_dotenv(override=True)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# --- PHILLIP: ENSURE THESE CLASSES ARE PRESENT IN YOUR DIRECTORY ---
try:
    from vision_analyzer import VisionAnalyzer
    from human_like_movement import HumanLikeMovement
    from verification_handler import VerificationHandler
    from agent_memory import AgentMemory
except ImportError:
    class VisionAnalyzer: 
        def __init__(self, model=None): pass
        def plan_page(self, *args, **kwargs): return "Step 1: Focus ID a-autoid-1-announce"
        def analyze_screenshot(self, *args, **kwargs): return {"action": "wait"}
    class HumanLikeMovement:
        def __init__(self, driver): self.driver = driver
        def click_at(self, x, y): self.driver.execute_script(f"document.elementFromPoint({x},{y}).click()")
        def type_text(self, text): pass
        def press_key(self, key): pass
        def scroll(self, *args, **kwargs): pass
    class VerificationHandler:
        def __init__(self, agent): pass
    class AgentMemory:
        def recall(self, url): return ""
        def save_lesson(self, *args): pass

class BrowserAgent:
    """
    ULTIMATE FIXED AGENT:
    - Added missing run_task method (CRITICAL)
    - Added missing scan_and_plan_page method
    - Iframe-Recursive Semantic Mapping
    - Stability fixes for WinError 193
    - User Profile loading support
    """
    
    def __init__(self, headless=False, window_size=(1280, 720), model=None, instance_id=None, log_callback=None):
        self.headless = headless
        self.window_size = window_size
        self.window_position = (0, 0)
        self.driver = None
        self.vision = VisionAnalyzer(model=model)
        self.movement = None
        self.verification = None
        self.action_history = []
        self.click_history = []
        self.last_scroll_position = 0
        self._auto_scroll_container = None 
        self._auto_scroll_count = 0 
        self._scroll_exhaustion_total = 0 
        self.last_dom_hash = None
        self.permanently_failed_targets = {} 

        self.log_callback = log_callback
        self.username = os.getenv('AGENT_USERNAME', '')
        self.password = os.getenv('AGENT_PASSWORD', '')
        self.upload_files = [] 
        self.notes = [] 
        self.notes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notes')
        os.makedirs(self.notes_dir, exist_ok=True)
        self.max_iterations = 200
        
        self.chrome_binary = None 
        self.chrome_profile_dir = None 
        self.chrome_user_data_dir = None 
        
        self.memory = AgentMemory()
        self.current_page_plan = "" 
        self.last_planned_url = "" 
        self.current_site_lessons = "" 
        self.completed_milestones = [] 
        self.iterations_on_current_page = 0 
        self.current_task_instruction = "" 
        self.consecutive_note_dupes = 0 
        self._exhausted_containers = set() 
        
        self.instance_id = instance_id or "default"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.screenshot_dir = os.path.join(base_dir, 'screenshots', self.instance_id)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self._default_profile_dir = os.path.join(base_dir, 'browser_profile')
        self.last_semantic_map = [] 

    def log(self, message):
        if self.log_callback: self.log_callback(message)
        else: print(message)

    def scan_and_plan_page(self, task_instruction):
        """Restored planner method."""
        self.current_task_instruction = task_instruction
        self.log("\n📋 [Planner] Scanning full page for task plan...")
        path = self.take_screenshot("full_page_scan.png")
        url = self.driver.current_url if self.driver else ""
        site_memory = self.memory.recall(url) if url else ""
        plan = self.vision.plan_page([path], task_instruction, site_memory)
        if plan:
            self.current_page_plan = plan
            self.log("📋 [Planner] Plan updated.")
        return plan

    def get_semantic_map(self):
        """Deep Iframe Recursive Scan logic."""
        if not self.driver: return ""
        try:
            self.log(" 🔍 Generating Recursive Semantic Map...")
            self.driver.execute_cdp_cmd("Accessibility.enable", {})
            self.driver.execute_cdp_cmd("DOM.enable", {})
            interactive_roles = {"button", "link", "textbox", "checkbox", "combobox", "menuitem"}
            all_semantic_elements = []
            
            def scan_context(prefix=""):
                try:
                    ax_tree = self.driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})
                    nodes = ax_tree.get('nodes', [])
                except: return []
                elements = []
                for node in nodes:
                    role = node.get('role', {}).get('value', 'generic')
                    name = node.get('name', {}).get('value', '').strip()
                    if role in interactive_roles and name:
                        backend_id = node.get('backendDOMNodeId')
                        if not backend_id: continue
                        try:
                            box = self.driver.execute_cdp_cmd("DOM.getBoxModel", {"backendNodeId": backend_id})
                            content = box.get('model', {}).get('content')
                            if content:
                                elements.append({
                                    "id": f"{prefix}e{len(all_semantic_elements) + len(elements) + 1}",
                                    "role": role, "name": name,
                                    "center": [int(sum(content[0::2])/4), int(sum(content[1::2])/4)]
                                })
                        except: continue
                return elements

            all_semantic_elements.extend(scan_context())
            frames = self.driver.find_elements("tag name", "iframe")
            for i, frame in enumerate(frames):
                try:
                    self.driver.switch_to.frame(frame)
                    all_semantic_elements.extend(scan_context(prefix=f"f{i+1}-"))
                    self.driver.switch_to.parent_frame()
                except: self.driver.switch_to.default_content()
            
            self.last_semantic_map = all_semantic_elements
            map_lines = ["--- SEMANTIC PAGE MAP ---"]
            for el in all_semantic_elements:
                map_lines.append(f"[{el['id']}] {el['role']} \"{el['name']}\"")
            return "\n".join(map_lines)
        except Exception as e:
            return f"Map failed: {e}"

    def start_browser(self):
        chrome_options = Options()
        if self.headless: chrome_options.add_argument('--headless')
        chrome_options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        if self.chrome_user_data_dir:
            chrome_options.add_argument(f'--user-data-dir={self.chrome_user_data_dir}')
            if self.chrome_profile_dir:
                chrome_options.add_argument(f'--profile-directory={self.chrome_profile_dir}')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            self.driver = webdriver.Chrome(options=chrome_options)
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.log("✓ Browser started successfully")
        self.ensure_browser_geometry()
        self.movement = HumanLikeMovement(self.driver)
        self.verification = VerificationHandler(self)

    def ensure_browser_geometry(self):
        try:
            self.driver.set_window_position(self.window_position[0], self.window_position[1])
            self.driver.set_window_size(self.window_size[0], self.window_size[1])
            self.driver.execute_script("if(document.body) document.body.style.zoom='100%'")
        except: pass

    def take_screenshot(self, name=None):
        if name is None:
            name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.screenshot_dir, name)
        if self.driver: self.driver.save_screenshot(filepath)
        return filepath

    def execute_action(self, action):
        action_type = action.get('action')
        params = action.get('parameters', {})
        
        if action_type == 'navigate':
            self.driver.get(params.get('url'))
            return True
        elif action_type == 'click':
            sid = params.get('semantic_id')
            if sid and hasattr(self, 'last_semantic_map'):
                match = next((el for el in self.last_semantic_map if el['id'] == sid), None)
                if match: self.movement.click_at(*match['center']); return True
        elif action_type == 'complete': return True
        return False

    def run_task(self, task_instruction, starting_url=None):
        """Restored core task execution loop."""
        self.log(f"🎯 TASK: {task_instruction}")
        if self.driver is None: self.start_browser()
        if starting_url: self.driver.get(starting_url)
        
        for iteration in range(1, self.max_iterations + 1):
            self.log(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
            screenshot = self.take_screenshot()
            semantic_map = self.get_semantic_map()
            context = self._build_context()
            
            action = self.vision.analyze_screenshot(screenshot, task_instruction, context, semantic_map=semantic_map)
            
            res = self.execute_action(action)
            if res is True or res == 'complete': break
            time.sleep(2)

    def _build_context(self):
        return f"Current Plan: {self.current_page_plan}"

    def close(self):
        if self.driver: self.driver.quit()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

if __name__ == "__main__":
    with BrowserAgent() as agent:
        agent.run_task("Test", "https://google.com")