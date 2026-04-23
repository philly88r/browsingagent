"""
Test script to demonstrate verification handling
"""

from browser_agent import BrowserAgent
import time


def main():
    print("\n" + "="*60)
    print("🧪 Testing Verification Detection")
    print("="*60 + "\n")
    
    print("This test will:")
    print("1. Navigate to a site that requires verification")
    print("2. Detect when verification is needed")
    print("3. Pause and request user input")
    print("4. Continue after verification is provided\n")
    
    with BrowserAgent(headless=False) as agent:
        # Example: Try to log into a site that uses 2FA
        # The agent will detect the verification prompt and pause
        
        agent.run_task(
            task_instruction="Navigate to the login page and attempt to sign in. If verification is needed, request it from the user.",
            starting_url="https://www.google.com"  # Replace with actual test site
        )
    
    print("\n" + "="*60)
    print("✅ Test complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
