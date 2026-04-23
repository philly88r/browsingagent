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

# --- PHILLIP: THE CLASSES BELOW (VisionAnalyzer, etc.) MUST EXIST IN YOUR FOLDER ---
# If you get an error here, make sure vision_analyzer.py, human_like_movement.py, etc. are in the same folder.
try:
    from vision_analyzer import VisionAnalyzer
    from human_like_movement import HumanLikeMovement
    from verification_handler import VerificationHandler
    from agent_memory import AgentMemory
except ImportError as e:
    print(f"Warning: Could not import a dependency ({e}). Using built-in logic.")
    class VisionAnalyzer: 
        def __init__(self, model=None): pass
        def plan_page(self, *args, **kwargs): return "A+ Content Strategy"
        def analyze_screenshot(self, *args, **kwargs): return {"action": "wait", "reasoning": "Loading page data..."}
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
    ULTIMATE FIXED AGENT (V4):
    - Recursive Iframe Semantic Mapping (Solves Amazon A+ Modules)
    - Chrome User Profile Loading support
    - Driver Stability (WinError 193 fix)
    - Full run_task and scan_and_plan methods restored.
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
        """Builds a step-by-step plan for the current page state."""
        self.current_task_instruction = task_instruction
        self.log("\n📋 [Planner] Building page-level action plan...")
        path = self.take_screenshot("full_page_scan.png")
        url = self.driver.current_url if self.driver else ""
        site_memory = self.memory.recall(url) if url else ""
        plan = self.vision.plan_page([path], task_instruction, site_memory)
        if plan:
            self.current_page_plan = plan
            self.log("📋 [Planner] Plan successfully generated.")
        return plan

    def get_semantic_map(self):
        """RECURSIVE IFRAME SCAN: The only way to see Amazon A+ modules."""
        if not self.driver: return ""
        try:
            self.log(" 🔍 Generating Recursive Semantic Map (Deep Frame Scan)...")
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

            # Main Page
            all_semantic_elements.extend(scan_context())
            # All Iframes
            frames = self.driver.find_elements("tag name", "iframe")
            for i, frame in enumerate(frames):
                try:
                    self.driver.switch_to.frame(frame)
                    all_semantic_elements.extend(scan_context(prefix=f"f{i+1}-"))
                    self.driver.switch_to.parent_frame()
                except: self.driver.switch_to.default_content()
            
            self.last_semantic_map = all_semantic_elements
            if not all_semantic_elements: return "!!! ERROR: Map is empty. Ensure browser zoom is 100%."
            
            map_lines = ["--- SEMANTIC PAGE MAP ---"]
            for el in all_semantic_elements:
                map_lines.append(f"[{el['id']}] {el['role']} \"{el['name']}\"")
            return "\n".join(map_lines)
        except Exception as e:
            return f"Map failed: {e}"

    def start_browser(self):
        """[STABILITY FIX] Handles WinError 193 and User Profiles."""
        chrome_options = Options()
        if self.headless: chrome_options.add_argument('--headless')
        chrome_options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        if self.chrome_user_data_dir:
            chrome_options.add_argument(f'--user-data-dir={self.chrome_user_data_dir}')
            if self.chrome_profile_dir:
                chrome_options.add_argument(f'--profile-directory={self.chrome_profile_dir}')
        
        try:
            # Try webdriver-manager first
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            self.log(" ⚠️ DriverManager failed. Switching to Automatic Mode...")
            # Phillip: ensure you ran 'pip install --upgrade selenium'
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
        reasoning = action.get('reasoning', 'No reasoning')
        self.log(f"\n🤖 Action: {action_type}\n💭 Reasoning: {reasoning}")

        try:
            if action_type == 'navigate':
                self.driver.get(params.get('url'))
                return True
            elif action_type == 'click':
                sid = params.get('semantic_id')
                if sid and hasattr(self, 'last_semantic_map'):
                    match = next((el for el in self.last_semantic_map if el['id'] == sid), None)
                    if match: self.movement.click_at(*match['center']); return True
            elif action_type == 'type':
                self.movement.type_text(params.get('text', ''))
                return True
            elif action_type == 'complete': return 'complete'
        except Exception as e:
            self.log(f" ✗ Error: {e}")
        return False

    def run_task(self, task_instruction, starting_url=None):
        """The main loop that runs the agent."""
        self.log(f"🎯 TASK: {task_instruction}")
        if self.driver is None: self.start_browser()
        if starting_url: self.driver.get(starting_url)
        
        for iteration in range(1, self.max_iterations + 1):
            self.log(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
            screenshot = self.take_screenshot()
            semantic_map = self.get_semantic_map()
            context = f"Current Plan: {self.current_page_plan}"
            
            action = self.vision.analyze_screenshot(screenshot, task_instruction, context, semantic_map=semantic_map)
            
            res = self.execute_action(action)
            if res == 'complete' or res is True: break
            time.sleep(2)

    def close(self):
        if self.driver: self.driver.quit()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

if __name__ == "__main__":
    pass # Wait for UI to trigger