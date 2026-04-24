SYSTEM_JSON_STRICT = "Return ONLY valid JSON."
SYSTEM_JSON_COORDS = "Return JSON with element coordinates."
SYSTEM_RESCUE = "Recover the agent from a stuck state."

COORDINATOR_TEMPLATE = """You are the Lead Coordinator.
TASK: {task_instruction}
MILESTONES: {milestones}
PLAN: {active_plan}
HISTORY: {action_history}
MAP: {semantic_map}"""

MAIN_AGENT_TEMPLATE = """You are a vision agent.
TASK: {task_instruction}
DIRECTIVE: {directive}
CONTEXT: {context}
MAP: {semantic_map}"""

VERIFIER_TEMPLATE = "Verify {target} on page."
PLANNER_TEMPLATE = "Create a plan for {task_instruction}."
PLANNER_COMPLETED_SECTION = "Finished: {items}"
RESCUE_TEMPLATE = "Stuck on {task_instruction}. Last reasoning: {reasoning}"