SYSTEM_JSON_STRICT = "Return ONLY a valid JSON object."
SYSTEM_JSON_COORDS = "Return JSON with coordinates."
SYSTEM_RESCUE = "You are a recovery agent."

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

VERIFIER_TEMPLATE = "Verify {target}."
PLANNER_TEMPLATE = "Plan for {task_instruction}."
PLANNER_COMPLETED_SECTION = "Done: {items}"
RESCUE_TEMPLATE = "Stuck on {task_instruction}."
