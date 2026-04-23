import sys

file_path = r'c:\Users\info\browserstealth\vision_agent\vision_analyzer.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the top-level import with a module import
old_import = """from prompts import (
    SYSTEM_JSON_STRICT,
    SYSTEM_JSON_COORDS,
    SYSTEM_RESCUE,
    MAIN_AGENT_TEMPLATE,
    PLANNER_TEMPLATE,
    PLANNER_COMPLETED_SECTION,
    VERIFIER_TEMPLATE,
    RESCUE_TEMPLATE,
    COORDINATOR_TEMPLATE,
)"""

new_import = "import prompts"

if old_import in content:
    content = content.replace(old_import, new_import)
else:
    # Try with unix line endings if needed
    old_import_unix = old_import.replace('\r\n', '\n')
    if old_import_unix in content:
        content = content.replace(old_import_unix, new_import)

# Now replace all usages with prompts.VAR_NAME
replacements = {
    'SYSTEM_JSON_STRICT': 'prompts.SYSTEM_JSON_STRICT',
    'SYSTEM_JSON_COORDS': 'prompts.SYSTEM_JSON_COORDS',
    'SYSTEM_RESCUE': 'prompts.SYSTEM_RESCUE',
    'MAIN_AGENT_TEMPLATE': 'prompts.MAIN_AGENT_TEMPLATE',
    'PLANNER_TEMPLATE': 'prompts.PLANNER_TEMPLATE',
    'PLANNER_COMPLETED_SECTION': 'prompts.PLANNER_COMPLETED_SECTION',
    'VERIFIER_TEMPLATE': 'prompts.VERIFIER_TEMPLATE',
    'RESCUE_TEMPLATE': 'prompts.RESCUE_TEMPLATE',
    'COORDINATOR_TEMPLATE': 'prompts.COORDINATOR_TEMPLATE',
}

for old, new in replacements.items():
    # Use word boundary or exact match to avoid partial replacements
    # but since these are all-caps constants it's usually safe
    content = content.replace(old, new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully refactored vision_analyzer.py to use 'import prompts' module access.")
