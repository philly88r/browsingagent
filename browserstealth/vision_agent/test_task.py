from browser_agent import BrowserAgent

with BrowserAgent() as agent:
    agent.run_task(
        task_instruction="Go to Google, search for OpenAI, and click the first official result",
        starting_url="https://www.google.com"
    )
