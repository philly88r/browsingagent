import sys

file_path = r'c:\Users\info\browserstealth\vision_agent\agent_ui.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_call = "action = self.agent.vision.analyze_screenshot(screenshot_path, task, context)"
new_call = "action = self.agent.vision.analyze_screenshot(screenshot_path, task, context, milestones=self.agent.completed_milestones)"

if old_call in content:
    content = content.replace(old_call, new_call)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully updated analyze_screenshot call in agent_ui.py")
else:
    print("Could not find analyze_screenshot call in agent_ui.py")
