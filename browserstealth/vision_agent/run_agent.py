"""
Fresh launcher that forces module reload
"""
import sys
import os

# Clear any cached modules
for module in list(sys.modules.keys()):
    if 'human_like_movement' in module or 'browser_agent' in module or 'vision_analyzer' in module:
        del sys.modules[module]

# Now run the agent
from agent_ui import AgentUI

if __name__ == "__main__":
    app = AgentUI()
    app.run()
