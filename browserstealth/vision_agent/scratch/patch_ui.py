import sys

file_path = r'c:\Users\info\browserstealth\vision_agent\agent_ui.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "commentary = action.get('plan_commentary', '')" in line and "directive =" not in line:
        indent = line[:line.find("commentary")]
        new_lines.append(f"{indent}directive = action.get('_directive', '')\n")
        new_lines.append(line)
    elif "if commentary:" in line and "if directive:" not in line:
        indent = line[:line.find("if commentary")]
        new_lines.append(f"{indent}if directive:\n")
        new_lines.append(f"{indent}    self.log(f\"📋 DIRECTIVE: {{directive}}\", \"info\")\n")
        new_lines.append(line)
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Successfully patched agent_ui.py")
