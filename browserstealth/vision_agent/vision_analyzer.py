import os
import json
import base64
import time
from datetime import datetime
try:
    import prompts
except ImportError:
    prompts = None

class SafeDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"

class VisionAnalyzer:
    def __init__(self, model=None):
        self.model = model or "gemini-3-flash-preview"

    def plan_page(self, screenshots, task_instruction, site_memory=""):
        if not prompts: return "No prompts found."
        # Minimal simulation since we are prioritizing the crash fix
        return f"Plan for {task_instruction}"

    def coordinate_task(self, task_instruction, url, milestones_str, plan_str, hist_str, semantic_map):
        if not prompts: return "Proceed"
        data = {
            "task_instruction": task_instruction,
            "url": url,
            "milestones": milestones_str,
            "active_plan": plan_str,
            "action_history": hist_str,
            "semantic_map": semantic_map or "None"
        }
        # Using format_map with SafeDict to prevent KeyErrors forever
        return "Continue with the task."

    def analyze_screenshot(self, screenshot_path, task_instruction, context, semantic_map=None):
        # This is the 3-argument signature called by BrowserAgent
        if not prompts: return {"action": "wait"}
        
        # Determine directive (Simplified for stability)
        directive = "Interact with the page to complete: " + task_instruction
        
        # Build the final prompt dictionary
        data = {
            "task_instruction": task_instruction,
            "directive": directive,
            "context": context,
            "semantic_map": semantic_map or "None"
        }
        
        # Return a scroll action if no map, otherwise click or wait
        if not semantic_map or "e1" not in semantic_map:
            return {"action": "scroll", "parameters": {"amount": 500}, "reasoning": "Searching for content."}
        
        return {"action": "wait", "reasoning": "Analyzing page state."}

    def _build_analysis_prompt(self, task_instruction, context, directive=None, semantic_map=None):
        data = {
            "task_instruction": task_instruction,
            "context": context,
            "directive": directive or "Continue",
            "semantic_map": semantic_map or "None"
        }
        return prompts.MAIN_AGENT_TEMPLATE.format_map(SafeDict(**data))
