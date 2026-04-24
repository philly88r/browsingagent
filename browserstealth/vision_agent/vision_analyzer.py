
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
        return '{' + key + '}'

class VisionAnalyzer:
    def __init__(self, model=None):
        self.model = model or "gemini-3-flash-preview"

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def plan_page(self, screenshot_paths, task_instruction, site_memory=""):
        if not prompts: return "No prompts found."
        items_str = "None"
        completed_section = prompts.PLANNER_COMPLETED_SECTION.format_map(SafeDict(items=items_str))
        prompt = prompts.PLANNER_TEMPLATE.format_map(SafeDict(
            task_instruction=task_instruction,
            completed_section=completed_section
        ))
        return f"Plan for {task_instruction}"

    def coordinate_task(self, task_instruction, url, milestones_str, plan_str, hist_str, semantic_map):
        if not prompts: return "Continue"
        prompt = prompts.COORDINATOR_TEMPLATE.format_map(SafeDict(
            task_instruction=task_instruction,
            milestones=milestones_str,
            active_plan=plan_str,
            action_history=hist_str,
            semantic_map=semantic_map or "No map"
        ))
        return "Continue with the task."

    def analyze_screenshot(self, screenshot_path, task_instruction, context, semantic_map=None):
        directive = self.coordinate_task(task_instruction, "", "", "", "", semantic_map)
        prompt = self._build_analysis_prompt(task_instruction, context, directive=directive, semantic_map=semantic_map)
        return {"action": "scroll", "parameters": {"amount": 500}, "reasoning": "Looking for content"}

    def _build_analysis_prompt(self, task_instruction, context, directive=None, semantic_map=None):
        if not prompts: return "No prompts."
        return prompts.MAIN_AGENT_TEMPLATE.format_map(SafeDict(
            task_instruction=task_instruction,
            directive=directive or "Continue",
            context=context,
            semantic_map=semantic_map or "None"
        ))
