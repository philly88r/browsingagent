from dotenv import load_dotenv
import os, requests, base64, json
load_dotenv(override=True)

key = os.getenv('OPENCODE_API_KEY')
headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
BASE = 'https://opencode.ai/zen/go/v1/chat/completions'
MODEL = 'mimo-v2-omni'

def post(messages, max_tokens=200):
    r = requests.post(BASE, headers=headers, json={
        'model': MODEL, 'messages': messages, 'max_tokens': max_tokens, 'temperature': 0.1
    }, timeout=30)
    r.raise_for_status()
    choice = r.json()['choices'][0]
    msg = choice['message']
    print(f"  [finish={choice.get('finish_reason')} content={'null' if msg.get('content') is None else 'set'} reasoning={'null' if msg.get('reasoning') is None else 'set'}]")
    content = msg.get('content') or ''
    reasoning = msg.get('reasoning') or ''
    print(f"  content: {content[:150].encode('ascii','replace').decode()}")
    print(f"  reasoning: {reasoning[:150].encode('ascii','replace').decode()}")
    return content or reasoning

print(f"Model: {MODEL}\n")

# Test 1: basic text
print("--- Test 1: Basic text ---")
out = post([{'role': 'user', 'content': 'Say exactly: hello world'}])
print(out[:200].encode('ascii', 'replace').decode())

# Test 2: JSON format compliance
print("\n--- Test 2: JSON output ---")
out = post([{'role': 'user', 'content': 'Respond with ONLY this JSON, no other text:\n{"action": "navigate", "reasoning": "test", "parameters": {"url": "https://google.com"}}'}], max_tokens=512)
print(out[:300].encode('ascii', 'replace').decode())

# Test 3: vision
print("\n--- Test 3: Vision ---")
img_b64 = base64.b64encode(open('screenshots/iter_001.png','rb').read()).decode() if os.path.exists('screenshots/iter_001.png') else None
if img_b64:
    out = post([{'role': 'user', 'content': [
        {'type': 'text', 'text': 'What is on this webpage? Answer in one sentence.'},
        {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
    ]}], max_tokens=512)
    print(out[:300].encode('ascii', 'replace').decode())
else:
    print("No screenshot found — skipping vision test")

print("\nDone.")
