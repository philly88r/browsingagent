# Vision Browser Agent 🤖👁️

A vision-based browser automation agent that uses AI to understand web pages through screenshots and interact with them like a human.

## How It Works

The agent operates in a continuous loop:

1. **📸 Screenshot** - Captures the current browser state
2. **👁️ Analyze** - Gemini Flash vision model analyzes the screenshot and decides what to do
3. **🖱️ Act** - Executes the action with human-like movements
4. **🔄 Repeat** - Continues until task is complete

## Features

- **Vision-Based Navigation**: Uses Gemini Flash to "see" and understand web pages
- **Human-Like Interactions**: 
  - Bezier curve mouse movements
  - Variable typing speed with occasional typos
  - Natural scrolling patterns
  - Random pauses and micro-movements
- **Smart Verification Detection**: 
  - Automatically detects 2FA prompts, SMS codes, email verification
  - Pauses and requests user input when needed
  - Seamlessly resumes after verification
- **Context-Aware**: Maintains action history for better decision making
- **GUI Interface**: Easy-to-use interface for controlling the agent
- **Stealth Mode**: Configured to avoid bot detection

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your API key:
```bash
# Copy .env.example to .env (already configured with your key)
cp .env.example .env
```

3. Run the agent:
```bash
# With GUI
python agent_ui.py

# Or programmatically
python browser_agent.py
```

## Usage

### GUI Mode

1. Launch the UI: `python agent_ui.py`
2. Enter a starting URL (optional)
3. Describe the task you want to accomplish
4. Click "Start Agent"
5. Watch the agent work!

### Programmatic Mode

```python
from browser_agent import BrowserAgent

with BrowserAgent() as agent:
    agent.run_task(
        task_instruction="Go to Amazon and search for 'wireless mouse'",
        starting_url="https://www.amazon.com"
    )
```

## Example Tasks

- "Search Google for 'Python tutorials' and click the first result"
- "Go to Reddit and find posts about AI"
- "Navigate to Twitter and read the trending topics"
- "Fill out a contact form with test data"
- "Find and click the login button, then enter credentials"
- "Log into my account (agent will pause and ask for 2FA code)"

## Verification Handling

The agent automatically detects when human verification is needed:

### What It Detects
- 2FA/MFA prompts
- SMS verification codes
- Email verification links
- CAPTCHA challenges
- Security questions
- Any "Enter code" or "Verify your identity" prompts

### How It Works
1. Agent sees verification prompt in screenshot
2. Pauses execution automatically
3. Shows alert: "⚠️ HUMAN VERIFICATION REQUIRED"
4. Displays what's needed (e.g., "Please provide the SMS verification code")
5. You enter the code in the UI
6. Agent submits it and continues

### Example Flow
```
Agent: Clicking login button...
Agent: Entering credentials...
Agent: ⚠️ VERIFICATION REQUIRED
       📋 Request: Please provide the 6-digit SMS code
       📍 Field: Verification code input
[You enter: 123456]
Agent: ✅ Code submitted
Agent: Continuing task...
```

## Configuration

### Browser Settings

In `browser_agent.py`:
- `headless`: Run browser in headless mode (default: False)
- `window_size`: Browser window dimensions (default: 1920x1080)
- `max_iterations`: Maximum steps before stopping (default: 50)

### Human-Like Behavior

In `human_like_movement.py`:
- Adjust typing speed (WPM)
- Modify mouse movement curves
- Change scroll patterns
- Tune pause durations

### Vision Analysis

In `vision_analyzer.py`:
- Model: `gemini-flash-latest`
- Temperature: 0.4 (for consistent behavior)
- Max tokens: 2048

## Architecture

```
vision_agent/
├── browser_agent.py          # Main agent loop
├── vision_analyzer.py         # Gemini vision integration
├── human_like_movement.py     # Human-like interactions
├── agent_ui.py               # GUI interface
├── requirements.txt          # Dependencies
├── .env                      # API keys
└── screenshots/              # Saved screenshots
```

## How the Vision System Works

The agent sends each screenshot to Gemini Flash with a prompt that includes:
- The overall task objective
- Recent action history for context
- Instructions on available actions
- Request for JSON-formatted response

Gemini analyzes the screenshot and responds with:
```json
{
    "action": "click",
    "reasoning": "I can see a search button at these coordinates",
    "parameters": {
        "x": 500,
        "y": 300,
        "description": "Google search button"
    }
}
```

## Tips for Best Results

1. **Be Specific**: Clear task descriptions work better
   - ✅ "Search for 'Python' and click the first Wikipedia result"
   - ❌ "Find some Python stuff"

2. **Start Simple**: Test with straightforward tasks first
   - Google searches
   - Clicking obvious buttons
   - Simple form filling

3. **Monitor Progress**: Watch the agent work to understand its behavior

4. **Adjust Max Iterations**: Complex tasks may need more steps

## Troubleshooting

### Agent gets stuck in a loop
- The task may be too vague
- Try breaking it into smaller steps
- Check if the page loaded correctly

### Actions are inaccurate
- Ensure window size matches your screen
- Check screenshot quality
- Verify coordinates are visible in screenshots

### API errors
- Verify your Gemini API key is correct
- Check your API quota/limits
- Ensure internet connection is stable

## Advanced Usage

### Custom Actions

Add new actions in `browser_agent.py`:

```python
elif action_type == 'custom_action':
    # Your custom logic here
    pass
```

### Modify Vision Prompt

Edit the prompt in `vision_analyzer.py` to change how the agent thinks:

```python
def _build_analysis_prompt(self, task_instruction, context):
    prompt = f"""Your custom instructions here..."""
    return prompt
```

### Add Memory/State

The agent maintains `action_history` - extend this for more complex state:

```python
self.custom_state = {
    'visited_pages': [],
    'found_items': [],
    'current_goal': None
}
```

## Future Enhancements

- [ ] Multi-tab support
- [ ] Form auto-fill with smart field detection
- [ ] Screenshot comparison for change detection
- [ ] Captcha solving integration
- [ ] Session persistence
- [ ] Task templates/recipes
- [ ] Performance metrics and analytics

## License

MIT

## Credits

Built with:
- Selenium for browser control
- Gemini Flash for vision analysis
- Python for everything else
