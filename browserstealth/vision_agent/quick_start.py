"""
Quick start script for testing the vision agent
"""

from browser_agent import BrowserAgent


def main():
    print("\n" + "="*60)
    print("🤖 Vision Browser Agent - Quick Start")
    print("="*60 + "\n")
    
    # Example 1: Simple Google search
    print("Example 1: Google Search")
    print("-" * 60)
    
    with BrowserAgent(headless=False) as agent:
        agent.run_task(
            task_instruction="Search Google for 'Python automation' and click the first result",
            starting_url="https://www.google.com"
        )
    
    print("\n" + "="*60)
    print("✅ Quick start complete!")
    print("="*60 + "\n")
    
    print("Next steps:")
    print("1. Run 'python agent_ui.py' for the GUI interface")
    print("2. Try more complex tasks")
    print("3. Check the screenshots/ folder to see what the agent saw")
    print("4. Read README.md for more examples\n")


if __name__ == "__main__":
    main()
