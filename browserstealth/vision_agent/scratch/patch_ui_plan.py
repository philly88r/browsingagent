import sys

file_path = r'c:\Users\info\browserstealth\vision_agent\agent_ui.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "self.agent.scan_and_plan_page(task)" in line:
        indent = line[:line.find("self.agent")]
        new_lines.append(f"{indent}plan = self.agent.scan_and_plan_page(task)\n")
        new_lines.append(f"{indent}if plan:\n")
        new_lines.append(f"{indent}    self.log(f\"📋 PAGE PLAN:\\n{{plan}}\", \"info\")\n")
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Successfully updated agent_ui.py with plan logging")
